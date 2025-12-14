import os
import json
import cv2
from pathlib import Path
from paddleocr import PaddleOCR
from datetime import datetime
from parsers import parse_medical_report

def preprocess_image(img):
    """
    Preprocess image for better OCR results.
    For WhatsApp images, upscaling and thresholding can help.
    """
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Upscale image (important for low-resolution WhatsApp images)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    
    # Apply adaptive threshold for better text contrast
    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31, 2
    )
    
    return thresh

def process_images_with_ocr():
    """
    Process all images in the 'images' folder using PaddleOCR
    and save results in JSON and Markdown formats for each image.
    """
    # Initialize PaddleOCR (use_lang='en' for English, can be changed)
    print("Initializing PaddleOCR...")
    ocr = PaddleOCR(
        lang='en',
        use_textline_orientation=True,
        det_db_box_thresh=0.5,
        det_db_unclip_ratio=1.5
    )
    print("PaddleOCR initialized successfully!")
    
    # Define paths
    images_folder = Path("images")
    json_output_folder = Path("json_results")
    markdown_output_folder = Path("markdown_results")
    raw_data_folder = Path("raw_data")
    
    # Create output folders if they don't exist
    json_output_folder.mkdir(exist_ok=True)
    markdown_output_folder.mkdir(exist_ok=True)
    raw_data_folder.mkdir(exist_ok=True)
    
    # Get all image files
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
    image_files = [f for f in images_folder.iterdir() 
                   if f.suffix.lower() in image_extensions]
    
    if not image_files:
        print(f"No images found in '{images_folder}' folder!")
        return
    
    print(f"\nFound {len(image_files)} image(s) to process...\n")
    
    # Process each image
    for idx, image_path in enumerate(image_files, 1):
        print(f"[{idx}/{len(image_files)}] Processing: {image_path.name}")
        
        try:
            # Read image
            img = cv2.imread(str(image_path))
            if img is None:
                print(f"  [ERROR] Could not read image: {image_path.name}")
                continue
            
            # Try OCR on original image first (often works better)
            result = ocr.ocr(img)
            
            # If no results or very few detections, try with preprocessing
            if not result or not result[0] or len(result[0]) < 2:
                print(f"  [INFO] Trying with preprocessing...")
                processed_img = preprocess_image(img)
                result = ocr.ocr(processed_img)
            
            # Save raw OCR result to file for inspection
            raw_data = {
                "image_name": image_path.name,
                "image_path": str(image_path),
                "processed_at": datetime.now().isoformat(),
                "raw_result": result
            }
            raw_filename = image_path.stem + "_raw.json"
            raw_path = raw_data_folder / raw_filename
            with open(raw_path, 'w', encoding='utf-8') as f:
                json.dump(raw_data, f, indent=2, ensure_ascii=False, default=str)
            print(f"  [INFO] Raw data saved: {raw_path}")
            
            # Extract structured fields from medical report
            structured_data = {}
            if result and isinstance(result, list) and len(result) > 0:
                first_item = result[0]
                if isinstance(first_item, dict) and "rec_texts" in first_item:
                    rec_texts = first_item.get("rec_texts", [])
                    structured_data = parse_medical_report(rec_texts)
                    patient_id = structured_data.get('patient_info', {}).get('patient_id', 'N/A')
                    haematology_count = len(structured_data.get('haematology_report', []))
                    blood_indices_count = len(structured_data.get('blood_indices', []))
                    print(f"  [INFO] Extracted: Patient ID={patient_id}, Haematology tests={haematology_count}, Blood indices={blood_indices_count}")
            
            # Create final output with only structured fields
            final_output = {
                "image_name": image_path.name,
                "image_path": str(image_path),
                "processed_at": datetime.now().isoformat(),
                **structured_data  # Unpack all structured fields directly
            }
            
            # Save JSON result
            json_filename = image_path.stem + ".json"
            json_path = json_output_folder / json_filename
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(final_output, f, indent=2, ensure_ascii=False)
            print(f"  [OK] JSON saved: {json_path}")
            
            # Generate Markdown result
            markdown_content = generate_markdown(final_output)
            
            # Save Markdown result
            md_filename = image_path.stem + ".md"
            md_path = markdown_output_folder / md_filename
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            print(f"  [OK] Markdown saved: {md_path}")
        
        except Exception as e:
            import traceback
            error_msg = str(e) if str(e) else type(e).__name__
            print(f"  [ERROR] Error processing {image_path.name}: {error_msg}")
            # Print full traceback for debugging (comment out in production)
            # traceback.print_exc()
    
    print(f"\n[OK] Processing complete! Results saved in:")
    print(f"  - JSON: '{json_output_folder}'")
    print(f"  - Markdown: '{markdown_output_folder}'")
    print(f"  - Raw data: '{raw_data_folder}'")


def generate_markdown(data):
    """
    Generate Markdown formatted output from structured data.
    """
    md = f"# Medical Report: {data['image_name']}\n\n"
    md += f"**Image Path:** `{data['image_path']}`\n\n"
    md += f"**Processed At:** {data['processed_at']}\n\n"
    
    # Patient Info
    if data.get('patient_info'):
        md += "## Patient Information\n\n"
        for key, value in data['patient_info'].items():
            md += f"- **{key.replace('_', ' ').title()}:** {value}\n"
        md += "\n"
    
    # Laboratory Info
    if data.get('laboratory_info'):
        md += "## Laboratory Information\n\n"
        for key, value in data['laboratory_info'].items():
            md += f"- **{key.replace('_', ' ').title()}:** {value}\n"
        md += "\n"
    
    # Haematology Report
    if data.get('haematology_report'):
        md += "## Haematology Report\n\n"
        md += "| Test Name | Observed Value | Unit | Reference Range |\n"
        md += "|-----------|----------------|------|-----------------|\n"
        for test in data['haematology_report']:
            test_name = test.get('test_name', '').replace('|', '\\|')
            value = test.get('observed_value', '').replace('|', '\\|')
            unit = test.get('unit', '').replace('|', '\\|')
            ref_range = test.get('reference_range', '').replace('|', '\\|')
            md += f"| {test_name} | {value} | {unit} | {ref_range} |\n"
        md += "\n"
    
    # Blood Indices
    if data.get('blood_indices'):
        md += "## Blood Indices\n\n"
        md += "| Test Name | Observed Value | Unit | Reference Range |\n"
        md += "|-----------|----------------|------|-----------------|\n"
        for test in data['blood_indices']:
            test_name = test.get('test_name', '').replace('|', '\\|')
            value = test.get('observed_value', '').replace('|', '\\|')
            unit = test.get('unit', '').replace('|', '\\|')
            ref_range = test.get('reference_range', '').replace('|', '\\|')
            md += f"| {test_name} | {value} | {unit} | {ref_range} |\n"
        md += "\n"
    
    # Morphology
    if data.get('morphology'):
        md += "## Morphology\n\n"
        for key, value in data['morphology'].items():
            md += f"- **{key.replace('_', ' ').title()}:** {value}\n"
        md += "\n"
    
    # Footer Info
    if data.get('footer_info'):
        md += "## Footer Information\n\n"
        for key, value in data['footer_info'].items():
            md += f"- **{key.replace('_', ' ').title()}:** {value}\n"
        md += "\n"
    
    return md


if __name__ == "__main__":
    print("=" * 60)
    print("PaddleOCR Image Processor")
    print("=" * 60)
    process_images_with_ocr()
