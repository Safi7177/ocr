"""
Medical report parsers for different laboratory formats.
"""

from .parth_parser import parse_parth_format
from .grant_parser import parse_grant_format
from .arfa_parser import parse_arfa_format
from .universal_parser import parse_universal_format


def detect_report_format(texts):
    """
    Detect the format of the medical report based on keywords.
    Returns: 'parth', 'grant', 'arfa', or 'unknown'
    """
    if not texts:
        return 'unknown'
    
    text_str = " ".join(texts[:50]).upper()  # Check first 50 items
    
    if "PARTH PATHOLOGY" in text_str or "PARTH" in text_str:
        return 'parth'
    elif "GRANT MEDICAL" in text_str or "GRANT" in text_str:
        return 'grant'
    elif "ARFA DIAGNOSTIC" in text_str or "ARFA" in text_str:
        return 'arfa'
    return 'unknown'


def parse_medical_report(rec_texts):
    """
    Parse medical report from OCR text and extract structured fields.
    Supports multiple report formats: PARTH, Grant Medical, ARFA, and any other format via universal parser.
    """
    if not rec_texts:
        return {
            "patient_info": {},
            "laboratory_info": {},
            "haematology_report": [],
            "blood_indices": [],
            "morphology": {},
            "footer_info": {},
            "other_fields": {}
        }
    
    # Convert to list of strings for easier processing
    texts = [str(t).strip() for t in rec_texts if t and str(t).strip()]
    
    # Detect format
    format_type = detect_report_format(texts)
    
    # Route to appropriate parser
    # For known formats, try specific parser first, then fallback to universal
    if format_type == 'parth':
        try:
            result = parse_parth_format(texts)
            # Validate that we got some data
            if result.get('haematology_report') or result.get('blood_indices') or result.get('patient_info'):
                return result
        except Exception:
            pass
        # Fallback to universal parser
        return parse_universal_format(texts)
    elif format_type == 'grant':
        try:
            result = parse_grant_format(texts)
            # Validate that we got some data
            if result.get('haematology_report') or result.get('blood_indices') or result.get('patient_info'):
                return result
        except Exception:
            pass
        # Fallback to universal parser
        return parse_universal_format(texts)
    elif format_type == 'arfa':
        try:
            result = parse_arfa_format(texts)
            # Validate that we got some data
            if result.get('haematology_report') or result.get('blood_indices') or result.get('patient_info'):
                return result
        except Exception:
            pass
        # Fallback to universal parser
        return parse_universal_format(texts)
    else:
        # Use universal parser for unknown formats or as fallback
        return parse_universal_format(texts)
