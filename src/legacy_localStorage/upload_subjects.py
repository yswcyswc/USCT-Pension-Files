import csv
import mimetypes
import os
from pathlib import Path
from urllib.parse import urlparse

from panoptes_client import Panoptes, Project, Subject, SubjectSet

REPO_ROOT = Path(__file__).resolve().parents[2]
USERNAME = os.getenv("ZOONIVERSE_USERNAME", "usct_pension_files")
PASSWORD = os.getenv("ZOONIVERSE_PASSWORD", "usct2026")
PROJECT_ID = int(os.getenv("ZOONIVERSE_PROJECT_ID", "32086"))
SUBJECT_SET_NAME = os.getenv("SUBJECT_SET_NAME", "USCT Pension Files Upload")
MANIFEST_PATH = Path(os.getenv("MANIFEST_PATH", REPO_ROOT / "dataset/manifest.csv"))


def guess_mime_type(image_url: str) -> str:
    path = urlparse(image_url).path
    mime_type, _ = mimetypes.guess_type(path)
    if mime_type is None or not mime_type.startswith("image/"):
        raise ValueError(f"Could not determine image MIME type from URL: {image_url}")
    return mime_type


if not MANIFEST_PATH.exists():
    raise FileNotFoundError(f"Manifest not found: {MANIFEST_PATH}")

Panoptes.connect(username=USERNAME, password=PASSWORD)
project = Project.find(PROJECT_ID)

subject_set = SubjectSet()
subject_set.links.project = project
subject_set.display_name = SUBJECT_SET_NAME
subject_set.save()

print(f"Created subject set: {SUBJECT_SET_NAME} (id={subject_set.id})")

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

        subject = Subject()
        subject.links.project = project
        subject.add_location({mime_type: image_url})

        subject.metadata["page"] = row["page"]
        subject.metadata["pdf"] = row["pdf_stem"]
        subject.metadata["pdf_file"] = row["pdf_file"]
        subject.metadata["transcription_id"] = row["transcription_id"]
        subject.metadata["source_image_url"] = image_url
        if row.get("txt_file"):
            subject.metadata["txt_file"] = row["txt_file"]
        subject.metadata["AI Transcript"] = row.get("ai_transcript", "")

        subject.save()
        subject_set.add(subject)

        count += 1
        print(f"Uploaded {count}: {row['pdf_stem']} page {row['page']}")

subject_set.save()

print(f"Done. Uploaded {count} subjects to subject set '{SUBJECT_SET_NAME}'.")
