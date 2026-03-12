import pathlib
import csv

images_dir = pathlib.Path("dataset/images")
transcripts_dir = pathlib.Path("dataset/ai_transcripts")
manifest_path = pathlib.Path("dataset/manifest.csv")

rows = []

for img_path in sorted(images_dir.rglob("*.png")):
    name = img_path.stem # e.g. Robinson_Lucius-1
    pdf_name = img_path.parent.name  # e.g. Robinson_Lucius
    page_num = name.rsplit("-", 1)[-1]  # e.g. 1

    transcript_path = transcripts_dir / pdf_name / f"{name}.txt"

    rows.append({
        "image": img_path.name,
        "page": page_num,
        "pdf": pdf_name,
        "ai_text": str(transcript_path)
    })

with open(manifest_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["image", "page", "pdf", "ai_text"])
    writer.writeheader()
    writer.writerows(rows)

print(f"Manifest written: {len(rows)} subjects")