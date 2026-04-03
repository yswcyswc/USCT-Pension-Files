# Zooniverse Workflow

## Overview

This repository now follows a manifest-first upload workflow built around two separate sources of truth:

- `transcriber_db.db` is the source of truth for page-level transcriptions and metadata.
- Amazon S3 is the source of truth for page images.

The Zooniverse upload pipeline does not depend on local image files. Instead, it:

1. Queries `transcriber_db.db`
2. Generates a manifest CSV that pairs each page with an S3 image URL
3. Uploads subjects to Zooniverse from that manifest using the Panoptes Python client

This is intended to be easy to hand back to project partners so they can run the same process at full scale.

## Architecture

Pipeline overview:

1. PDFs are converted to page images outside this repo's upload step.
2. The page images are stored in S3 with stable HTTPS URLs.
3. AI transcription text is stored in `transcriber_db.db`.
4. `build_manifest.py` joins the DB records to the expected S3 URL pattern.
5. `upload_subjects.py` creates Zooniverse subjects from the manifest.
6. Volunteers review the page image and open the AI draft from subject metadata.

## Files

- `build_manifest.py`: Generates `dataset/manifest.csv` from the SQLite database and an S3 naming convention.
- `upload_subjects.py`: Uploads subjects to Zooniverse from remote image URLs listed in the manifest.
- `initial_design_doc.md`: Longer design and handoff notes.
- `zooniverse_guide.md`: Manual verification checklist after upload.

## Manifest Format

`build_manifest.py` writes one row per transcribed page with these columns:

- `image_url`
- `page`
- `pdf_file`
- `pdf_stem`
- `transcription_id`
- `txt_file`
- `ai_transcript`

The upload script uses:

- `image_url` for the remote Zooniverse subject media
- `page`, `pdf_stem`, `pdf_file`, and `transcription_id` as subject metadata
- `ai_transcript` as the `AI Transcript` metadata field shown in Zooniverse's subject info panel

## Configuration

Both scripts are configured with environment variables so partners can adapt the workflow without editing code.

### `build_manifest.py`

- `TRANSCRIBER_DB_PATH`
  Default: `transcriber_db.db`
- `MANIFEST_PATH`
  Default: `dataset/manifest.csv`
- `S3_BASE_URL`
  Example: `https://my-bucket.s3.amazonaws.com`
- `S3_PREFIX`
  Optional prefix inside the bucket
- `S3_KEY_TEMPLATE`
  Default: `{pdf_stem}/{pdf_stem}-{page_padded}.jpg`
- `PAGE_PADDING`
  Default: `4`

The default URL builder assumes a layout like:

```text
https://my-bucket.s3.amazonaws.com/usct-pages/Abbs Wilkins/Abbs Wilkins-0001.jpg
https://my-bucket.s3.amazonaws.com/usct-pages/Abbs Wilkins/Abbs Wilkins-0002.jpg
```

If the partners use a different S3 naming pattern, update `S3_PREFIX`, `S3_KEY_TEMPLATE`, or both.

### `upload_subjects.py`

- `ZOONIVERSE_USERNAME`
- `ZOONIVERSE_PASSWORD`
- `ZOONIVERSE_PROJECT_ID`
  Default: `32086`
- `SUBJECT_SET_NAME`
- `MANIFEST_PATH`
  Default: `dataset/manifest.csv`

## Usage

### 1. Generate the manifest

PowerShell example:

```powershell
$env:S3_BASE_URL="https://my-bucket.s3.amazonaws.com"
$env:S3_PREFIX="usct-pages"
python build_manifest.py
```

### 2. Upload a subject set

PowerShell example:

```powershell
$env:ZOONIVERSE_USERNAME="your-zooniverse-user"
$env:ZOONIVERSE_PASSWORD="your-zooniverse-password"
$env:SUBJECT_SET_NAME="Batch 01 - Abbs Wilkins"
python upload_subjects.py
```

## Important Assumptions

- The S3 image URLs must be reachable by Zooniverse over HTTPS.
- The S3 URLs must point directly to the image, not to a viewer page.
- The file extension in the URL must match the actual media type so the upload script can infer the image MIME type.
- The DB `transcriptions` table is the authoritative source for page order and transcript text.

## Scale Notes

- Zooniverse projects often split large uploads into multiple subject sets.
- If the full collection exceeds the default Zooniverse upload quota, partners should request a higher limit from the Zooniverse team before full deployment.
- Remote image hosting in S3 avoids moving tens of thousands of images through one local workstation.

## Verification

After upload, use the checklist in `zooniverse_guide.md` to confirm:

1. the subject set exists
2. images load in the workflow
3. the `AI Transcript` metadata field appears in the subject info panel
4. test classifications are recorded correctly

## Relationship to Weaviate

Weaviate is not required for the Zooniverse upload pipeline.

It is useful for semantic search over page transcripts, but the upload workflow only needs:

- `transcriber_db.db`
- S3 image hosting
- manifest generation
- Zooniverse upload credentials
