# Part 4. Zooniverse Workflow Design

## Technical Design Document

## 1. Overview

This design uses a split-source architecture that is practical for partner handoff and large-scale reruns:

- `transcriber_db.db` stores page-level transcription text and related identifiers.
- Amazon S3 stores the page images that Zooniverse will display.
- A generated manifest CSV links the database records to the S3 image URLs.
- Zooniverse subjects are created from that manifest with the Panoptes Python client.

This avoids rebuilding a local image staging area every time a new upload batch is prepared.

## 2. Core Pipeline

1. Convert each PDF into page images.
2. Store the page images in S3.
3. Store or confirm page-level transcription text in `transcriber_db.db`.
4. Generate a manifest from the DB plus the S3 URL convention.
5. Upload subjects to Zooniverse from the manifest.
6. Link the subject set to the workflow.
7. Export volunteer classifications and post-process them later.

## 3. Scale Assumptions

| Metric | Value |
|--------|-------|
| PDFs | about 200 |
| Average pages per PDF | about 150 |
| Total pages | about 30,000 |
| Classifications per page | 5 |
| Total classifications | about 150,000 |

At this scale:

- browser-based upload is not the main path
- images should live in durable object storage
- uploads should be split across multiple subject sets
- the upload process should be rerunnable without hand-editing CSV files

## 4. Data Sources

### 4.1 SQLite database

`transcriber_db.db` is the source of truth for transcription text and page metadata.

For the upload pipeline, the key table is `transcriptions`, especially:

- `id`
- `pdf_file`
- `page`
- `txt_file`
- `result`

### 4.2 S3 object storage

S3 is the source of truth for images.

The upload pipeline assumes every transcribed page can be mapped to a stable HTTPS image URL in S3. The exact key structure can vary by partner setup, but it should be deterministic.

Example:

```text
https://bucket-name.s3.amazonaws.com/usct-pages/Abbs Wilkins/Abbs Wilkins-0001.jpg
https://bucket-name.s3.amazonaws.com/usct-pages/Abbs Wilkins/Abbs Wilkins-0002.jpg
```

The important requirement is not the exact folder pattern. The important requirement is that the mapping from `pdf_file + page` to URL is stable and automatic.

## 5. Manifest Design

The manifest is generated rather than maintained manually.

One row represents one Zooniverse subject.

Recommended columns:

- `image_url`
- `page`
- `pdf_file`
- `pdf_stem`
- `transcription_id`
- `txt_file`
- `ai_transcript`

This gives the uploader everything it needs:

- a remote image to display
- page and file metadata
- the AI transcript text to expose in the subject info panel

## 6. Subject Definition

In Zooniverse:

- 1 subject = 1 page image

Each subject should carry enough metadata to trace it back to the original DB row.

Recommended metadata fields:

- `page`
- `pdf`
- `pdf_file`
- `transcription_id`
- `source_image_url`
- `txt_file`
- `AI Transcript`

## 7. Upload Method

The Panoptes Python client is the preferred upload path for this project.

Why:

- it supports automated batch uploads
- it supports remote media URLs
- it is easier to rerun than the browser uploader

The upload script should:

1. read the generated manifest
2. create a subject set
3. add each S3 image URL as subject media
4. attach transcript text as subject metadata
5. save the subjects and add them to the set

## 8. Why S3 Instead of Local Files or Drive Links

S3 is the better production fit because it provides:

- direct HTTPS object URLs
- predictable naming
- better long-term ownership for partners
- less dependency on one local machine
- easier scale-up for tens of thousands of pages

Google Drive viewer links are less suitable because they are often page URLs rather than direct media URLs and may behave differently depending on sharing settings or rate limits.

## 9. Zooniverse Workflow Notes

The volunteer-facing workflow remains simple:

1. volunteer opens the page image
2. volunteer opens the subject info panel if needed
3. volunteer views the AI draft transcript
4. volunteer corrects the text

This design keeps the AI draft close to the page without requiring a second local transcript file upload.

## 10. Operational Notes For Partners

Partners should be able to rerun the upload process by controlling:

- DB path
- S3 base URL
- S3 prefix
- S3 key template
- Zooniverse credentials
- subject set name

Those values should be managed through environment variables whenever possible.

## 11. Failure Modes And Mitigations

| Risk | Mitigation |
|------|------------|
| S3 URL pattern does not match actual object keys | Keep the key template configurable and test one batch first |
| Zooniverse cannot fetch the image URL | Confirm the URL is direct, public or otherwise reachable, and HTTPS |
| Wrong page-to-image mapping | Derive URLs from a deterministic naming rule and spot-check sample pages |
| Missing transcript text | Pull directly from `transcriptions.result` in the DB |
| Large full-dataset upload | Break into multiple subject sets and request a quota increase if needed |

## 12. Relationship To Weaviate

Weaviate is not required for the upload pipeline.

Its role is separate:

- semantic search
- retrieval across many pages
- research exploration and QA support

For Zooniverse upload, the necessary production components are:

- SQLite database
- S3 object storage
- generated manifest
- Zooniverse upload script

## 13. Handoff Model

This repository should be easy for partners to run after handoff.

The intended handoff package is:

1. `transcriber_db.db`
2. the upload scripts
3. documented S3 naming assumptions
4. Zooniverse project credentials handled by the partner team
5. a short upload checklist

That keeps the workflow reproducible without depending on student-local file layouts.
