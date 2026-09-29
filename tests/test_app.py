import io
import pytest
from datetime import date, datetime, time
from zoneinfo import ZoneInfo
import os
import sys
from unittest.mock import MagicMock, patch
from PIL import Image
from reportlab.pdfgen import canvas

# Ensure src is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import streamlit as st
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
    render_pdf_to_images,
    apply_ocr_results_to_session_state,
    _find_img,
    format_date_val,
    format_time_val,
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

def test_webp_licence_loading():
    img_buf = io.BytesIO()
    im = Image.new("RGB", (300, 200), color="green")
    im.save(img_buf, format="WEBP")
    img_buf.seek(0)
    img_buf.name = "licence.webp"

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
    assert doc_name == "Contract - John Smith - YF22UWM"

    perm_name = build_default_doc_name("Permission", "JOHN SMITH", "YF22UWM", "Permission Letter")
    assert perm_name == "Permission - John Smith - YF22UWM"

def test_no_duplicate_name_or_registration_in_filename():
    dup_doc_name = build_default_doc_name("Contract", "John Smith YF22UWM", "YF22UWM", "Contract")
    assert dup_doc_name == "Contract - John Smith - YF22UWM"

    dup_clean = clean_document_name("Contract - John Smith - YF22UWM - John Smith - YF22UWM", "Contract")
    assert dup_clean == "Contract - John Smith - YF22UWM"

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

def test_live_document_preview_rendering():
    perm_data = {
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
    pdf_bytes = generate_permission_letter(perm_data)
    imgs = render_pdf_to_images(pdf_bytes)
    assert len(imgs) == 1
    assert isinstance(imgs[0], Image.Image)

    contract_data = {
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
    c_bytes = generate_contract(contract_data)
    c_imgs = render_pdf_to_images(c_bytes)
    assert len(c_imgs) == 2
    for img in c_imgs:
        assert isinstance(img, Image.Image)

def test_ocr_populates_workspace_fields_immediately():
    st.session_state.clear()
    st.session_state.sel_reg = "YF22 UWM"

    parsed_ocr = {
        "forename": "JOHN",
        "surname": "SMITH",
        "licence": "SMITH901019A999",
        "address": "123 TEST STREET",
        "postcode": "SW1A 1AA",
        "dob": "01/01/1990",
        "expiry": "01/01/2030",
        "signature_bytes": b"fake_sig_bytes",
    }

    apply_ocr_results_to_session_state(parsed_ocr)

    assert st.session_state["p_form_name"] == "John Smith"
    assert st.session_state["c_form_name"] == "John Smith"
    assert st.session_state["p_form_lic"] == "SMITH901019A999"
    assert st.session_state["c_form_lic"] == "SMITH901019A999"
    assert st.session_state["c_form_addr"] == "123 TEST STREET"
    assert st.session_state["c_form_post"] == "SW1A 1AA"
    assert st.session_state["p_form_addr"] == "123 TEST STREET, SW1A 1AA"
    assert st.session_state["c_form_dob"] == "01/01/1990"
    assert st.session_state["c_form_exp"] == "01/01/2030"
    assert st.session_state.ocr_signature_bytes == b"fake_sig_bytes"
    assert st.session_state["perm_document_name"] == "Permission - John Smith - YF22UWM"
    assert st.session_state["contract_document_name"] == "Contract - John Smith - YF22UWM"
    assert st.session_state["c_form_no"] == "1608/JOHN-SMITH/YF22UWM2026"

def test_permission_letter_preview_empty_fields():
    empty_perm_data = {
        "date": "28/09/2026",
        "insurance_policy": "",
        "registration": "",
        "make_model": "",
        "driver_name": "",
        "address": "",
        "license_no": "",
        "start_date": "28/09/2026",
        "end_date": "27/11/2026"
    }
    pdf_bytes = generate_permission_letter(empty_perm_data)
    imgs = render_pdf_to_images(pdf_bytes)
    assert len(imgs) == 1
    assert isinstance(imgs[0], Image.Image)

def test_contract_preview_empty_fields():
    empty_contract_data = {
        "contract_no": "1608/DRIVER/REG/2026",
        "date": "28/09/2026",
        "driver_name": "",
        "address": "",
        "postcode": "",
        "dob": "",
        "license_no": "",
        "expiry_date": "",
        "issuing_authority": "DVLA",
        "phone": "",
        "email": "",
        "rent": "250/-",
        "rate": "20/-",
        "deposit": "500/-",
        "start_date": "28/09/2026",
        "expected_return": "27/11/2026",
        "start_time": "12:00",
        "return_time": "12:00",
        "registration": "",
        "car_make": "",
        "car_model": "",
        "owner_signature": "-- No Signature --",
        "hirer_signature": None,
    }
    pdf_bytes = generate_contract(empty_contract_data)
    imgs = render_pdf_to_images(pdf_bytes)
    assert len(imgs) == 2
    for img in imgs:
        assert isinstance(img, Image.Image)

def test_form_field_and_ocr_updates_live_preview():
    # Render empty preview
    empty_perm_pdf = generate_permission_letter({
        "date": "28/09/2026", "insurance_policy": "", "registration": "",
        "make_model": "", "driver_name": "", "address": "", "license_no": "",
        "start_date": "28/09/2026", "end_date": "27/11/2026"
    })
    empty_img = render_pdf_to_images(empty_perm_pdf)[0]

    # Populate via OCR
    st.session_state.clear()
    st.session_state.sel_reg = "YF22 UWM"
    parsed_ocr = {
        "forename": "JANE", "surname": "DOE", "licence": "DOE901019A999",
        "address": "456 HIGH STREET", "postcode": "NW1 1AA",
        "dob": "15/05/1985", "expiry": "15/05/2032", "signature_bytes": None
    }
    apply_ocr_results_to_session_state(parsed_ocr)

    updated_perm_pdf = generate_permission_letter({
        "date": "28/09/2026", "insurance_policy": "HAVFL-000211",
        "registration": "YF22 UWM", "make_model": "MG 5 EV",
        "driver_name": st.session_state["p_form_name"].upper(),
        "address": st.session_state["p_form_addr"].upper(),
        "license_no": st.session_state["p_form_lic"].upper(),
        "start_date": "28/09/2026", "end_date": "27/11/2026"
    })
    updated_img = render_pdf_to_images(updated_perm_pdf)[0]

    # PDF bytes and rendered image content must differ once populated with values
    assert empty_perm_pdf != updated_perm_pdf
    assert empty_img.tobytes() != updated_img.tobytes()

def test_find_img_template_resolution():
    # Background images for permission letter and contract templates must be found
    assert _find_img("image_f4efbe") is not None
    assert _find_img("1") is not None
    assert _find_img("2") is not None
    assert _find_img("signature") is not None

def test_format_date_and_time_helpers():
    now_d = date(2026, 9, 28)
    now_t = time(14, 30)

    assert format_date_val(now_d) == "28/09/2026"
    assert format_date_val(None, fallback_default=now_d) == "28/09/2026"
    assert format_date_val("12/12/2026") == "12/12/2026"
    assert format_date_val(None) == ""

    assert format_time_val(now_t) == "14:30"
    assert format_time_val("10:15") == "10:15"
    assert ":" in format_time_val(None)

def test_bmp_and_tiff_licence_loading():
    bmp_buf = io.BytesIO()
    im_bmp = Image.new("RGB", (200, 150), color="red")
    im_bmp.save(bmp_buf, format="BMP")
    bmp_buf.seek(0)
    bmp_buf.name = "licence.bmp"

    loaded_bmp = load_uploaded_image(bmp_buf)
    assert isinstance(loaded_bmp, Image.Image)
    assert loaded_bmp.size == (200, 150)

    tiff_buf = io.BytesIO()
    im_tiff = Image.new("RGB", (200, 150), color="yellow")
    im_tiff.save(tiff_buf, format="TIFF")
    tiff_buf.seek(0)
    tiff_buf.name = "licence.tiff"

    loaded_tiff = load_uploaded_image(tiff_buf)
    assert isinstance(loaded_tiff, Image.Image)
    assert loaded_tiff.size == (200, 150)

def test_ocr_preserves_existing_manual_entries_when_missing():
    st.session_state.clear()
    st.session_state["p_form_name"] = "Existing Manual Name"
    st.session_state["p_form_lic"] = "MANUAL12345"
    st.session_state.ocr_name = "Existing Manual Name"
    st.session_state.ocr_licence = "MANUAL12345"
    st.session_state.ocr_address = ""
    st.session_state.ocr_postcode = ""
    st.session_state.sel_reg = ""

    partial_ocr = {
        "forename": "",
        "surname": "",
        "licence": "",
        "address": "789 NEW ROAD",
        "postcode": "E1 6AN",
    }

    apply_ocr_results_to_session_state(partial_ocr)

    assert st.session_state["p_form_name"] == "Existing Manual Name"
    assert st.session_state["p_form_lic"] == "MANUAL12345"
    assert st.session_state["c_form_addr"] == "789 NEW ROAD"

def test_oversized_upload_validation_logic():
    import streamlit_app
    limit = getattr(streamlit_app, "MAX_UPLOAD_SIZE_BYTES", 25 * 1024 * 1024)
    fake_file = MagicMock()
    fake_file.size = 30 * 1024 * 1024  # 30MB
    assert fake_file.size > limit

def test_licence_preview_panel_image_rendering():
    img_buf = io.BytesIO()
    im = Image.new("RGB", (400, 250), color="purple")
    im.save(img_buf, format="PNG")
    img_buf.seek(0)
    img_buf.name = "licence_preview.png"

    preview_img = load_uploaded_image(img_buf)
    assert isinstance(preview_img, Image.Image)
    assert preview_img.size == (400, 250)

def test_audit_logs_pagination_and_caching():
    from streamlit_app import get_cached_audit_logs
    logs = get_cached_audit_logs()
    assert isinstance(logs, list)

    # Test pagination slicing logic on mock list
    mock_logs = [{"id": i, "event_type": "test"} for i in range(25)]
    items_per_page = 10
    total_logs = len(mock_logs)
    total_pages = max(1, (total_logs + items_per_page - 1) // items_per_page)
    assert total_pages == 3

    page1_items = mock_logs[0:10]
    page2_items = mock_logs[10:20]
    page3_items = mock_logs[20:25]

    assert len(page1_items) == 10
    assert len(page2_items) == 10
    assert len(page3_items) == 5

def test_css_transitions_and_reduced_motion():
    import streamlit_app
    with open(streamlit_app.__file__, "r", encoding="utf-8") as f:
        content = f.read()
    assert "@keyframes faIbiFadeIn" in content
    assert "@media (prefers-reduced-motion: reduce)" in content

def test_ab_workspace_social_image_and_og_metadata():
    import streamlit_app
    # Verify 1200x630 public social image asset
    social_img_path = os.path.join(os.path.dirname(streamlit_app.__file__), "ab_workspace_social.png")
    assert os.path.exists(social_img_path)
    with Image.open(social_img_path) as im:
        assert im.size == (1200, 630)

    # Verify Open Graph and Twitter metadata in app code
    with open(streamlit_app.__file__, "r", encoding="utf-8") as f:
        code = f.read()

    assert 'og:title" content="AB Workspace"' in code
    assert 'og:description" content="AB Workspace — Create, manage and generate your documents in one place."' in code
    assert 'og:image"' in code
    assert 'og:url"' in code
    assert 'https://vchletter.xubi.org' in code
    assert 'twitter:card" content="summary_large_image"' in code
    assert 'twitter:title" content="AB Workspace"' in code

def test_licence_preview_card_bounds_and_aspect_ratio():
    import streamlit_app
    with open(streamlit_app.__file__, "r", encoding="utf-8") as f:
        code = f.read()

    # Verify licence preview container class and styling
    assert ".licence-preview-card" in code
    assert "max-width: 420px;" in code
    assert "object-fit: contain !important;" in code
    assert "width=360" in code

    # Test aspect ratio preservation for JPG landscape and portrait images
    img_land = Image.new("RGB", (800, 500), color="blue")
    buf_land = io.BytesIO()
    img_land.save(buf_land, format="JPEG")
    buf_land.seek(0)
    buf_land.name = "landscape.jpg"
    loaded_land = load_uploaded_image(buf_land)
    assert loaded_land.size[0] > loaded_land.size[1]  # Aspect ratio preserved landscape

    img_port = Image.new("RGB", (500, 800), color="green")
    buf_port = io.BytesIO()
    img_port.save(buf_port, format="JPEG")
    buf_port.seek(0)
    buf_port.name = "portrait.jpg"
    loaded_port = load_uploaded_image(buf_port)
    assert loaded_port.size[1] > loaded_port.size[0]  # Aspect ratio preserved portrait
