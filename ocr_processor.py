import os
import json
import cv2
from pathlib import Path
from paddleocr import PaddleOCR
from datetime import datetime

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


def detect_report_format(texts):
    """
    Detect the format of the medical report based on keywords.
    Returns: 'parth', 'grant', 'arfa', or 'unknown'
    """
    text_str = " ".join(texts[:50]).upper()  # Check first 50 items
    
    if "PARTH PATHOLOGY" in text_str or "PARTH" in text_str:
        return 'parth'
    elif "GRANT MEDICAL" in text_str or "GRANT" in text_str:
        return 'grant'
    elif "ARFA DIAGNOSTIC" in text_str or "ARFA" in text_str:
        return 'arfa'
    return 'unknown'


def parse_parth_format(texts):
    """
    Parse PARTH PATHOLOGY LABORATORY format (original format).
    """
    parsed_data = {
        "patient_info": {},
        "laboratory_info": {},
        "haematology_report": [],
        "blood_indices": [],
        "morphology": {},
        "footer_info": {}
    }
    
    i = 0
    while i < len(texts):
        text = texts[i]
        
        # Parse Patient ID
        if "Patient ID" in text and i + 1 < len(texts):
            next_text = texts[i + 1]
            if next_text.startswith(":"):
                patient_id = next_text.replace(":", "").strip()
                parsed_data["patient_info"]["patient_id"] = patient_id
            i += 2
            continue
        
        # Parse Collection Date
        if "Collection Date" in text:
            for j in range(i + 1, min(i + 3, len(texts))):
                next_text = texts[j]
                if next_text.startswith(":") or any(char.isdigit() for char in next_text):
                    date_value = next_text.replace(":", "").strip()
                    if date_value:
                        parsed_data["patient_info"]["collection_date"] = date_value
                        i = j + 1
                        break
            else:
                i += 1
            continue
        
        # Parse Reporting Date
        if "Reporting Date" in text:
            for j in range(i + 1, min(i + 3, len(texts))):
                next_text = texts[j]
                if next_text.startswith(":") or any(char.isdigit() for char in next_text):
                    date_value = next_text.replace(":", "").strip()
                    if date_value:
                        parsed_data["patient_info"]["reporting_date"] = date_value
                        i = j + 1
                        break
            else:
                i += 1
            continue
        
        # Parse Laboratory name
        if "PATHOLOGY LABORATORY" in text:
            parsed_data["laboratory_info"]["name"] = "PARTH PATHOLOGY LABORATORY"
            i += 1
            continue
        
        # Parse Reference Doctor
        if "Dr." in text and "Hospital" in text:
            parsed_data["patient_info"]["referring_doctor"] = text
            i += 1
            continue
        
        # Parse HAEMATOLOGY REPORT section
        if "HAEMATOLOGY REPORT" in text:
            i += 1
            while i < len(texts) and texts[i] in ["Test Name", "Observed Value", "Unit", "Reference Range"]:
                i += 1
            
            while i < len(texts):
                test_text = texts[i]
                
                if any(header in test_text for header in ["DIFFERENTIAL COUNT", "PLATELET COUNT", "BLOOD INDICES", "** End of Report"]):
                    break
                
                if test_text.startswith(":") or not test_text or test_text in ["Test Name", "Observed Value", "Unit", "Reference Range"]:
                    i += 1
                    continue
                
                if i + 1 < len(texts) and texts[i + 1].startswith(":"):
                    test_name = test_text
                    value_text = texts[i + 1].replace(":", "").strip()
                    unit = texts[i + 2] if i + 2 < len(texts) else ""
                    ref_range = texts[i + 3] if i + 3 < len(texts) else ""
                    
                    if i + 2 < len(texts) and not any(char.isdigit() or char in "-" for char in texts[i + 2]):
                        unit = ""
                        ref_range = texts[i + 2] if i + 2 < len(texts) else ""
                    
                    parsed_data["haematology_report"].append({
                        "test_name": test_name,
                        "observed_value": value_text,
                        "unit": unit,
                        "reference_range": ref_range
                    })
                    i += 4
                else:
                    i += 1
        
        # Parse DIFFERENTIAL COUNT
        elif "DIFFERENTIAL COUNT" in text:
            i += 1
            while i < len(texts):
                test_text = texts[i]
                
                if any(header in test_text for header in ["PLATELET COUNT", "BLOOD INDICES", "** End of Report"]):
                    break
                
                if test_text.startswith(":") or not test_text:
                    i += 1
                    continue
                
                if "?olymorphs" in test_text or "olymorphs" in test_text.lower():
                    test_text = "Polymorphs"
                
                if i + 1 < len(texts) and texts[i + 1].startswith(":"):
                    test_name = test_text
                    value_text = texts[i + 1].replace(":", "").strip()
                    unit = texts[i + 2] if i + 2 < len(texts) else ""
                    ref_range = texts[i + 3] if i + 3 < len(texts) else ""
                    
                    parsed_data["haematology_report"].append({
                        "test_name": test_name,
                        "observed_value": value_text,
                        "unit": unit,
                        "reference_range": ref_range,
                        "category": "Differential Count"
                    })
                    i += 4
                else:
                    i += 1
        
        # Parse PLATELET COUNT
        elif "PLATELET COUNT" in text:
            i += 1
            if i < len(texts) and texts[i].startswith(":"):
                value_text = texts[i].replace(":", "").strip()
                unit = texts[i + 1] if i + 1 < len(texts) else ""
                ref_range = texts[i + 2] if i + 2 < len(texts) else ""
                
                parsed_data["haematology_report"].append({
                    "test_name": "PLATELET COUNT",
                    "observed_value": value_text,
                    "unit": unit,
                    "reference_range": ref_range
                })
                i += 3
            else:
                i += 1
        
        # Parse BLOOD INDICES
        elif "BLOOD INDICES" in text:
            i += 1
            while i < len(texts):
                test_text = texts[i]
                
                if any(header in test_text for header in ["RBC Morphology", "Platelets on Smear", "** End of Report"]):
                    break
                
                if test_text.startswith(":") or not test_text:
                    i += 1
                    continue
                
                if test_text in ["M.C.H.C.", "H.C.T.", "M.C.V.", "M.C.H.", "R.D.W.", "M.P.V.", "Plateletcrit (PCT)"]:
                    test_name = test_text
                    if i + 1 < len(texts):
                        next_text = texts[i + 1]
                        if next_text.startswith(":"):
                            value_text = next_text.replace(":", "").strip()
                            unit = texts[i + 2] if i + 2 < len(texts) else ""
                            ref_range = texts[i + 3] if i + 3 < len(texts) else ""
                            i += 4
                        else:
                            value_text = next_text.strip()
                            unit = texts[i + 2] if i + 2 < len(texts) else ""
                            ref_range = texts[i + 3] if i + 3 < len(texts) else ""
                            i += 4
                        
                        parsed_data["blood_indices"].append({
                            "test_name": test_name,
                            "observed_value": value_text,
                            "unit": unit,
                            "reference_range": ref_range
                        })
                    else:
                        i += 1
                elif i + 1 < len(texts) and texts[i + 1].startswith(":"):
                    test_name = test_text
                    value_text = texts[i + 1].replace(":", "").strip()
                    unit = texts[i + 2] if i + 2 < len(texts) else ""
                    ref_range = texts[i + 3] if i + 3 < len(texts) else ""
                    
                    parsed_data["blood_indices"].append({
                        "test_name": test_name,
                        "observed_value": value_text,
                        "unit": unit,
                        "reference_range": ref_range
                    })
                    i += 4
                else:
                    i += 1
        
        # Parse Morphology
        elif "RBC Morphology" in text:
            if i + 1 < len(texts) and texts[i + 1].startswith(":"):
                morphology1 = texts[i + 1].replace(":", "").strip()
                morphology2 = texts[i + 2] if i + 2 < len(texts) else ""
                parsed_data["morphology"]["rbc_morphology"] = f"{morphology1} {morphology2}".strip()
                i += 3
            else:
                i += 1
        elif "Platelets on Smear" in text:
            if i + 1 < len(texts):
                parsed_data["morphology"]["platelets_on_smear"] = texts[i + 1]
                i += 2
            else:
                i += 1
        
        # Parse Footer info
        elif "Dr." in text and "Rajput" in text:
            parsed_data["footer_info"]["doctor_name"] = text
            if i + 1 < len(texts):
                parsed_data["footer_info"]["qualification"] = texts[i + 1]
            if i + 2 < len(texts) and "Registration" in texts[i + 2]:
                parsed_data["footer_info"]["registration"] = texts[i + 2]
            i += 3
        elif "Lab Technician" in text:
            parsed_data["footer_info"]["lab_technician"] = text
            i += 1
        else:
            i += 1
    
    return parsed_data


def parse_grant_format(texts):
    """
    Parse Grant Medical Foundation format.
    """
    parsed_data = {
        "patient_info": {},
        "laboratory_info": {},
        "haematology_report": [],
        "blood_indices": [],
        "morphology": {},
        "footer_info": {}
    }
    
    i = 0
    while i < len(texts):
        text = texts[i]
        
        # Parse Laboratory name
        if "Grant Medical Foundation" in text or "Grant Medical" in text:
            parsed_data["laboratory_info"]["name"] = "Grant Medical Foundation"
            i += 1
            continue
        
        # Parse Received Date
        if "Received Date" in text and i + 1 < len(texts):
            date_value = texts[i + 1].strip()
            if date_value:
                parsed_data["patient_info"]["received_date"] = date_value
            i += 2
            continue
        
        # Parse Report Date
        if "Report Date" in text and i + 1 < len(texts):
            date_value = texts[i + 1].strip()
            if date_value:
                parsed_data["patient_info"]["report_date"] = date_value
            i += 2
            continue
        
        # Parse Lab No/Result No
        if "Lab No/Result No" in text and i + 1 < len(texts):
            lab_no = texts[i + 1].strip()
            if lab_no:
                parsed_data["patient_info"]["lab_no"] = lab_no
            i += 2
            continue
        
        # Parse Referred By Dr.
        if "Referred By Dr." in text and i + 1 < len(texts):
            doctor = texts[i + 1].replace(":", "").strip()
            if doctor:
                parsed_data["patient_info"]["referring_doctor"] = doctor
            i += 2
            continue
        
        # Parse Specimen
        if "Specimen" in text and i + 1 < len(texts):
            specimen = texts[i + 1].replace(":", "").strip()
            if specimen:
                parsed_data["patient_info"]["specimen"] = specimen
            i += 2
            continue
        
        # Parse Ward / Bed
        if "Ward / Bed" in text and i + 1 < len(texts):
            ward = texts[i + 1].replace(":", "").strip()
            if ward:
                parsed_data["patient_info"]["ward_bed"] = ward
            i += 2
            continue
        
        # Parse HAEMATOLOGY section
        if "DEPARTMENT OF LABORATORY MEDICINE-HAEMATOLOGY" in text or "HAEMATOLOGY" in text:
            i += 1
            # Skip headers
            while i < len(texts) and texts[i] in ["Investigation", "Result", "Units", "Biological Reference Interval", "Haemogram Report"]:
                i += 1
            
            # Parse test results
            in_differential_count = False
            while i < len(texts):
                test_text = texts[i]
                
                # Stop at footer
                if "Printed By" in test_text or "Printed On" in test_text:
                    break
                
                # Check for Differential Count section
                if "Differential Count" in test_text:
                    in_differential_count = True
                    i += 1
                    continue
                
                # Skip method lines
                if "Method :" in test_text or "MethOd :" in test_text:
                    i += 1
                    continue
                
                # Skip empty or colon-only
                if not test_text or test_text == ":" or test_text.startswith(":"):
                    i += 1
                    continue
                
                # Check if this is a test name followed by ": value"
                if i + 1 < len(texts) and texts[i + 1].startswith(":"):
                    test_name = test_text
                    value_text = texts[i + 1].replace(":", "").strip()
                    
                    # Get unit and reference range
                    unit = ""
                    ref_range = ""
                    if i + 2 < len(texts):
                        unit = texts[i + 2].strip()
                    if i + 3 < len(texts):
                        ref_range = texts[i + 3].strip()
                    
                    # Determine if it's haematology or blood indices
                    test_lower = test_name.lower()
                    if any(x in test_lower for x in ["mcv", "mch", "mchc", "rdw", "hct", "hematocrit"]):
                        parsed_data["blood_indices"].append({
                            "test_name": test_name,
                            "observed_value": value_text,
                            "unit": unit,
                            "reference_range": ref_range
                        })
                    else:
                        test_entry = {
                            "test_name": test_name,
                            "observed_value": value_text,
                            "unit": unit,
                            "reference_range": ref_range
                        }
                        if in_differential_count:
                            test_entry["category"] = "Differential Count"
                        parsed_data["haematology_report"].append(test_entry)
                    
                    i += 4
                else:
                    i += 1
        
        # Parse Footer
        elif "Printed By" in text:
            if i + 1 < len(texts):
                parsed_data["footer_info"]["printed_by"] = texts[i + 1].replace(":", "").strip()
            if i + 2 < len(texts) and "Printed On" in texts[i + 2]:
                if i + 3 < len(texts):
                    parsed_data["footer_info"]["printed_on"] = texts[i + 3].strip()
            i += 4
        else:
            i += 1
    
    return parsed_data


def parse_arfa_format(texts):
    """
    Parse ARFA DIAGNOSTIC CENTRE format.
    """
    parsed_data = {
        "patient_info": {},
        "laboratory_info": {},
        "haematology_report": [],
        "blood_indices": [],
        "morphology": {},
        "footer_info": {}
    }
    
    i = 0
    while i < len(texts):
        text = texts[i]
        
        # Parse Laboratory name
        if "ARFA DIAGNOSTIC CENTRE" in text or "ARFA" in text:
            parsed_data["laboratory_info"]["name"] = "ARFA DIAGNOSTIC CENTRE"
            i += 1
            continue
        
        # Parse User
        if "User:" in text and i + 1 < len(texts):
            parsed_data["patient_info"]["user"] = texts[i + 1].strip()
            i += 2
            continue
        
        # Parse PHCR #
        if "PHCR #:" in text and i + 1 < len(texts):
            parsed_data["laboratory_info"]["phcr_number"] = texts[i + 1].strip()
            i += 2
            continue
        
        # Parse Booking No.
        if "Booking No.:" in text and i + 1 < len(texts):
            parsed_data["patient_info"]["booking_no"] = texts[i + 1].strip()
            i += 2
            continue
        
        # Parse Patient No.
        if "Patient No.:" in text and i + 1 < len(texts):
            parsed_data["patient_info"]["patient_no"] = texts[i + 1].strip()
            i += 2
            continue
        
        # Parse Patient Name
        if "Patient Name:" in text and i + 1 < len(texts):
            parsed_data["patient_info"]["patient_name"] = texts[i + 1].strip()
            i += 2
            continue
        
        # Parse Sample Collected
        if "Sample Collected:" in text and i + 1 < len(texts):
            parsed_data["patient_info"]["sample_collected"] = texts[i + 1].strip()
            i += 2
            continue
        
        # Parse Age/Sex
        if "Age/Sex:" in text and i + 1 < len(texts):
            parsed_data["patient_info"]["age_sex"] = texts[i + 1].strip()
            i += 2
            continue
        
        # Parse Test Booked
        if "Test Booked:" in text and i + 1 < len(texts):
            parsed_data["patient_info"]["test_booked"] = texts[i + 1].strip()
            i += 2
            continue
        
        # Parse Results Saved
        if "Results Saved:" in text and i + 1 < len(texts):
            parsed_data["patient_info"]["results_saved"] = texts[i + 1].strip()
            i += 2
            continue
        
        # Parse Mobile
        if "Mobile:" in text and i + 1 < len(texts):
            parsed_data["patient_info"]["mobile"] = texts[i + 1].strip()
            i += 2
            continue
        
        # Parse Collection Point
        if "Collection Point:" in text and i + 1 < len(texts):
            parsed_data["patient_info"]["collection_point"] = texts[i + 1].strip()
            i += 2
            continue
        
        # Parse Consultant
        if "Consultant:" in text and i + 1 < len(texts):
            parsed_data["patient_info"]["consultant"] = texts[i + 1].strip()
            i += 2
            continue
        
        # Parse HAEMATOLOGY section
        if "HAEMATOLOGY" in text:
            i += 1
            # Skip column headers
            while i < len(texts) and texts[i] in ["Test", "Normal Range", "Unit", "Result", "CBC With ESR"]:
                i += 1
            
            # Parse test results - ARFA format has mixed order
            # Pattern: Test Name, [Normal Range (may have gender)], Unit, Result
            while i < len(texts):
                test_text = texts[i]
                
                # Stop at footer sections
                if "Electronically Generated" in test_text or ("Dr." in test_text and i > 50) or "www." in test_text:
                    break
                
                # Skip empty
                if not test_text or test_text.strip() == "":
                    i += 1
                    continue
                
                # Common test names in ARFA format
                test_names = [
                    "Hemoglobin (HB)", "Hematocrit (HCT)", "Red Blood Cell (RBC)",
                    "Mean Cell Volume (MCV)", "Mean Cell Hemoglobin (MCH)",
                    "Mean Cell Hb Conc (MCHC)", "White Blood Cell (WBC/TLC)",
                    "Neutrophils", "Lymphocytes", "Monocytes", "Eosinophil", "Basophils",
                    "Platelets Count"
                ]
                
                # Check if current text is a test name
                is_test_name = any(tn in test_text for tn in test_names)
                
                if is_test_name:
                    test_name = test_text
                    value = ""
                    unit = ""
                    ref_range = ""
                    
                    # Look ahead to find value, unit, and range
                    # ARFA format: Test Name -> [Range/Gender Range] -> Unit -> Result
                    j = i + 1
                    found_range = False
                    
                    while j < min(i + 6, len(texts)):
                        next_text = texts[j]
                        
                        # Skip gender-specific ranges (Female:, Male:)
                        if "Female:" in next_text or "Male:" in next_text:
                            j += 1
                            continue
                        
                        # Check if it's a range (contains "-" and digits)
                        if "-" in next_text and any(char.isdigit() for char in next_text) and not found_range:
                            ref_range = next_text.strip()
                            found_range = True
                            j += 1
                            continue
                        
                        # Check if it's a unit
                        if any(x in next_text for x in ["g/dl", "%", "fl", "pg", "*10", "/ul", "/l"]) and not unit:
                            unit = next_text.strip()
                            j += 1
                            continue
                        
                        # Check if it's a result value (contains digits, may have ↓ or ↑)
                        if any(char.isdigit() for char in next_text) and not value:
                            # Make sure it's not a range or unit
                            if "-" not in next_text and not any(x in next_text for x in ["g/dl", "%", "fl", "pg", "*10", "/"]):
                                value = next_text.strip()
                                j += 1
                                # After finding value, check if next items are unit/range if not found
                                if j < len(texts) and not unit:
                                    potential_unit = texts[j]
                                    if any(x in potential_unit for x in ["g/dl", "%", "fl", "pg", "*10", "/"]):
                                        unit = potential_unit.strip()
                                        j += 1
                                if j < len(texts) and not ref_range:
                                    potential_range = texts[j]
                                    if "-" in potential_range and any(char.isdigit() for char in potential_range):
                                        ref_range = potential_range.strip()
                                        j += 1
                                break
                        
                        j += 1
                    
                    # Determine category
                    test_lower = test_name.lower()
                    if any(x in test_lower for x in ["mcv", "mch", "mchc", "hct", "hematocrit", "mean cell"]):
                        parsed_data["blood_indices"].append({
                            "test_name": test_name,
                            "observed_value": value,
                            "unit": unit,
                            "reference_range": ref_range
                        })
                    else:
                        parsed_data["haematology_report"].append({
                            "test_name": test_name,
                            "observed_value": value,
                            "unit": unit,
                            "reference_range": ref_range
                        })
                    
                    i = j
                else:
                    i += 1
        
        # Parse Footer (doctors, etc.)
        elif "Dr." in text and i + 1 < len(texts):
            # Collect doctor information
            if "doctor_name" not in parsed_data["footer_info"]:
                parsed_data["footer_info"]["doctor_name"] = text
            i += 1
        else:
            i += 1
    
    return parsed_data


def parse_medical_report(rec_texts):
    """
    Parse medical report from OCR text and extract structured fields.
    Supports multiple report formats: PARTH, Grant Medical, ARFA.
    """
    if not rec_texts:
        return {
            "patient_info": {},
            "laboratory_info": {},
            "haematology_report": [],
            "blood_indices": [],
            "morphology": {},
            "footer_info": {}
        }
    
    # Convert to list of strings for easier processing
    texts = [str(t).strip() for t in rec_texts if t and str(t).strip()]
    
    # Detect format
    format_type = detect_report_format(texts)
    
    # Route to appropriate parser
    if format_type == 'parth':
        return parse_parth_format(texts)
    elif format_type == 'grant':
        return parse_grant_format(texts)
    elif format_type == 'arfa':
        return parse_arfa_format(texts)
    else:
        # Try to parse as generic/unknown format
        # Fallback to PARTH format parser
        return parse_parth_format(texts)


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
