# Technical Design Document

## Project Scope

This repository supports the Zooniverse portion of the Civil War pension file workflow. The current design prepares page-level image and transcription data for human review in Zooniverse using the `TextFromSubject` task type.

The main goal is to move away from a local-file-only upload model and toward a pipeline that:

- stores page images online
- keeps transcription data in a database
- generates a manifest automatically
- uploads paired image + text subjects to Zooniverse
- supports volunteer correction of draft transcription text

## Current Architecture

The system now uses four main components:

1. `dataset/transcriber_db.db`
   This SQLite database is the local source of truth for page-level transcription text and extracted structured data.

2. CloudFront / S3 image hosting
   Historical page images are served from:
   `https://d49k6q6w27fis.cloudfront.net`

3. Manifest generation
   A generated CSV manifest connects each transcription record to its image URL, transcription URL, metadata, and Zooniverse-facing editable text payload.

4. Zooniverse upload
   Subjects are uploaded to Zooniverse as paired files:
   - one remote image
   - one in-memory plain-text payload for `TextFromSubject`

5. Post-processing
   Classification exports are aggregated after volunteer work is complete and the majority-vote names/places block is written back to the database.

## Core Workflow

The intended flow is:

1. A page is transcribed and stored in the `transcriptions` table.
2. People and locations are extracted into `persons` and `locations`.
3. `src/zooniverse/build_manifest_S3.py` reads the database and produces `dataset/manifest_s3.csv`.
4. The manifest includes:
   - `image_url`
   - `txt_url`
   - page/file metadata
   - a formatted editable transcript block for Zooniverse
5. `src/zooniverse/upload_subjects_S3.py` reads the manifest.
6. For each row, the script:
   - links the remote page image
   - uploads the final text payload as the paired `TextFromSubject` text source
   - stores selected metadata on the Zooniverse subject
7. Volunteers see the image and preloaded text in the transcription interface and can directly correct it.
8. `src/zooniverse/postprocess.py` reads the classification export, majority-votes the editable section, and writes the result into `transcriptions.validated_names`.

## Why `TextFromSubject`

The current workflow uses Zooniverse's `TextFromSubject` task type rather than metadata-only transcript display.

This choice matters because:

- the text appears directly in the editable text box
- volunteers can correct the draft immediately
- the transcription is treated as subject content, not just reference metadata
- the workflow matches Zooniverse guidance for text-correction projects

In practice, this means each Zooniverse subject must contain:

- an image file
- a plain-text file

The plain-text file is uploaded as a paired subject location, not as an `AI Transcript` metadata field.

## Online Storage Design

The image hosting pattern provided by project partners is:

- Base URL:
  `https://d49k6q6w27fis.cloudfront.net`
- Image key pattern:
  `images/{pdf_stem}/{pdf_stem}-{page_padded}.jpg`
- Transcription key pattern:
  `transcriptions/{pdf_stem}/{pdf_stem}-{page_padded}.txt`

Example:

`https://d49k6q6w27fis.cloudfront.net/images/Abbs_Wilkins/Abbs_Wilkins-001.jpg`

This allows Zooniverse to fetch page images directly over HTTPS without local image staging.

## Database Usage

The key table for upload is `transcriptions`.

Important fields:

- `id`
- `pdf_file`
- `page`
- `txt_file`
- `final_txt_for_upload`
- `validated_names`

Additional extracted data comes from:

- `persons`
- `locations`

The current local SQLite file does not yet contain `s3_image_url` or `s3_txt_url`, so `src/zooniverse/build_manifest_S3.py` supports both cases:

- if those columns exist in a future DB, it uses them directly
- otherwise it constructs CloudFront URLs from the naming convention

This keeps the pipeline compatible with both the current local DB and an updated DB from partners.

## Zooniverse Text Payload Format

The editable text uploaded for each subject is intentionally structured.

Current format:

```text
===Modify below this===
People:
...

Places / Locations:
...

===Do NOT modify below this===
===Context: Full Transcription===
...
```

The top section is designed to be edited by volunteers. The lower context section preserves the full source transcription for reference.

The `People` and `Places / Locations` sections are generated from existing extracted tables rather than rerunning transcription.

The reusable logic for this formatting now lives in:

`src/zooniverse/transcript_formatter.py`

## Script Responsibilities

### `src/zooniverse/build_manifest_S3.py`

Responsibilities:

- open the SQLite database
- read transcription rows
- read extracted people and locations
- derive or reuse CloudFront URLs
- call the transcript formatter to build the Zooniverse text payload
- write `dataset/manifest_s3.csv`

Output columns:

- `image_url`
- `txt_url`
- `page`
- `pdf_file`
- `pdf_stem`
- `transcription_id`
- `txt_file`
- `final_txt_for_upload`

This field holds the full formatted `TextFromSubject` text payload used for upload.

### `src/zooniverse/upload_subjects_S3.py`

Responsibilities:

- connect to Zooniverse using Panoptes
- create a fresh subject set
- read the generated manifest
- upload one remote image plus one paired text payload per subject
- attach core metadata

### `src/zooniverse/transcript_formatter.py`

Responsibilities:

- format the volunteer-facing names/places block
- append the protected transcription context
- extract and normalize the editable section for post-processing

### `src/zooniverse/postprocess.py`

Responsibilities:

- read a Zooniverse classification export CSV
- extract only the editable names/places section from `textFromSubject` responses
- majority-vote that editable section per `transcription_id`
- write the aggregated result into `transcriptions.validated_names`

## Configuration

### Manifest builder

Supported environment variables:

- `TRANSCRIBER_DB_PATH`
- `MANIFEST_PATH`
- `CLOUDFRONT_BASE_URL`
- `IMAGE_KEY_TEMPLATE`
- `TXT_KEY_TEMPLATE`
- `PAGE_PADDING`
- `FORMAT_FOR_ZOONIVERSE`

### Upload script

Supported environment variables:

- `ZOONIVERSE_USERNAME`
- `ZOONIVERSE_PASSWORD`
- `ZOONIVERSE_PROJECT_ID`
- `SUBJECT_SET_NAME`
- `MANIFEST_PATH`
## Operational Assumptions

The current design assumes:

- CloudFront image URLs are public and stable
- Zooniverse can fetch the image URLs directly over HTTPS
- the target Zooniverse workflow uses `TextFromSubject`
- one subject corresponds to one page
- the local machine running the upload can read the manifest produced by the builder

## Current Limitations

1. The final volunteer-facing text is currently stored in the manifest.
   That is simple and explicit, but it means the manifest is not just lightweight routing metadata.

2. Name quality depends on prior extraction quality.
   The `People` section is drawn from the `persons` table, so OCR or extraction errors can still appear there.

3. The formatted text currently uses existing extracted people and places only.
   It does not yet perform deeper entity cleanup, spelling normalization, or deduplication beyond simple ordering and duplicate suppression.

4. The current post-processing step only aggregates the editable names/places block.
   It does not attempt to reconcile the full transcription context.

5. Existing uploaded subject sets are not updated in place.
   Any metadata or text-formatting change requires a new upload batch unless a separate update process is built.

## Future Direction

Several near-term changes are already anticipated:

- migration from local SQLite to hosted PostgreSQL at CMU
- use of direct `s3_image_url` / `s3_txt_url` columns when available
- storage of volunteer-corrected text in a new linked table rather than overwriting originals
- possible cleanup or normalization of extracted names and locations before manifest generation

The current code is structured to make those changes incremental rather than requiring a full rewrite.

## Verification Checklist

After a successful upload:

1. Confirm the new subject set exists in the Zooniverse project.
2. Link the subject set to the intended workflow.
3. Open `Classify`.
4. Verify the page image loads.
5. Verify the text box is prefilled.
6. Confirm the editable section and the protected context section appear as expected.
7. Submit a test classification and confirm the output appears in the export.

## Summary

The present design uses SQLite as the structured source, CloudFront as the image delivery layer, a generated manifest as the handoff artifact, and Zooniverse `TextFromSubject` as the volunteer correction interface.

This design minimizes manual pairing work, supports partner-managed online storage, and keeps the pipeline compatible with future migration to hosted database infrastructure.
