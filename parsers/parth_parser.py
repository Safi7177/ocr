"""
Parser for PARTH PATHOLOGY LABORATORY format reports.
"""


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
