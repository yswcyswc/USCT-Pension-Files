import csv
import json
import os
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

from transcript_formatter import normalize_editable_section

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPORT_FILE = Path(os.getenv("EXPORT_FILE", REPO_ROOT / "classifications.csv"))
DB_PATH = Path(os.getenv("TRANSCRIBER_DB_PATH", REPO_ROOT / "dataset/transcriber_db.db"))


def extract_corrected_text(annotations: list[dict]) -> str | None:
    for task in annotations:
        if task.get("taskType") == "textFromSubject":
            value = task.get("value")
            if isinstance(value, str):
                value = value.strip()
                if value:
                    return value
    return None


def majority_vote(texts: list[str]) -> str:
    counter = Counter(texts)
    return counter.most_common(1)[0][0]


def parse_transcription_id(subject_data: dict) -> int | None:
    subject_id = next(iter(subject_data))
    metadata = subject_data[subject_id]
    raw_id = metadata.get("transcription_id")
    if raw_id is None or str(raw_id).strip() == "":
        return None
    return int(raw_id)


def ensure_validated_names_column(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        columns = [row[1] for row in conn.execute("PRAGMA table_info(transcriptions)").fetchall()]
        if "validated_names" not in columns:
            conn.execute("ALTER TABLE transcriptions ADD COLUMN validated_names TEXT")
            conn.commit()


def load_votes(export_file: Path) -> dict[int, list[str]]:
    votes: dict[int, list[str]] = defaultdict(list)

    with export_file.open(newline="", encoding="utf8") as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            annotations = json.loads(row["annotations"])
            subject_data = json.loads(row["subject_data"])

            corrected_text = extract_corrected_text(annotations)
            if not corrected_text:
                continue

            transcription_id = parse_transcription_id(subject_data)
            if transcription_id is None:
                continue

            editable_section = normalize_editable_section(corrected_text)
            if editable_section:
                votes[transcription_id].append(editable_section)

    return votes


def write_validated_names(db_path: Path, votes: dict[int, list[str]]) -> int:
    updated = 0

    with sqlite3.connect(db_path) as conn:
        for transcription_id, text_versions in votes.items():
            winning_text = majority_vote(text_versions)
            conn.execute(
                """
                UPDATE transcriptions
                SET validated_names = ?
                WHERE id = ?
                """,
                (winning_text, transcription_id),
            )
            updated += 1
        conn.commit()

    return updated


def main():
    if not EXPORT_FILE.exists():
        raise FileNotFoundError(f"Classification export not found: {EXPORT_FILE}")
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    ensure_validated_names_column(DB_PATH)
    votes = load_votes(EXPORT_FILE)
    updated = write_validated_names(DB_PATH, votes)

    print(f"Loaded votes for {len(votes)} transcriptions from {EXPORT_FILE}")
    print(f"Updated validated_names for {updated} transcriptions in {DB_PATH}")


if __name__ == "__main__":
    main()
