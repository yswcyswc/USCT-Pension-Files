import csv
import json
import os
from collections import defaultdict, Counter

EXPORT_FILE = "classifications.csv"
OUTPUT_ROOT = "dataset/validated_transcripts"


def extract_transcription(annotations):
    """
    Extract corrected transcription from annotation JSON.
    """
    for task in annotations:
        if task.get("task") == "T0":  # transcription task
            value = task.get("value")
            if isinstance(value, str):
                return value.strip()
    return None


def majority_vote(texts):
    """
    Choose the most common transcript among volunteers.
    """
    counter = Counter(texts)
    return counter.most_common(1)[0][0]


def parse_subject(subject_data):
    """
    Extract page metadata from subject_data JSON.
    """
    subject_id = list(subject_data.keys())[0]
    meta = subject_data[subject_id]

    pdf = meta["pdf"]
    page = meta["page"]

    return pdf, page


def main():
    classifications = defaultdict(list)

    with open(EXPORT_FILE, newline="", encoding="utf8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            annotations = json.loads(row["annotations"])
            subject_data = json.loads(row["subject_data"])

            text = extract_transcription(annotations)
            if not text:
                continue

            pdf, page = parse_subject(subject_data)

            key = (pdf, page)
            classifications[key].append(text)

    for (pdf, page), texts in classifications.items():
        final_text = majority_vote(texts)

        out_dir = os.path.join(OUTPUT_ROOT, pdf)
        os.makedirs(out_dir, exist_ok=True)

        filename = f"{pdf}-{page}.txt"
        out_path = os.path.join(out_dir, filename)

        with open(out_path, "w", encoding="utf8") as f:
            f.write(final_text)

        print("Wrote:", out_path)


if __name__ == "__main__":
    main()