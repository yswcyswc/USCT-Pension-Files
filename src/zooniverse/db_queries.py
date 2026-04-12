import sqlite3
from pathlib import Path


def get_transcription_columns(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("PRAGMA table_info(transcriptions)").fetchall()
    return {row[1] for row in rows}


def fetch_transcriptions(db_path: Path):
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        columns = get_transcription_columns(conn)

        has_s3_image_url = "s3_image_url" in columns
        has_s3_txt_url = "s3_txt_url" in columns

        query = """
            SELECT
                id AS transcription_id,
                pdf_file,
                page,
                txt_file,
                final_txt_for_upload
        """
        if has_s3_image_url:
            query += ", s3_image_url"
        if has_s3_txt_url:
            query += ", s3_txt_url"
        query += """
            FROM transcriptions
            ORDER BY pdf_file, page
        """

        return conn.execute(query).fetchall(), has_s3_image_url, has_s3_txt_url


def fetch_people_by_transcription(db_path: Path) -> dict[int, list[sqlite3.Row]]:
    query = """
        SELECT
            transcription_id,
            first_name,
            middle_name,
            middle_initial,
            last_name,
            prefix,
            suffix,
            title
        FROM persons
        ORDER BY transcription_id, id
    """
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query).fetchall()

    grouped: dict[int, list[sqlite3.Row]] = {}
    for row in rows:
        grouped.setdefault(row["transcription_id"], []).append(row)
    return grouped


def fetch_locations_by_transcription(db_path: Path) -> dict[int, list[sqlite3.Row]]:
    query = """
        SELECT
            transcription_id,
            place_name,
            type,
            city,
            county,
            state
        FROM locations
        ORDER BY transcription_id, id
    """
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query).fetchall()

    grouped: dict[int, list[sqlite3.Row]] = {}
    for row in rows:
        grouped.setdefault(row["transcription_id"], []).append(row)
    return grouped
