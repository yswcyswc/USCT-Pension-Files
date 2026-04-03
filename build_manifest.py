import csv
import os
import sqlite3
from pathlib import Path, PureWindowsPath
from urllib.parse import quote

DB_PATH = Path(os.getenv("TRANSCRIBER_DB_PATH", "transcriber_db.db"))
MANIFEST_PATH = Path(os.getenv("MANIFEST_PATH", "dataset/manifest.csv"))
S3_BASE_URL = os.getenv("S3_BASE_URL", "https://example-bucket.s3.amazonaws.com").rstrip("/")
S3_PREFIX = os.getenv("S3_PREFIX", "").strip("/")
S3_KEY_TEMPLATE = os.getenv(
    "S3_KEY_TEMPLATE",
    "{pdf_stem}/{pdf_stem}-{page_padded}.jpg",
)
PAGE_PADDING = int(os.getenv("PAGE_PADDING", "4"))


def pdf_stem_from_path(pdf_file: str) -> str:
    return PureWindowsPath(pdf_file).stem


def normalize_pdf_stem(pdf_stem: str) -> str:
    return pdf_stem.replace("\\", "_").replace("/", "_").strip()


def build_s3_key(pdf_file: str, page: int) -> str:
    pdf_stem = normalize_pdf_stem(pdf_stem_from_path(pdf_file))
    page_padded = f"{page:0{PAGE_PADDING}d}"
    key = S3_KEY_TEMPLATE.format(
        pdf_stem=pdf_stem,
        page=page,
        page_padded=page_padded,
    ).lstrip("/")
    if S3_PREFIX:
        return f"{S3_PREFIX}/{key}"
    return key


def build_image_url(pdf_file: str, page: int) -> str:
    key = build_s3_key(pdf_file, page)
    return f"{S3_BASE_URL}/{quote(key, safe='/')}"


def fetch_transcriptions(db_path: Path):
    query = """
        SELECT
            id AS transcription_id,
            pdf_file,
            page,
            txt_file,
            result
        FROM transcriptions
        ORDER BY pdf_file, page
    """
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(query).fetchall()


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for record in fetch_transcriptions(DB_PATH):
        pdf_file = record["pdf_file"]
        page = record["page"]
        pdf_stem = pdf_stem_from_path(pdf_file)
        rows.append(
            {
                "image_url": build_image_url(pdf_file, page),
                "page": page,
                "pdf_file": pdf_file,
                "pdf_stem": pdf_stem,
                "transcription_id": record["transcription_id"],
                "txt_file": record["txt_file"] or "",
                "ai_transcript": record["result"] or "",
            }
        )

    with MANIFEST_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "image_url",
                "page",
                "pdf_file",
                "pdf_stem",
                "transcription_id",
                "txt_file",
                "ai_transcript",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Manifest written: {len(rows)} subjects -> {MANIFEST_PATH}")
    print(f"Image base URL: {S3_BASE_URL}")
    if S3_PREFIX:
        print(f"S3 prefix: {S3_PREFIX}")
    print(f"S3 key template: {S3_KEY_TEMPLATE}")


if __name__ == "__main__":
    main()
