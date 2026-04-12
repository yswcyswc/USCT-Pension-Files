# USCT Pension Files Project (Zooniverse Portion)


## Overview

This repository supports the USCT Pension Files project, which combines AI transcription, structured extraction, crowdsourced validation, and downstream research use for Civil War pension documents.

At a high level, the workflow is:

1. original pension files are transcribed page by page
2. page images and page-level text are stored as source data
3. entities such as people, locations, and dates are extracted and then optimized using Splink linkage to identify variations or misspellings of the same name and link them together.
4. Zooniverse is used for human review and correction
5. validated results can feed later aggregation, analysis, and public-facing search

The current code in this repo is centered on the Zooniverse portion of that workflow, but it depends on the broader transcription and extraction pipeline.

![USCT Pension Files Project Workflow](<assets/373 Project Workflow Updated.jpg>)


If you are approaching this as:

- a client or project partner, start with [CLIENT_README.md](CLIENT_README.md)
- a future student team member, start with this and [FUTURE_TEAMS_README.md](FUTURE_TEAMS_README.md)
- Dietrich Computing or a technical maintainer, start with [DIETRICH_COMPUTING_README.md](DIETRICH_COMPUTING_README.md)

## Main Components

- `dataset/transcriber_db.db`
  SQLite database containing page-level transcriptions and extracted structured data.

- `src/zooniverse/build_manifest_S3.py`
  Generates the current Zooniverse manifest from the database using the S3 / CloudFront image setup.

- `src/zooniverse/db_queries.py`
  Holds the SQLite query helpers used by the Zooniverse scripts.

- `src/zooniverse/transcript_formatter.py`
  Contains the names/places formatting logic used to build the volunteer-facing text block.

- `src/zooniverse/upload_subjects_S3.py`
  Uploads page images and paired text files to Zooniverse using the `TextFromSubject` workflow.

- `src/zooniverse/postprocess.py`
  Reads Zooniverse classification exports, majority-votes the editable names/places section, and writes the result into `transcriptions.validated_names`.

- `dataset/manifest_s3.csv`
  Generated manifest used for Zooniverse upload.

## Project Structure

The repository now uses a simple `src/` layout:

- `src/zooniverse/`
  Current scripts for the active S3 / CloudFront + `TextFromSubject` workflow.

- `src/legacy/`
  Older non-S3 scripts and archived helper scripts that are still retained for reference.

- `src/user_testing/`
  Small one-off upload scripts used with the `dataset/userTesting/` sample assets.

- `dataset/`
  Generated manifests and sample project data.

- `dataset/userTesting/`
  User-testing image assets, transcript assets, and the local user-testing readme.

- repo root
  Project documentation, database files, and reference materials.

## Zooniverse in Context

Zooniverse is the human validation layer in this project.

In the current design:

- one subject equals one page
- each subject includes one page image and one editable text file
- volunteers review and correct the text in Zooniverse
- those corrections are intended to support later aggregation and final output

This sits between the source transcription database and any later validated output database or public search interface.

## Current Workflow

1. Page-level transcription text is stored in `transcriptions`.
2. Extracted people and places are stored in `persons` and `locations`.
3. `src/zooniverse/build_manifest_S3.py` creates `dataset/manifest_s3.csv`.
4. `src/zooniverse/upload_subjects_S3.py` uploads the manifest contents to Zooniverse.
5. Volunteers review and correct text using `TextFromSubject`.
6. `src/zooniverse/postprocess.py` aggregates the editable section and writes majority-vote results back into the database.
   This post-processing step still needs to be confirmed against real exports.

## Key Documents

- [CLIENT_README.md](CLIENT_README.md)
  Short client-facing explanation of the Zooniverse stage.

- [FUTURE_TEAMS_README.md](FUTURE_TEAMS_README.md)
  Student-oriented handoff focused on the Zooniverse component in the context of the larger project.

- [DIETRICH_COMPUTING_README.md](DIETRICH_COMPUTING_README.md)
  Technical design document for the current Zooniverse implementation.

- [STUDENT_TEAM_README.md](STUDENT_TEAM_README.md)
  Broader dataset and project background for student researchers.

- [ZOONIVERSE_SETUP_CHECKLIST.md](ZOONIVERSE_SETUP_CHECKLIST.md)
  Manual post-upload checklist for verifying the Zooniverse setup.

## Running the Current Zooniverse Pipeline

Generate the manifest:

```powershell
python src\zooniverse\build_manifest_S3.py
```

Set Zooniverse credentials and a subject set name:

```powershell
$env:ZOONIVERSE_USERNAME="your-zooniverse-username"
$env:ZOONIVERSE_PASSWORD="your-zooniverse-password"
$env:ZOONIVERSE_PROJECT_ID="32086"
$env:SUBJECT_SET_NAME="TextFromSubject Test"
```

Upload to Zooniverse:

```powershell
python src\zooniverse\upload_subjects_S3.py
```

Post-process a Zooniverse classification export:

```powershell
$env:EXPORT_FILE="classifications.csv"
python src\zooniverse\postprocess.py
```

`postprocess.py` is currently marked as: needs to be confirmed.

## Important Notes

- The current upload flow assumes the Zooniverse project is configured with the `TextFromSubject` task type.
- Images are served from CloudFront rather than uploaded from a local image directory.
- The current manifest stores the final upload-ready text in `final_txt_for_upload`.
- Post-processing currently aggregates only the editable names/places block and stores the majority-vote result in `validated_names`.
- The DB access layer for the current Zooniverse workflow is split into `src/zooniverse/db_queries.py`.
- If you change the manifest text format, existing Zooniverse subject sets will not update automatically.

