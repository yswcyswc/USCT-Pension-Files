# Future Teams Readme (Zooniverse Component)

## Project Context

This project is larger than the Zooniverse upload scripts, so it helps to understand where the crowdsourcing piece sits in the full workflow.

At a high level, the diagram shows three connected layers:

1. transcription and source-data creation
2. entity linking and enrichment
3. crowdsourced validation and downstream public use

The flow is:

- original pension files go through AI transcription
- page images and page-level text are stored in the source transcription database
- entity extraction produces structured names, locations, and dates
- the crowdsourcing layer uses that source database to generate a manifest and send subjects to Zooniverse
- volunteer corrections are aggregated into validated data
- validated data flows into a final output database and later into a public-facing search application

Zooniverse is therefore not a standalone side project. It is the main human validation layer between automated transcription/extraction and any later research or public search experience.

## What the Zooniverse Component Does

The current Zooniverse pipeline prepares one subject per page.

Each subject contains:

- one page image
- one paired plain-text transcription file for the `TextFromSubject` task type
- a small amount of metadata for traceability

The important design choice is that the volunteer edits happen inside the Zooniverse text box, not in a metadata panel. That is why the upload script now uses paired `.txt` files instead of relying on a metadata field like `AI Transcript`.

## Current Data Flow

The implemented flow in this repo is:

1. `transcriptions` in SQLite stores the page text and page metadata.
2. `persons` and `locations` store extracted structured information.
3. `src/zooniverse/build_manifest_S3.py` queries those tables and generates `dataset/manifest_s3.csv`.
4. The manifest points each row to a CloudFront-hosted image URL.
5. `src/zooniverse/transcript_formatter.py` builds the text payload that volunteers will edit.
6. `src/zooniverse/upload_subjects_S3.py` uploads the image plus the manifest's final text payload to Zooniverse using Panoptes.
7. Volunteers review and correct text in Zooniverse.
8. `src/zooniverse/postprocess.py` majority-votes the editable section and writes the result into `validated_names`.

In the workflow diagram, this corresponds to the path:

- `Source Transcription Database (SQLite)` -> `Manifest.csv` -> `Zooniverse` -> `Crowd Validation DB` -> `Aggregation` -> `Final Output DB`

## Why the Current Design Looks Like This

There are a few design decisions that are worth preserving unless you have a strong reason to change them.

### Images are online, not local

Images are served through CloudFront rather than uploaded from a local images directory. This reduces local storage requirements and avoids rebuilding a huge image staging area every time a batch needs to be uploaded.

### Transcription text still comes from the database

The database remains the structured source of truth for page text and extracted fields, even though the text shown in Zooniverse is uploaded as a temporary `.txt` file.

### `TextFromSubject` is required

This project needs volunteer correction, not just volunteer viewing. Because of that, the workflow depends on Zooniverse's `TextFromSubject` task type. If you switch workflows, make sure you understand whether the replacement still supports preloaded editable text.

### One subject equals one page

This keeps provenance simple and aligns with the rest of the pipeline, which is page-based at the transcription, extraction, and validation stages.

## Important Files

- [src/zooniverse/build_manifest_S3.py](src/zooniverse/build_manifest_S3.py)
  Builds the S3/CloudFront-based manifest from the database.

- [src/zooniverse/upload_subjects_S3.py](src/zooniverse/upload_subjects_S3.py)
  Uploads subjects to Zooniverse in the current `TextFromSubject` format.

- [src/zooniverse/transcript_formatter.py](src/zooniverse/transcript_formatter.py)
  Holds the reusable formatting and editable-section parsing logic.

- [src/zooniverse/postprocess.py](src/zooniverse/postprocess.py)
  Aggregates Zooniverse corrections and writes majority-vote names/places back to the database.

- [dataset/manifest_s3.csv](dataset/manifest_s3.csv)
  Generated manifest used for upload.

- [DIETRICH_COMPUTING_README.md](DIETRICH_COMPUTING_README.md)
  More formal technical design document for the current implementation.

- [CLIENT_README.md](CLIENT_README.md)
  Client-facing explanation of the Zooniverse stage.

## Manifest Design

The manifest currently contains:

- `image_url`
- `txt_url`
- `page`
- `pdf_file`
- `pdf_stem`
- `transcription_id`
- `txt_file`
- `final_txt_for_upload`

This field is the final formatted text payload used for `TextFromSubject` upload.

The payload is structured like:

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

The top portion is intended for volunteer editing. The lower section preserves the full page transcription for context.

## Online Hosting Assumptions

The current S3 / CloudFront pattern is:

- base URL:
  `https://d49k6q6w27fis.cloudfront.net`
- images:
  `images/{pdf_stem}/{pdf_stem}-{page_padded}.jpg`
- transcription files:
  `transcriptions/{pdf_stem}/{pdf_stem}-{page_padded}.txt`

The current local SQLite file does not yet include `s3_image_url` or `s3_txt_url`, so the manifest builder can construct URLs automatically. If future partner-provided DBs include those columns, the script is already prepared to use them directly.

## Current Limitations

1. The editable `People` and `Places / Locations` sections depend on prior extraction quality.
   If upstream extraction is noisy, that noise will be exposed to volunteers.

2. The final volunteer-facing text is currently materialized in the manifest rather than generated entirely at upload time.
   That keeps the upload path simple, but it means the manifest contains more than just routing metadata.

3. The current post-processing step only aggregates the editable names/places section and stores it in `validated_names`.
   It is a pragmatic first aggregation layer, not a full end-to-end crowd-validation database implementation.

4. Previously uploaded Zooniverse subjects are not updated in place.
   If you change the text format or metadata structure, you usually need a new subject set.

## Likely Next Steps for Future Teams

If you inherit this project, these are the most likely engineering directions:

1. Move from local SQLite to the planned CMU-hosted PostgreSQL database.
2. Build the post-Zooniverse ingestion path from classification exports into a proper crowd-validation store.
3. Define an aggregation strategy for reconciling multiple volunteer edits into one validated output.
4. Decide how validated output feeds back into the final output database shown in the diagram.
5. Improve normalization of extracted people and place names before they are shown to volunteers.

## Practical Advice

- Keep the page-level model unless there is a strong research reason to change it.
- Preserve traceability from Zooniverse output back to `transcription_id`, `pdf_file`, and `page`.
- Treat Zooniverse configuration as part of the system design, not as a separate manual step.
- Test new upload logic with a tiny subject set before pushing a full batch.
- Do not assume old subject sets reflect the newest text payload format.

## Suggested Starting Point

If you are taking over this component, start by:

1. reading [DIETRICH_COMPUTING_README.md](DIETRICH_COMPUTING_README.md)
2. inspecting [src/zooniverse/build_manifest_S3.py](src/zooniverse/build_manifest_S3.py) and [src/zooniverse/upload_subjects_S3.py](src/zooniverse/upload_subjects_S3.py)
3. generating a small manifest batch
4. uploading a test subject set to confirm the `TextFromSubject` workflow still behaves as expected

## Bottom Line

The Zooniverse component is the bridge between automated page transcription and trustworthy research-ready text. In the project architecture, it is the main human validation step, and future teams will get the most leverage by treating it as part of a larger data pipeline rather than as a one-off upload script.
