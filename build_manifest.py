import pathlib
import csv

images_dir = pathlib.Path("dataset/images")
transcripts_dir = pathlib.Path("dataset/ai_transcripts")
manifest_path = pathlib.Path("dataset/manifest.csv")

rows = []

for img_path in sorted(images_dir.rglob("*.png")):
    name = img_path.stem                  # Robinson_Lucius-1
    pdf_name = img_path.parent.name       # Robinson_Lucius
    page_num = name.rsplit("-", 1)[-1]    # 1

    transcript_path = transcripts_dir / pdf_name / f"{name}.txt"

    # Read the actual transcript text
    if transcript_path.exists():
        ai_transcript = transcript_path.read_text(encoding="utf-8").strip()
    else:
        ai_transcript = ""  # or some placeholder like "[No transcript available]"

    rows.append({
        "image": str(img_path),
        "page": page_num,
        "pdf": pdf_name,
        "AI Transcript": ai_transcript   # ← exact name to match {{AI Transcript}}
    })

with open(manifest_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["image", "page", "pdf", "AI Transcript"]
    )
    writer.writeheader()
    writer.writerows(rows)

print(f"Manifest written: {len(rows)} subjects")