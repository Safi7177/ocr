"""
Test script for universal parser with all images.
"""
import json
import os
from pathlib import Path
from parsers import parse_medical_report

def test_universal_parser_all_images():
    """
    Test universal parser with all images present in the images folder.
    Creates test-result files for each image.
    """
    # Define paths
    images_folder = Path("images")
    raw_data_folder = Path("raw_data")
    json_output_folder = Path("json_results")
    
    # Create output folder if it doesn't exist
    json_output_folder.mkdir(exist_ok=True)
    
    # Get all image files
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
    image_files = [f for f in images_folder.iterdir() 
                   if f.suffix.lower() in image_extensions]
    
    if not image_files:
        print(f"No images found in '{images_folder}' folder!")
        return
    
    print(f"Found {len(image_files)} image(s) to test...\n")
    
    # Process each image
    for idx, image_path in enumerate(image_files, 1):
        print(f"[{idx}/{len(image_files)}] Processing: {image_path.name}")
        
        # Find corresponding raw data file
        raw_filename = image_path.stem + "_raw.json"
        raw_path = raw_data_folder / raw_filename
        
        if not raw_path.exists():
            print(f"  [WARNING] Raw data file not found: {raw_path}")
            print(f"  [SKIP] Skipping {image_path.name}\n")
            continue
        
        try:
            # Load raw data
            with open(raw_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            # Extract rec_texts
            rec_texts = []
            if raw_data.get('raw_result') and len(raw_data['raw_result']) > 0:
                first_result = raw_data['raw_result'][0]
                if isinstance(first_result, dict) and 'rec_texts' in first_result:
                    rec_texts = first_result.get('rec_texts', [])
                elif isinstance(first_result, list):
                    # Sometimes rec_texts might be directly in the list
                    rec_texts = first_result
            
            if not rec_texts:
                print(f"  [WARNING] No rec_texts found in raw data")
                print(f"  [SKIP] Skipping {image_path.name}\n")
                continue
            
            print(f"  [INFO] Found {len(rec_texts)} text items")
            
            # Parse using universal parser
            parsed = parse_medical_report(rec_texts)
            
            # Print summary
            patient_id = parsed.get('patient_info', {}).get('patient_id', 'N/A')
            haematology_count = len(parsed.get('haematology_report', []))
            blood_indices_count = len(parsed.get('blood_indices', []))
            
            print(f"  [INFO] Extracted: Patient ID={patient_id}, "
                  f"Haematology tests={haematology_count}, "
                  f"Blood indices={blood_indices_count}")
            
            # Save result with test-result in filename
            output = {
                "image_name": raw_data.get('image_name', image_path.name),
                "image_path": raw_data.get('image_path', str(image_path)),
                "processed_at": raw_data.get('processed_at'),
                **parsed
            }
            
            # Create filename with test-result prefix
            test_result_filename = f"test-result_{image_path.stem}.json"
            test_result_path = json_output_folder / test_result_filename
            
            with open(test_result_path, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            
            print(f"  [OK] Test result saved: {test_result_path}\n")
        
        except Exception as e:
            import traceback
            error_msg = str(e) if str(e) else type(e).__name__
            print(f"  [ERROR] Error processing {image_path.name}: {error_msg}")
            traceback.print_exc()
            print()
    
    print("="*60)
    print("✅ Testing complete! All test-result files saved in json_results folder.")
    print("="*60)


if __name__ == "__main__":
    print("=" * 60)
    print("Universal Parser Test - All Images")
    print("=" * 60)
    print()
    test_universal_parser_all_images()
