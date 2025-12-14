"""
Parser for ARFA DIAGNOSTIC CENTRE format reports.
"""


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
