import pytest
from datetime import date, datetime
import os
import sys

# Ensure src is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from streamlit_app import (
    build_default_doc_name,
    clean_document_name,
    DEFAULT_HIRE_END_DATE,
    generate_permission_letter,
    generate_contract,
    add_audit_log,
    get_audit_logs,
    FLEET_VEHICLES,
    download_from_supabase_storage,
)

def test_document_auto_naming():
    perm_name = build_default_doc_name("Permission", "Areeb Ansari", "MA16BFZ", "Permission Letter")
    assert perm_name == "Permission Areeb Ansari MA16BFZ"

    contract_name = build_default_doc_name("Contract", "Areeb Ansari", "MA16BFZ", "Contract")
    assert contract_name == "Contract Areeb Ansari MA16BFZ"

    # Test clean document name
    assert clean_document_name("Permission Areeb Ansari MA16BFZ.pdf", "Fallback") == "Permission Areeb Ansari MA16BFZ"

def test_default_hire_end_date():
    assert DEFAULT_HIRE_END_DATE == date(2026, 11, 27)

def test_permission_letter_generation():
    data = {
        "date": "10/06/2026",
        "insurance_policy": "HAVFL-000211",
        "registration": "MA16 BFZ",
        "make_model": "MERCEDES-BENZ E220D",
        "driver_name": "AREEB ANSARI",
        "address": "123 TEST STREET, LONDON",
        "license_no": "ANSAR901019A999",
        "start_date": "10/06/2026",
        "end_date": "27/11/2026"
    }
    pdf_bytes = generate_permission_letter(data)
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")

def test_contract_generation():
    data = {
        "contract_no": "1608/DRIVER/REG/2026",
        "date": "10/06/2026",
        "driver_name": "AREEB ANSARI",
        "address": "123 TEST STREET, LONDON",
        "postcode": "SW1A 1AA",
        "dob": "01/01/1990",
        "license_no": "ANSAR901019A999",
        "expiry_date": "01/01/2030",
        "issuing_authority": "DVLA",
        "phone": "07123456789",
        "email": "TEST@EXAMPLE.COM",
        "rent": "250/-",
        "rate": "20/-",
        "deposit": "500/-",
        "start_date": "10/06/2026",
        "expected_return": "27/11/2026",
        "start_time": "10:00",
        "return_time": "10:00",
        "registration": "MA16 BFZ",
        "car_make": "MERCEDES-BENZ",
        "car_model": "E220D",
        "owner_signature": "-- No Signature --",
        "hirer_signature": None,
    }
    pdf_bytes = generate_contract(data)
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")

def test_audit_logs():
    test_doc = "Permission Areeb Ansari MA16BFZ.pdf"
    test_details = "Driver: AREEB ANSARI, Reg: MA16 BFZ"
    test_path = "driver_documents/20260610_120000_Permission Areeb Ansari MA16BFZ.pdf"
    add_audit_log("Permission Letter Generated", details=test_details, doc_name=test_doc, file_path=test_path)

    logs = get_audit_logs()
    assert len(logs) > 0
    latest = logs[0]
    assert latest["event_type"] == "Permission Letter Generated"
    assert latest["doc_name"] == test_doc
    assert latest["details"] == test_details
    assert latest["file_path"] == test_path

def test_fleet_vehicles_structure():
    assert len(FLEET_VEHICLES) > 0
    for v in FLEET_VEHICLES:
        assert "reg" in v
        assert "model" in v
        assert "category" in v
