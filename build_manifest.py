import pathlib
import csv
import re

images_dir = pathlib.Path("dataset/images")
transcripts_dir = pathlib.Path("dataset/ai_transcripts")
manifest_path = pathlib.Path("dataset/manifest.csv")

def extract_page_num(stem: str):
    m = re.search(r"-(\d+)$", stem)
    return int(m.group(1)) if m else None

rows = []

for img_path in sorted(images_dir.rglob("*.png")):
    image_stem = img_path.stem
    pdf_name = img_path.parent.name
    page_num = extract_page_num(image_stem)

    transcript_dir = transcripts_dir / pdf_name
    transcript_path = ""

    if transcript_dir.exists() and page_num is not None:
        for txt_path in sorted(transcript_dir.glob("*.txt")):
            txt_page = extract_page_num(txt_path.stem)
            if txt_page == page_num:
                transcript_path = str(txt_path)
                break

    rows.append({
        "image": str(img_path),
        "page": page_num,
        "pdf": pdf_name,
        "ai_text_file": transcript_path
    })

with open(manifest_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["image", "page", "pdf", "ai_text_file"]
    )
    writer.writeheader()
    writer.writerows(rows)

print(f"Manifest written: {len(rows)} subjects")