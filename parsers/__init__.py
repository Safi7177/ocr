"""
Medical report parsers for different laboratory formats.
"""

from .parth_parser import parse_parth_format
from .grant_parser import parse_grant_format
from .arfa_parser import parse_arfa_format


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
