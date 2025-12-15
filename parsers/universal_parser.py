"""
Universal parser for blood reports that can handle any format.
Uses predefined common fields and intelligent pattern matching.
"""

import re
from typing import List, Dict, Any, Optional


# Predefined common fields for blood reports
COMMON_PATIENT_FIELDS = {
    'patient_id': ['patient id', 'patient no', 'lab no', 'result no', 'phcr', 'booking no'],
    'patient_name': ['name', 'patient name', 'user'],
    'age': ['age'],
    'gender': ['gender', 'sex'],
    'age_gender': ['age/gender', 'age/sex'],
    'collection_date': ['collection date', 'sample collected', 'received date'],
    'report_date': ['report date', 'reporting date', 'results saved', 'release date'],
    'referring_doctor': ['referred by', 'referring doctor', 'consultant', 'dr.'],
    'phone': ['phone', 'mobile', 'phone no'],
    'specimen': ['specimen'],
    'ward_bed': ['ward', 'bed'],
    'report_id': ['report id'],
    'passport_no': ['passport no'],
}

COMMON_LAB_FIELDS = {
    'name': ['laboratory', 'lab', 'diagnostic', 'pathology', 'medical', 'foundation', 'clinic', 'centre'],
    'address': ['address'],
    'phone': ['phone', 'tel', 'telephone'],
    'email': ['email', '@'],
    'website': ['www', 'http', 'https'],
    'phcr_number': ['phcr'],
}

COMMON_TEST_NAMES = {
    # Haematology tests
    'haemoglobin': ['haemoglobin', 'hemoglobin', 'hb', 'hgb'],
    'wbc': ['wbc', 'white blood cell', 'total leucocyte count', 'total w.b.c.', 'total wbc', 'leucocyte count'],
    'rbc': ['rbc', 'red blood cell', 'r.b.c.', 'rbc count'],
    'platelet': ['platelet', 'platelet count', 'plt'],
    'neutrophils': ['neutrophils', 'polymorphs', 'neutrophil'],
    'lymphocytes': ['lymphocytes', 'lymphocyte'],
    'eosinophils': ['eosinophils', 'eosinophil'],
    'monocytes': ['monocytes', 'monocyte'],
    'basophils': ['basophils', 'basophil'],
    'absolute_neutrophils': ['absolute neutrophil', 'absolute neutrophils'],
    'absolute_lymphocytes': ['absolute lymphocyte', 'absolute lymphocytes'],
    'absolute_eosinophils': ['absolute eosinophil', 'absolute eosinophils'],
    'absolute_monocytes': ['absolute monocyte', 'absolute monocytes'],
    'absolute_basophils': ['absolute basophil', 'absolute basophils'],
    
    # Blood indices
    'mcv': ['mcv', 'm.c.v.', 'mean cell volume'],
    'mch': ['mch', 'm.c.h.', 'mean cell hemoglobin'],
    'mchc': ['mchc', 'm.c.h.c.', 'mean cell hb conc', 'mean cell hemoglobin concentration'],
    'hct': ['hct', 'h.c.t.', 'hematocrit', 'haematocrit'],
    'rdw': ['rdw', 'r.d.w.', 'rdw-cv', 'rdw-sd'],
    'mpv': ['mpv', 'm.p.v.', 'mean platelet volume'],
    'pct': ['pct', 'plateletcrit'],
    'pdw': ['pdw'],
}

COMMON_MORPHOLOGY_FIELDS = {
    'rbc_morphology': ['rbc morphology', 'red cell morphology'],
    'platelets_on_smear': ['platelets on smear', 'platelet on smear'],
    'wbc_morphology': ['wbc morphology', 'white cell morphology'],
}

COMMON_FOOTER_FIELDS = {
    'doctor_name': ['dr.', 'doctor'],
    'qualification': ['mbbs', 'md', 'dcp', 'phd'],
    'registration': ['registration', 'reg no', 'reg. no'],
    'lab_technician': ['lab technician', 'technician'],
    'printed_by': ['printed by'],
    'printed_on': ['printed on'],
}


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    if not text:
        return ""
    return text.lower().strip()


def matches_field(text: str, field_keywords: List[str]) -> bool:
    """Check if text matches any of the field keywords."""
    normalized = normalize_text(text)
    for keyword in field_keywords:
        if keyword in normalized:
            return True
    return False


def extract_value_after_colon(texts: List[str], start_idx: int, max_lookahead: int = 3) -> Optional[str]:
    """Extract value after a colon or in next few items."""
    # Check current item for colon
    if start_idx < len(texts):
        current = texts[start_idx]
        if ':' in current:
            parts = current.split(':', 1)
            if len(parts) > 1 and parts[1].strip():
                return parts[1].strip()
    
    # Look ahead
    for i in range(1, min(max_lookahead + 1, len(texts) - start_idx)):
        if start_idx + i < len(texts):
            value = texts[start_idx + i].strip()
            # Skip empty, colons only, or common separators
            if value and value not in [':', '.', '"', "'"] and not value.startswith(':'):
                return value
    return None


def is_test_name(text: str) -> bool:
    """Check if text looks like a test name."""
    normalized = normalize_text(text)
    # Check against common test names
    for test_keywords in COMMON_TEST_NAMES.values():
        for keyword in test_keywords:
            if keyword in normalized:
                return True
    return False


def is_number(text: str) -> bool:
    """Check if text is a number (with optional decimal)."""
    if not text:
        return False
    # Remove common units and check
    cleaned = text.replace('g/dl', '').replace('%', '').replace('fl', '').replace('pg', '').strip()
    try:
        float(cleaned)
        return True
    except ValueError:
        return False


def is_reference_range(text: str) -> bool:
    """Check if text looks like a reference range."""
    if not text:
        return False
    # Pattern: number-number or number - number
    pattern = r'\d+[\s-]+\d+'
    if re.search(pattern, text):
        return True
    # Pattern: number-number-number (like 13-17)
    if '-' in text and any(c.isdigit() for c in text):
        return True
    return False


def is_unit(text: str) -> bool:
    """Check if text looks like a unit."""
    if not text:
        return False
    normalized = normalize_text(text)
    units = ['g/dl', 'g/l', '%', 'fl', 'pg', '/ul', '/cumm', '/l', 'million/ul', 
             'x103', 'x10^3', 'cells/ul', 'lakhs', 'cmm', 'mill/cumm']
    return any(unit in normalized for unit in units)


def parse_test_result(texts: List[str], start_idx: int) -> Optional[Dict[str, Any]]:
    """
    Parse a test result starting from start_idx.
    Returns dict with test_name, observed_value, unit, reference_range or None.
    """
    if start_idx >= len(texts):
        return None
    
    test_name = texts[start_idx].strip()
    if not test_name or test_name in ['TEST DESCRIPTION', 'RESULT', 'REF. RANGE', 'UNIT', 
                                       'Test Name', 'Observed Value', 'Reference Range',
                                       'Investigation', 'Units', 'Biological Reference Interval']:
        return None
    
    # Skip if it's a section header
    section_headers = ['HAEMATOLOGY', 'BLOOD INDICES', 'DIFFERENTIAL COUNT', 
                       'PLATELET COUNT', 'RBC INDICES', 'PLATELETS INDICES',
                       'ABSOLUTE LEUCOCYTE COUNT', 'COMPLETE BLOOD COUNT']
    if any(header in test_name.upper() for header in section_headers):
        return None
    
    result = {
        'test_name': test_name,
        'observed_value': '',
        'unit': '',
        'reference_range': ''
    }
    
    # Look ahead to find value, unit, and range
    i = start_idx + 1
    found_value = False
    found_unit = False
    found_range = False
    
    # Check if current item has colon with value
    if ':' in test_name:
        parts = test_name.split(':', 1)
        if len(parts) > 1:
            test_name = parts[0].strip()
            potential_value = parts[1].strip()
            if potential_value and (is_number(potential_value) or potential_value):
                result['test_name'] = test_name
                result['observed_value'] = potential_value
                found_value = True
    
    result['test_name'] = test_name
    
    # Look ahead up to 5 items
    while i < min(start_idx + 6, len(texts)) and (not found_value or not found_unit or not found_range):
        current = texts[i].strip()
        
        if not current or current in [':', '.', '"', "'"]:
            i += 1
            continue
        
        # Check for value (number)
        if not found_value and is_number(current) and not is_reference_range(current):
            result['observed_value'] = current
            found_value = True
            i += 1
            continue
        
        # Check for unit
        if not found_unit and is_unit(current):
            result['unit'] = current
            found_unit = True
            i += 1
            continue
        
        # Check for reference range
        if not found_range and is_reference_range(current):
            result['reference_range'] = current
            found_range = True
            i += 1
            continue
        
        # If we found value but next item might be value with colon
        if found_value and ':' in current:
            parts = current.split(':', 1)
            if len(parts) > 1 and parts[1].strip():
                # This might be another test, stop here
                break
        
        i += 1
    
    # Only return if we have at least test name and value
    if result['test_name'] and (result['observed_value'] or is_test_name(result['test_name'])):
        return result
    
    return None


def parse_universal_format(texts: List[str]) -> Dict[str, Any]:
    """
    Universal parser for blood reports.
    Extracts common fields and handles any format intelligently.
    """
    parsed_data = {
        "patient_info": {},
        "laboratory_info": {},
        "haematology_report": [],
        "blood_indices": [],
        "morphology": {},
        "footer_info": {},
        "other_fields": {}  # For unknown fields
    }
    
    if not texts:
        return parsed_data
    
    # Convert to list of strings
    texts = [str(t).strip() if t else "" for t in texts]
    
    i = 0
    in_haematology_section = False
    in_blood_indices_section = False
    in_morphology_section = False
    current_category = None
    
    while i < len(texts):
        text = texts[i]
        
        if not text or text in [':', '.', '"', "'"]:
            i += 1
            continue
        
        text_upper = text.upper()
        text_lower = text.lower()
        
        # Detect sections
        if any(x in text_upper for x in ['HAEMATOLOGY', 'HEMATOLOGY', 'CBC', 'COMPLETE BLOOD COUNT']):
            in_haematology_section = True
            in_blood_indices_section = False
            i += 1
            # Skip headers
            while i < len(texts) and texts[i].upper() in ['TEST DESCRIPTION', 'RESULT', 'REF. RANGE', 'UNIT',
                                                          'TEST NAME', 'OBSERVED VALUE', 'REFERENCE RANGE',
                                                          'INVESTIGATION', 'UNITS', 'BIOLOGICAL REFERENCE INTERVAL']:
                i += 1
            continue
        
        if any(x in text_upper for x in ['BLOOD INDICES', 'RBC INDICES', 'PLATELETS INDICES']):
            in_blood_indices_section = True
            in_haematology_section = False
            i += 1
            continue
        
        if any(x in text_upper for x in ['DIFFERENTIAL COUNT', 'DIFFERENTIAL LEUCOCYTE COUNT']):
            current_category = "Differential Count"
            i += 1
            continue
        
        if any(x in text_upper for x in ['ABSOLUTE LEUCOCYTE COUNT', 'ABSOLUTE COUNT']):
            current_category = "Absolute Count"
            i += 1
            continue
        
        if any(x in text_upper for x in ['RBC MORPHOLOGY', 'PLATELETS ON SMEAR', 'MORPHOLOGY']):
            in_morphology_section = True
            i += 1
            continue
        
        # Parse patient info fields
        for field_name, keywords in COMMON_PATIENT_FIELDS.items():
            if matches_field(text, keywords):
                value = extract_value_after_colon(texts, i)
                if value:
                    # Handle age/gender split
                    if field_name == 'age_gender':
                        if '/' in value:
                            parts = value.split('/', 1)
                            if len(parts) == 2:
                                parsed_data["patient_info"]["age"] = parts[0].strip()
                                parsed_data["patient_info"]["gender"] = parts[1].strip()
                        else:
                            parsed_data["patient_info"][field_name] = value
                    else:
                        parsed_data["patient_info"][field_name] = value
                    i += 2
                    break
        
        # Parse laboratory info
        for field_name, keywords in COMMON_LAB_FIELDS.items():
            if matches_field(text, keywords):
                if field_name == 'name':
                    # Lab name might be in current text or next
                    lab_name = text
                    if i + 1 < len(texts) and not matches_field(texts[i + 1], COMMON_PATIENT_FIELDS):
                        next_text = texts[i + 1]
                        if not any(x in next_text.lower() for x in [':', 'date', 'no', 'id']):
                            lab_name = f"{text} {next_text}".strip()
                            i += 1
                    parsed_data["laboratory_info"]["name"] = lab_name
                else:
                    value = extract_value_after_colon(texts, i)
                    if value:
                        parsed_data["laboratory_info"][field_name] = value
                        i += 2
                        break
                i += 1
                break
        
        # Parse test results
        test_result = parse_test_result(texts, i)
        if test_result:
            test_name_lower = normalize_text(test_result['test_name'])
            
            # Determine if it's blood indices or haematology
            is_blood_index = any(
                keyword in test_name_lower 
                for keywords in [COMMON_TEST_NAMES['mcv'], COMMON_TEST_NAMES['mch'], 
                                COMMON_TEST_NAMES['mchc'], COMMON_TEST_NAMES['hct'],
                                COMMON_TEST_NAMES['rdw'], COMMON_TEST_NAMES['mpv'],
                                COMMON_TEST_NAMES['pct'], COMMON_TEST_NAMES['pdw']]
                for keyword in keywords
            )
            
            # Add category if applicable
            if current_category:
                test_result['category'] = current_category
            
            if is_blood_index or in_blood_indices_section:
                parsed_data["blood_indices"].append(test_result)
            else:
                parsed_data["haematology_report"].append(test_result)
            
            # Advance index based on how many items we consumed
            i += 1
            # Skip the items we already parsed
            if test_result['observed_value']:
                i += 1
            if test_result['unit']:
                i += 1
            if test_result['reference_range']:
                i += 1
            continue
        
        # Parse morphology
        if in_morphology_section:
            for field_name, keywords in COMMON_MORPHOLOGY_FIELDS.items():
                if matches_field(text, keywords):
                    value = extract_value_after_colon(texts, i)
                    if value:
                        # Check if next item is also part of morphology
                        if i + 2 < len(texts):
                            next_text = texts[i + 2]
                            if not matches_field(next_text, COMMON_PATIENT_FIELDS) and not is_test_name(next_text):
                                value = f"{value} {next_text}".strip()
                                i += 1
                        parsed_data["morphology"][field_name] = value
                        i += 2
                        break
        
        # Parse footer info
        for field_name, keywords in COMMON_FOOTER_FIELDS.items():
            if matches_field(text, keywords):
                value = extract_value_after_colon(texts, i)
                if value:
                    parsed_data["footer_info"][field_name] = value
                    i += 2
                else:
                    # Sometimes the field name itself is the value (e.g., "Dr. Name")
                    parsed_data["footer_info"][field_name] = text
                    i += 1
                break
        
        # Store unknown fields in other_fields
        if i < len(texts):
            # Check if this looks like a key-value pair we haven't captured
            if ':' in text and i + 1 < len(texts):
                key = text.split(':')[0].strip()
                value = extract_value_after_colon(texts, i)
                if value and key and len(key) > 2:  # Only store meaningful keys
                    if key not in parsed_data["other_fields"]:
                        parsed_data["other_fields"][key] = value
                    else:
                        # If key exists, make it a list
                        if not isinstance(parsed_data["other_fields"][key], list):
                            parsed_data["other_fields"][key] = [parsed_data["other_fields"][key]]
                        parsed_data["other_fields"][key].append(value)
        
        i += 1
    
    return parsed_data


def generate_markdown(data: Dict[str, Any]) -> str:
    """
    Generate Markdown formatted output from structured data.
    """
    md = f"# Medical Report: {data.get('image_name', 'Unknown')}\n\n"
    
    if data.get('image_path'):
        md += f"**Image Path:** `{data['image_path']}`\n\n"
    
    if data.get('processed_at'):
        md += f"**Processed At:** {data['processed_at']}\n\n"
    
    # Patient Info
    if data.get('patient_info'):
        md += "## Patient Information\n\n"
        for key, value in data['patient_info'].items():
            if value:  # Only include non-empty values
                md += f"- **{key.replace('_', ' ').title()}:** {value}\n"
        md += "\n"
    
    # Laboratory Info
    if data.get('laboratory_info'):
        md += "## Laboratory Information\n\n"
        for key, value in data['laboratory_info'].items():
            if value:  # Only include non-empty values
                md += f"- **{key.replace('_', ' ').title()}:** {value}\n"
        md += "\n"
    
    # Haematology Report
    if data.get('haematology_report'):
        md += "## Haematology Report\n\n"
        md += "| Test Name | Observed Value | Unit | Reference Range |\n"
        md += "|-----------|----------------|------|-----------------|\n"
        for test in data['haematology_report']:
            test_name = str(test.get('test_name', '')).replace('|', '\\|')
            value = str(test.get('observed_value', '')).replace('|', '\\|')
            unit = str(test.get('unit', '')).replace('|', '\\|')
            ref_range = str(test.get('reference_range', '')).replace('|', '\\|')
            md += f"| {test_name} | {value} | {unit} | {ref_range} |\n"
        md += "\n"
    
    # Blood Indices
    if data.get('blood_indices'):
        md += "## Blood Indices\n\n"
        md += "| Test Name | Observed Value | Unit | Reference Range |\n"
        md += "|-----------|----------------|------|-----------------|\n"
        for test in data['blood_indices']:
            test_name = str(test.get('test_name', '')).replace('|', '\\|')
            value = str(test.get('observed_value', '')).replace('|', '\\|')
            unit = str(test.get('unit', '')).replace('|', '\\|')
            ref_range = str(test.get('reference_range', '')).replace('|', '\\|')
            md += f"| {test_name} | {value} | {unit} | {ref_range} |\n"
        md += "\n"
    
    # Morphology
    if data.get('morphology'):
        md += "## Morphology\n\n"
        for key, value in data['morphology'].items():
            if value:  # Only include non-empty values
                md += f"- **{key.replace('_', ' ').title()}:** {value}\n"
        md += "\n"
    
    # Footer Info
    if data.get('footer_info'):
        md += "## Footer Information\n\n"
        for key, value in data['footer_info'].items():
            if value:  # Only include non-empty values
                md += f"- **{key.replace('_', ' ').title()}:** {value}\n"
        md += "\n"
    
    # Other Fields
    if data.get('other_fields'):
        md += "## Other Fields\n\n"
        for key, value in data['other_fields'].items():
            if value:  # Only include non-empty values
                if isinstance(value, list):
                    md += f"- **{key.replace('_', ' ').title()}:** {', '.join(str(v) for v in value)}\n"
                else:
                    md += f"- **{key.replace('_', ' ').title()}:** {value}\n"
        md += "\n"
    
    return md
