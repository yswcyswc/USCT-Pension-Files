# Part 4. Zooniverse Workflow Design

## Technical Design Document


## 1. Overview

### Core Pipeline

1. Convert scanned PDFs into page-level images
2. Download the generated AI transcriptions for each page
3. Build a manifest CSV linking images to transcriptions
4. Upload images and manifest to Zooniverse as subjects
5. Volunteers correct errors, especially names
6. Export and aggregate corrected transcriptions for research use

### Scale

Thinking about the numbers:

| Metric | Value |
|--------|-------|
| PDFs | 200 |
| Average pages per PDF | 150 |
| Total pages | ~30,000 |
| Classifications per page | 5 volunteers |
| Total classifications | ~150,000 |
| PDF page range | 26 to 300 pages per file |

Individual PDFs range from 26 to 300 pages. The pipeline must handle batch processing of the full collection without manual intervention at each step.

**Does Zooniverse support this scale?** Yes, with 2 constraints to plan around before upload begins.

- Subject limit

  - Zooniverse user accounts can upload 10,000 subjects by default, but this limit can be increased by requesting a higher quota from the Zooniverse team.
  - Because the dataset contains around 30,000 pages, the project exceeds the default limit and a limit increase should be requested before beginning the upload process.
  - The dataset should not be uploaded as a single large subject set. Instead, it should be divided into multiple subject sets, currently planned as one set per PDF.
  - Smaller subject sets typically complete and retire faster, which helps maintain volunteer engagement and allows corrected transcriptions to become available earlier.

- Image file size

  - Zooniverse enforces a strict maximum image size of 1 MB per image, while a full-page PNG at 300 DPI will typically be between 3 MB and 8 MB, which exceeds the allowed upload limit.
  - All images must therefore be compressed before upload.
  - The recommended approach is to convert the images to JPEG at around 65% quality, which testing on comparable archival projects shows produces no visible deterioration when enlarged on a large monitor.
  - This compression step should be inserted into the pipeline between the `pdftoppm` output stage and the Zooniverse upload stage.

- Upload method

  - The browser uploader is intended for small projects and should only be used in batches of about 1,000 subjects.
  - With roughly 30,000 pages, the browser uploader is not practical for this dataset.
  - For projects larger than 1,000 subjects, Zooniverse supports automated batch uploads through the Panoptes command-line interface and the Panoptes Python client.
  - These tools allow subjects to be uploaded programmatically and are the appropriate approach for managing this dataset.

<!-- ## 2. Goals

Primary Goals

- Enable efficient transcription validation of archival documents
- Prioritize accuracy of names and key entities
- Combine AI and crowd verification
- Support large-scale batch processing

Secondary Goals

- Groupings (not sure at this stage...)
- Maintain traceability between PDFs, pages, and outputs
- Minimize manual data preparation
- Enable reproducible pipeline execution -->

### System Architecture

Pipeline Overview
![Pipeline Workflow](assets/workflow.png)

## 4. Data Model

### 4.1 Subject Definition

In Zooniverse, **1 subject = 1 page image**. Each page from each PDF becomes one subject.

| PDF | Page | Image |
|-----|------|-------|
| Robinson_Lucius.pdf | 1 | Robinson_Lucius-1.png |
| Robinson_Lucius.pdf | 2 | Robinson_Lucius-2.png |

### 4.2 File Structure

```
dataset/
    pdf/
        Robinson_Lucius.pdf
        Smith_John.pdf

    images/
        Robinson_Lucius/
            Robinson_Lucius-1.png
            Robinson_Lucius-2.png
        Smith_John/
            Smith_John-1.png
            Smith_John-2.png

    ai_transcripts/
        Robinson_Lucius/
            Robinson_Lucius-1.txt
            Robinson_Lucius-2.txt

    manifest.csv
```

## 5. PDF to Image Conversion

### Tool: pdftoppm (Poppler)

`pdftoppm` converts each PDF page into a PNG image. It is part of the Poppler utilities package and runs from the command line.

### Installation

On Ubuntu / WSL:

```bash
sudo apt install poppler-utils
```

On Windows (via Scoop):

```bash
scoop install poppler
```

### Single File — Manual Command

This is the basic form used to convert one PDF. The command below was used during initial testing:

```bash
pdftoppm -png -r 300 "Robinson, Lucius test.pdf" page
```

Explanation of flags:

| Flag | Meaning |
|------|---------|
| `-png` | Output format is PNG |
| `-r 300` | Resolution: 300 DPI (suitable for archival documents) |
| `"Robinson, Lucius test.pdf"` | Input PDF (quotes required when filename has spaces) |
| `page` | Output filename prefix — produces page-1.png, page-2.png, etc. |

Output from the command above:

```
page-1.png
page-2.png
page-3.png
...
```

### Batch Conversion — All PDFs in a Folder

For the full dataset, a shell script loops over every PDF in the `pdf/` directory and converts each one into its own subfolder under `images/`.

**Bash script (Linux / WSL) — `convert_pdfs.sh`:**
See bash convert_pdfs.sh file.


**Example terminal output:**

```
Converted: Robinson_Lucius
Converted: Smith_John
Done. Images saved to dataset/images
```

**Example files produced:**

```
dataset/images/Robinson_Lucius/Robinson_Lucius-1.png
dataset/images/Robinson_Lucius/Robinson_Lucius-2.png
dataset/images/Smith_John/Smith_John-1.png
dataset/images/Smith_John/Smith_John-2.png
```

### Naming Convention

`pdftoppm` appends a hyphen and page number to the prefix you supply. For a prefix of `Robinson_Lucius`, the output is:

```
Robinson_Lucius-1.png
Robinson_Lucius-2.png
...
Robinson_Lucius-26.png
```

This naming is used consistently throughout the rest of the pipeline — in the manifest CSV, AI transcript filenames, and Zooniverse subject metadata.

### Notes on Resolution

300 DPI is recommended for handwritten archival documents. Lower resolutions may be used if storage or upload time is a concern, but may reduce transcription accuracy.

| Resolution | Use case |
|------------|----------|
| 150 DPI | Draft / fast processing |
| 300 DPI | Standard archival quality (recommended) |
| 600 DPI | High detail, large file sizes |

## 6. AI Transcription Generation

An external research interface generates AI transcriptions for each page image. The transcript for each page is saved as a `.txt` file with the same base name as the image.

**Mapping rule:** `Robinson_Lucius-1.png` maps to `Robinson_Lucius-1.txt`

**Output structure:**

```
ai_transcripts/
    Robinson_Lucius/
        Robinson_Lucius-1.txt
        Robinson_Lucius-2.txt
    Smith_John/
        Smith_John-1.txt
        Smith_John-2.txt
```

## 7. Manifest CSV

Zooniverse requires a manifest CSV describing all uploaded subjects. Each row is one page image and links to its metadata and AI transcript. The manifest must be a CSV file — Zooniverse does not accept Excel's `.xlsx` format. The first column must contain the image filename exactly as it appears in the upload; any mismatch between manifest filenames and actual image filenames will cause an upload error. Each subject set must have its own manifest.

### Building the Manifest — `build_manifest.py`

Run from the project root:

```bash
python build_manifest.py
```

**Example terminal output:**

```
Manifest written: 30000 subjects
```

**Example manifest.csv:**

```csv
image,page,pdf,ai_text
Robinson_Lucius-1.png,1,Robinson_Lucius,dataset/ai_transcripts/Robinson_Lucius/Robinson_Lucius-1.txt
Robinson_Lucius-2.png,2,Robinson_Lucius,dataset/ai_transcripts/Robinson_Lucius/Robinson_Lucius-2.txt
Smith_John-1.png,1,Smith_John,dataset/ai_transcripts/Smith_John/Smith_John-1.txt
```

## 8. Upload to Zooniverse

Subjects are uploaded into Subject Sets using the Panoptes Python client. The Panoptes CLI and Python client are both officially supported by Zooniverse for teams with more than 1,000 subjects to upload, and offer equivalent functionality.

### Installation

```bash
pip install panoptes-client
```

### Upload Script — `upload_subjects.py`

```python
todo
```

Run from the project root:

```bash
python upload_subjects.py
```

**Example terminal output:**

```
Uploaded: Robinson_Lucius-1.png
Uploaded: Robinson_Lucius-2.png
...
Upload complete.
```

### Manual Upload (Alternative)

For small batches only (under 1,000 subjects), subjects can be uploaded through the browser:

Project Builder > Subject Sets > New Subject Set > Upload images and manifest

The manifest CSV must be uploaded alongside the images. This method is not suitable for the full dataset at 30,000 pages.

## 9. Zooniverse Workflow Design

Only one workflow is needed for the entire project. A workflow is the sequence of tasks a volunteer completes when presented with a subject. Tasks should be simple enough to complete with minimal guidance, and each task should contribute useful data even if the volunteer does not finish the entire workflow.

### Task 1: Correct AI Transcription

Display the page image alongside the AI-generated transcription.

**Volunteer instructions:**

1. Copy the AI transcription into the text editor
2. Correct any mistakes
3. Pay special attention to names
4. Preserve original wording and spelling

**Volunteer response field:** Corrected transcription

### Task 2: Name Verification

**Question:** Are all personal names correctly transcribed?

**Answer options:** Yes / No / Unsure

**Optional task:** Highlight names directly on the image.

## 10. Classification Process

Each subject receives classifications from multiple volunteers to reduce the impact of individual errors. A subject is retired once it reaches the classification retirement limit set for the workflow — the number of classifications at which Zooniverse stops showing it to new volunteers. This limit is configured in the Project Builder.

**Example — Robinson_Lucius-1.png:**

- Volunteer A submits corrected transcription
- Volunteer B submits corrected transcription
- Volunteer C submits corrected transcription
- Volunteer D submits corrected transcription
- Volunteer E submits corrected transcription

**Consensus methods:** majority voting, manual expert review, confidence scoring

## 11. Data Export

Classification data is exported from:

Project Builder > Lab > Data Exports > Request Classification Export

The export is a CSV file with one row per classification submitted. Zooniverse also provides a separate subject export (one row per subject uploaded) and a workflow export. All exports are requested from the same Data Exports tab and generated asynchronously — large exports may take time to prepare.

**Classification export fields:** classification_id, user_name, user_id, user_ip, workflow_id, workflow_name, workflow_version, created_at, gold_standard, expert, metadata, annotations, subject_data, subject_ids

## 12. Post-Processing

### Processing Steps

1. Parse the classification export CSV
2. Extract the corrected transcription from each annotation
3. Group classifications by subject (page)
4. Aggregate multiple responses using the chosen consensus method
5. Write the final validated transcript for each page

### Post-Processing Script — `postprocess.py`

```python
todo
```

Run from the project root:

```bash
python postprocess.py
```

**Output structure:**

```
dataset/validated_transcripts/
    Robinson_Lucius/
        Robinson_Lucius-1.txt
        Robinson_Lucius-2.txt
    Smith_John/
        Smith_John-1.txt
        Smith_John-2.txt
```

## 13. Quality Control

- Multiple independent classifications per page
- Consensus aggregation across volunteer responses
- Expert spot checks on flagged pages
- Name verification task surfacing uncertain names

## 14. Risks

| Risk | Mitigation |
|------|------------|
| Filename mismatches between images and transcripts | Consistent naming convention enforced at conversion step |
todo

## 15. Future Improvements

todo

## 16. Summary

todo
