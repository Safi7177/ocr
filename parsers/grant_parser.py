"""
Parser for Grant Medical Foundation format reports.
"""


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
