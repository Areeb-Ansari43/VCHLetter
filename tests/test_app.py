import io
import pytest
from datetime import date, datetime
import os
import sys
from PIL import Image
from reportlab.pdfgen import canvas

# Ensure src is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from streamlit_app import (
    build_default_doc_name,
    build_default_contract_no,
    format_driver_name_for_display,
    clean_document_name,
    load_uploaded_image,
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

    contract_name = build_default_doc_name("Contract", "JOHN SMITH", "YF22UWM", "Contract")
    assert contract_name == "Contract John Smith YF22UWM"

    contract_name_no_driver = build_default_doc_name("Contract", "", "YF22UWM", "Contract")
    assert contract_name_no_driver == "Contract YF22UWM"

    contract_name_driver_placeholder = build_default_doc_name("Contract", "Driver", "", "Contract")
    assert contract_name_driver_placeholder == "Contract"

    # Test clean document name
    assert clean_document_name("Permission Areeb Ansari MA16BFZ.pdf", "Fallback") == "Permission Areeb Ansari MA16BFZ"

def test_contract_number_building():
    c_no1 = build_default_contract_no("JOHN SMITH", "YF22UWM")
    assert c_no1 == "1608/JOHN-SMITH/YF22UWM2026"

    c_no2 = build_default_contract_no("JOHN SMITH", "YF22 UWM")
    assert c_no2 == "1608/JOHN-SMITH/YF22UWM2026"

    c_no3 = build_default_contract_no("", "")
    assert c_no3 == "1608/DRIVER/REG/2026"

    c_no4 = build_default_contract_no("Driver", "YF22UWM")
    assert c_no4 == "1608/DRIVER/YF22UWM2026"

def test_driver_name_display_formatting():
    assert format_driver_name_for_display("JOHN SMITH") == "John Smith"
    assert format_driver_name_for_display("AREEB ANSARI") == "Areeb Ansari"
    assert format_driver_name_for_display("MARY-ANN SMITH") == "Mary-Ann Smith"
    assert format_driver_name_for_display("Driver") == ""
    assert format_driver_name_for_display("") == ""

def test_pdf_page1_extraction():
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 500, "Page 1 Front Licence Content")
    c.showPage()
    c.drawString(100, 500, "Page 2 Back Licence Content")
    c.showPage()
    c.save()

    pdf_bytes = buf.getvalue()
    fake_file = io.BytesIO(pdf_bytes)
    fake_file.name = "licence.pdf"

    img = load_uploaded_image(fake_file)
    assert isinstance(img, Image.Image)
    assert img.size[0] > 0 and img.size[1] > 0

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
        "contract_no": "1608/JOHN-SMITH/YF22UWM2026",
        "date": "10/06/2026",
        "driver_name": "JOHN SMITH",
        "address": "123 TEST STREET, LONDON",
        "postcode": "SW1A 1AA",
        "dob": "01/01/1990",
        "license_no": "SMITH901019A999",
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
        "registration": "YF22 UWM",
        "car_make": "MG",
        "car_model": "5 EV",
        "owner_signature": "-- No Signature --",
        "hirer_signature": None,
    }
    pdf_bytes = generate_contract(data)
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")

def test_audit_logs():
    test_doc = "Contract John Smith YF22UWM.pdf"
    test_details = "Contract No: 1608/JOHN-SMITH/YF22UWM2026, Driver: JOHN SMITH, Reg: YF22 UWM"
    test_path = "driver_documents/20260610_120000_Contract John Smith YF22UWM.pdf"
    add_audit_log("Contract Generated", details=test_details, doc_name=test_doc, file_path=test_path)

    logs = get_audit_logs()
    assert len(logs) > 0
    latest = logs[0]
    assert latest["event_type"] == "Contract Generated"
    assert latest["doc_name"] == test_doc
    assert latest["details"] == test_details
    assert latest["file_path"] == test_path

def test_fleet_vehicles_structure():
    assert len(FLEET_VEHICLES) > 0
    for v in FLEET_VEHICLES:
        assert "reg" in v
        assert "model" in v
        assert "category" in v
