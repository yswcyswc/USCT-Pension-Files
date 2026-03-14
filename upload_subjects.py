import csv
from pathlib import Path
from panoptes_client import Panoptes, Project, SubjectSet, Subject

USERNAME = "usct_pension_files"
PASSWORD = "usct2026"

PROJECT_ID = 32086
SUBJECT_SET_NAME = "RobinsonLucius+RobinsonHarry"

MANIFEST_PATH = Path("dataset/manifest.csv")

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

with MANIFEST_PATH.open(newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    for row in reader:
        image_path = Path(row["image"])
        ai_text_path = Path(row["ai_text_file"])

        if not image_path.exists():
            print(f"Skipping missing image: {image_path}")
            continue

        if not ai_text_path.exists():
            print(f"Skipping missing transcript: {ai_text_path}")
            continue

        ai_text_content = ai_text_path.read_text(encoding="utf-8", errors="replace")

        subject = Subject()
        subject.links.project = project

        subject.add_location(str(image_path))

        subject.metadata["page"] = row["page"]
        subject.metadata["pdf"] = row["pdf"]
        subject.metadata["image_filename"] = image_path.name
        subject.metadata["ai_text_file"] = str(ai_text_path)
        subject.metadata["AI Transcript"] = ai_text_content

        subject.save()
        subject_set.add(subject)

        count += 1
        print(f"Uploaded {count}: {image_path.name}")

subject_set.save()

print(f"Done. Uploaded {count} subjects to subject set '{SUBJECT_SET_NAME}'.")