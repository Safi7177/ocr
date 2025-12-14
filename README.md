# OCR Image Processor

Simple OCR tool using PaddleOCR to process images and extract text.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the OCR processor:
```bash
python ocr_processor.py
```

## Output

The script will:
- Process all images from the `images/` folder
- Save JSON results in `json_results/` folder (one file per image)
- Save Markdown results in `markdown_results/` folder (one file per image)

Each result file contains:
- Detected text
- Confidence scores
- Bounding box coordinates
- Processing metadata
