import io
import pytest
from datetime import date, datetime
from zoneinfo import ZoneInfo
import os
import sys
from unittest.mock import MagicMock, patch
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
    run_ocr,
    run_ocr_azure,
    get_uk_now,
    DEFAULT_HIRE_END_DATE,
    generate_permission_letter,
    generate_contract,
    add_audit_log,
    get_audit_logs,
    FLEET_VEHICLES,
    download_from_supabase_storage,
    parse_licence,
)

def test_jpg_licence_loading():
    img_buf = io.BytesIO()
    im = Image.new("RGB", (300, 200), color="white")
    im.save(img_buf, format="JPEG")
    img_buf.seek(0)
    img_buf.name = "licence.jpg"

    loaded = load_uploaded_image(img_buf)
    assert isinstance(loaded, Image.Image)
    assert loaded.size == (300, 200)

def test_png_licence_loading():
    img_buf = io.BytesIO()
    im = Image.new("RGB", (300, 200), color="blue")
    im.save(img_buf, format="PNG")
    img_buf.seek(0)
    img_buf.name = "licence.png"

    loaded = load_uploaded_image(img_buf)
    assert isinstance(loaded, Image.Image)
    assert loaded.size == (300, 200)

def test_one_page_pdf():
    pdf_buf = io.BytesIO()
    c = canvas.Canvas(pdf_buf)
    c.drawString(100, 500, "Single Page Driving Licence Front")
    c.save()
    pdf_buf.seek(0)
    pdf_buf.name = "licence.pdf"

    loaded = load_uploaded_image(pdf_buf)
    assert isinstance(loaded, Image.Image)
    assert loaded.size[0] > 0 and loaded.size[1] > 0

def test_two_page_pdf():
    pdf_buf = io.BytesIO()
    c = canvas.Canvas(pdf_buf)
    c.drawString(100, 500, "Page 1 Front Licence")
    c.showPage()
    c.drawString(100, 500, "Page 2 Back Licence")
    c.showPage()
    c.save()
    pdf_buf.seek(0)
    pdf_buf.name = "licence.pdf"

    loaded = load_uploaded_image(pdf_buf)
    assert isinstance(loaded, Image.Image)
    assert loaded.size[0] > 0 and loaded.size[1] > 0

def test_two_page_pdf_only_page_1_processed():
    pdf_buf = io.BytesIO()
    c = canvas.Canvas(pdf_buf)
    c.drawString(100, 500, "FRONT LICENCE PAGE ONE")
    c.showPage()
    c.drawString(100, 500, "BACK LICENCE PAGE TWO SECRET")
    c.showPage()
    c.save()
    pdf_bytes = pdf_buf.getvalue()

    fake_file = io.BytesIO(pdf_bytes)
    fake_file.name = "licence.pdf"

    # Verify load_uploaded_image extracts page 1 as PIL Image
    img = load_uploaded_image(fake_file)
    assert isinstance(img, Image.Image)

    # Verify that passing fake_file to run_ocr uses load_uploaded_image and processes Page 1
    raw_text = run_ocr(fake_file)
    assert isinstance(raw_text, str)
    assert "SECRET" not in raw_text

def test_page_2_never_passed_to_azure():
    pdf_buf = io.BytesIO()
    c = canvas.Canvas(pdf_buf)
    c.drawString(100, 500, "FRONT PAGE ONE LICENCE")
    c.showPage()
    c.drawString(100, 500, "BACK PAGE TWO SECRET UNREADABLE DATA")
    c.showPage()
    c.save()
    raw_pdf_bytes = pdf_buf.getvalue()
    pdf_file = io.BytesIO(raw_pdf_bytes)
    pdf_file.name = "multi_page_licence.pdf"

    # Mock Azure client and st.secrets
    mock_field_fn = MagicMock(value_string="SMITH")
    mock_field_ln = MagicMock(value_string="JOHN")
    mock_doc = MagicMock()
    mock_doc.fields = {
        "LastName": mock_field_fn,
        "FirstName": mock_field_ln,
        "Address": "123 TEST ST",
        "DocumentNumber": "SMITH901019A999"
    }

    mock_result = MagicMock()
    mock_result.documents = [mock_doc]
    mock_result.pages = []

    mock_poller = MagicMock()
    mock_poller.result.return_value = mock_result

    mock_client = MagicMock()
    mock_client.begin_analyze_document.return_value = mock_poller

    with patch("streamlit_app.DocumentIntelligenceClient", return_value=mock_client), \
         patch("streamlit_app.st.secrets", {"AZURE_DOCINTEL_ENDPOINT": "https://test.cognitiveservices.azure.com/", "AZURE_DOCINTEL_KEY": "testkey"}), \
         patch("streamlit_app.load_uploaded_image", wraps=load_uploaded_image) as spy_load_img:

        res = run_ocr_azure(pdf_file)

        # Verify entry point load_uploaded_image was invoked
        assert spy_load_img.call_count == 1

        # Explicitly assert exactly one begin_analyze_document call
        assert mock_client.begin_analyze_document.call_count == 1
        call_kwargs = mock_client.begin_analyze_document.call_args.kwargs
        assert call_kwargs.get("content_type") == "image/jpeg"
        sent_body = call_kwargs.get("body")
        assert isinstance(sent_body, bytes)
        # Ensure raw PDF bytes and original PDF payload are NOT sent
        assert not sent_body.startswith(b"%PDF")
        assert sent_body != raw_pdf_bytes
        assert b"BACK PAGE TWO SECRET UNREADABLE DATA" not in sent_body

def test_oversized_upload_downscaled():
    # Create large image (e.g. 4000x3000)
    large_img = Image.new("RGB", (4000, 3000), color="white")
    buf = io.BytesIO()
    large_img.save(buf, format="JPEG")
    buf.seek(0)
    buf.name = "large_scan.jpg"

    loaded = load_uploaded_image(buf)
    assert isinstance(loaded, Image.Image)
    assert loaded.size == (4000, 3000)

    # When run_ocr_azure processes it, thumbnail downscales it to 1600x1600 max
    mock_result = MagicMock()
    mock_doc = MagicMock()
    mock_doc.fields = {}
    mock_result.documents = [mock_doc]
    mock_result.pages = []
    mock_poller = MagicMock()
    mock_poller.result.return_value = mock_result
    mock_client = MagicMock()
    mock_client.begin_analyze_document.return_value = mock_poller

    with patch("streamlit_app.DocumentIntelligenceClient", return_value=mock_client), \
         patch("streamlit_app.st.secrets", {"AZURE_DOCINTEL_ENDPOINT": "https://test.cognitiveservices.azure.com/", "AZURE_DOCINTEL_KEY": "testkey"}):
        buf.seek(0)
        run_ocr_azure(buf)
        assert mock_client.begin_analyze_document.call_count == 1
        sent_bytes = mock_client.begin_analyze_document.call_args.kwargs["body"]
        # Ensure payload is well under 1MB
        assert len(sent_bytes) < 1_000_000

def test_malformed_pdf():
    malformed = io.BytesIO(b"%PDF-1.4 malformed broken bytes content")
    malformed.name = "bad_licence.pdf"

    with pytest.raises(ValueError, match="Invalid or malformed PDF"):
        load_uploaded_image(malformed)

def test_unsupported_file():
    unsupported = io.BytesIO(b"Plain text file not an image or pdf")
    unsupported.name = "document.txt"

    with pytest.raises(ValueError, match="Unsupported or corrupted image"):
        load_uploaded_image(unsupported)

def test_driver_name_extraction_formatting():
    assert format_driver_name_for_display("JOHN SMITH") == "John Smith"
    assert format_driver_name_for_display("MARY JANE SMITH") == "Mary Jane Smith"
    assert format_driver_name_for_display("DRIVER") == ""
    assert format_driver_name_for_display("") == ""

def test_document_filename_formatting():
    doc_name = build_default_doc_name("Contract", "JOHN SMITH", "YF22UWM", "Contract")
    assert doc_name == "Contract John Smith YF22UWM"

    perm_name = build_default_doc_name("Permission", "JOHN SMITH", "YF22UWM", "Permission Letter")
    assert perm_name == "Permission John Smith YF22UWM"

def test_no_duplicate_name_or_registration_in_filename():
    dup_doc_name = build_default_doc_name("Contract", "John Smith YF22UWM", "YF22UWM", "Contract")
    assert dup_doc_name == "Contract John Smith YF22UWM"

    dup_clean = clean_document_name("Contract John Smith YF22UWM John Smith YF22UWM", "Contract")
    assert dup_clean == "Contract John Smith YF22UWM"

def test_dynamic_contract_number():
    c_no1 = build_default_contract_no("JOHN SMITH", "YF22UWM")
    assert c_no1 == "1608/JOHN-SMITH/YF22UWM2026"

    c_no2 = build_default_contract_no("JOHN SMITH", "YF22 UWM")
    assert c_no2 == "1608/JOHN-SMITH/YF22UWM2026"

    c_no3 = build_default_contract_no("", "")
    assert c_no3 == "1608/DRIVER/REG/2026"

def test_europe_london_timezone():
    uk_time = get_uk_now()
    assert isinstance(uk_time, datetime)
    assert uk_time.tzinfo is not None
    assert str(uk_time.tzinfo) == "Europe/London"

def test_gmt_and_bst_timezone_offset():
    # GMT in Winter (January) -> UTC+0
    dt_gmt = datetime(2026, 1, 15, 12, 0, tzinfo=ZoneInfo("Europe/London"))
    assert dt_gmt.utcoffset().total_seconds() == 0

    # BST in Summer (July) -> UTC+1
    dt_bst = datetime(2026, 7, 15, 12, 0, tzinfo=ZoneInfo("Europe/London"))
    assert dt_bst.utcoffset().total_seconds() == 3600

def test_mg5_yf22uwm_exists_exactly_once():
    matches = [v for v in FLEET_VEHICLES if v["reg"].replace(" ", "").upper() == "YF22UWM"]
    assert len(matches) == 1
    mg5 = matches[0]
    assert mg5["reg"] == "YF22 UWM"
    assert mg5["model"] == "MG 5 EV"
    assert mg5["category"] == "Other Premium & EVs"

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
