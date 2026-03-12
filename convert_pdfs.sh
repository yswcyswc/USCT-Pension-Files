#!/bin/bash

PDF_DIR="dataset/pdf"
IMG_DIR="dataset/images"

mkdir -p "$IMG_DIR"

for pdf_path in "$PDF_DIR"/*.pdf; do
    # Get filename without extension, e.g. Robinson_Lucius
    name=$(basename "$pdf_path" .pdf)

    out_folder="$IMG_DIR/$name"
    mkdir -p "$out_folder"

    # Convert all pages to PNG at 300 DPI
    # Output files will be named: Robinson_Lucius-1.png, Robinson_Lucius-2.png, etc.
    pdftoppm -png -r 300 "$pdf_path" "$out_folder/$name"

    echo "Converted: $name"
done

echo "Done. Images saved to $IMG_DIR"