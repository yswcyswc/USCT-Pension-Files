import csv
import io
import mimetypes
import os
from pathlib import Path
from urllib.parse import urlparse

from panoptes_client import Panoptes, Project, Subject, SubjectSet

REPO_ROOT = Path(__file__).resolve().parents[2]
USERNAME = os.getenv("ZOONIVERSE_USERNAME", "usct_pension_files")
PASSWORD = os.getenv("ZOONIVERSE_PASSWORD", "usct2026")
PROJECT_ID = int(os.getenv("ZOONIVERSE_PROJECT_ID", "32086"))
SUBJECT_SET_NAME = os.getenv("SUBJECT_SET_NAME", "Testing Batch Upload")
MANIFEST_PATH = Path(os.getenv("MANIFEST_PATH", REPO_ROOT / "dataset/manifest_s3.csv"))


def guess_mime_type(image_url: str) -> str:
    path = urlparse(image_url).path
    mime_type, _ = mimetypes.guess_type(path)
    if mime_type is None or not mime_type.startswith("image/"):
        raise ValueError(f"Could not determine image MIME type from URL: {image_url}")
    return mime_type


def create_subject_set(project: Project, display_name: str) -> SubjectSet:
    subject_set = SubjectSet()
    subject_set.links.project = project
    subject_set.display_name = display_name
    subject_set.save()
    print(f"Created subject set: {display_name} (id={subject_set.id})")
    return subject_set


def safe_stem(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value)


def build_virtual_text_filename(row: dict[str, str]) -> str:
    pdf_stem = safe_stem(row["pdf_stem"])
    page = str(row["page"]).strip()
    transcription_id = str(row["transcription_id"]).strip()
    return f"{pdf_stem}-page{page}-tid{transcription_id}.txt"


if not MANIFEST_PATH.exists():
    raise FileNotFoundError(f"Manifest not found: {MANIFEST_PATH}")

Panoptes.connect(username=USERNAME, password=PASSWORD)
project = Project.find(PROJECT_ID)

subject_set = create_subject_set(project, SUBJECT_SET_NAME)

count = 0

with MANIFEST_PATH.open(newline="", encoding="utf-8") as handle:
    reader = csv.DictReader(handle)

    for row in reader:
        image_url = row["image_url"].strip()
        if not image_url.startswith(("http://", "https://")):
            print(f"Skipping invalid image URL: {image_url}")
            continue

        try:
            mime_type = guess_mime_type(image_url)
        except ValueError as exc:
            print(f"Skipping row: {exc}")
            continue

        transcript_text = row.get("final_txt_for_upload", "")
        text_buffer = io.BytesIO(transcript_text.encode("utf-8"))
        text_buffer.name = build_virtual_text_filename(row)

        subject = Subject()
        subject.links.project = project
        subject.add_location({mime_type: image_url})
        subject.add_location(text_buffer, manual_mimetype="text/plain")

        subject.metadata["page"] = row["page"]
        subject.metadata["pdf"] = row["pdf_stem"]
        subject.metadata["pdf_file"] = row["pdf_file"]
        subject.metadata["transcription_id"] = row["transcription_id"]
        subject.metadata["source_image_url"] = image_url
        if row.get("txt_url"):
            subject.metadata["source_txt_url"] = row["txt_url"]
        subject.metadata["paired_text_file"] = build_virtual_text_filename(row)

        subject.save()
        subject_set.add(subject)

        count += 1
        print(f"Uploaded {count}: {row['pdf_stem']} page {row['page']}")

subject_set.save()

print(f"Done. Uploaded {count} subjects to subject set '{SUBJECT_SET_NAME}'.")
