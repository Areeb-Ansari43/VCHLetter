import streamlit as st
import os
import re
import cv2
import numpy as np
from PIL import Image
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

try:
    import pytesseract
except ImportError:
    pytesseract = None

# --- Full 89-Car Fleet Database ---
FLEET_VEHICLES = [
    {"reg": "AF70 MYK", "model": "TESLA MODEL 3 "},
    {"reg": "BD20 XPU", "model": "MERCEDES-BENZ E300 "},
    {"reg": "BJ20 L6X", "model": "TESLA MODEL 3 "},
    {"reg": "BK70 WYM", "model": "TESLA MODEL 3 "},
    {"reg": "BL19 JDZ", "model": "MERCEDES-BENZ E220D "},
    {"reg": "BN17 CVA", "model": "MERCEDES-BENZ VITO "},
    {"reg": "BN20 MXL", "model": "JAGUAR I-PACE "},
    {"reg": "BN60 MYZ", "model": "MERCEDES-BENZ E220D "},
    {"reg": "BN60 NHP", "model": "MERCEDES-BENZ E220D "},
    {"reg": "BT69 TEJ", "model": "TESLA MODEL 3 "},
    {"reg": "RE21 NRX", "model": "MG 5 EV"},
    {"reg": "BU19 ACJ", "model": "MERCEDES-BENZ E220D "},
    {"reg": "BV18 WNA", "model": "MERCEDES-BENZ E220D "},
    {"reg": "BX19 ZMY", "model": "MERCEDES-BENZ E220D "},
    {"reg": "CA19 UTF", "model": "MERCEDES-BENZ E220D "},
    {"reg": "EF70 ZPZ", "model": "HYUNDAI IONIQ "},
    {"reg": "EF70 ZVM", "model": "HYUNDAI IONIQ "},
    {"reg": "EF70 ZYD", "model": "HYUNDAI IONIQ "},
    {"reg": "EK70 AG0", "model": "HYUNDAI IONIQ "},
    {"reg": "EN73 UBZ", "model": "MERCEDES-BENZ EQE 300"},
    {"reg": "FL70 EUV", "model": "HYUNDAI IONIQ "},
    {"reg": "FX19 FXC", "model": "MERCEDES-BENZ E220D "},
    {"reg": "GU72 DVP", "model": "HYUNDAI IONIQ "},
    {"reg": "GX70 UBD", "model": "JAGUAR I-PACE "},
    {"reg": "GY69 NVL", "model": "MERCEDES-BENZ E300 "},
    {"reg": "HX19 VXB", "model": "MERCEDES-BENZ E220D "},
    {"reg": "HX19 VZG", "model": "MERCEDES-BENZ E220D "},
    {"reg": "KF19 UCJ", "model": "TOYOTA COROLLA "},
    {"reg": "KF19 UCN", "model": "TOYOTA COROLLA "},
    {"reg": "KN73 XLA", "model": "MERCEDES-BENZ EQE 300 "},
    {"reg": "KN73 XLB", "model": "MERCEDES-BENZ EQE 300 "},
    {"reg": "KO18 HKE", "model": "MERCEDES-BENZ VITO "},
    {"reg": "KP69 WOR", "model": "MERCEDES-BENZ E220D "},
    {"reg": "KR74 WDL", "model": "MERCEDES-BENZ EQE 350+ "},
    {"reg": "AK69 CKJ", "model": "MERCEDES-BENZ E220D "},
    {"reg": "KT18 ATF", "model": "MERCEDES-BENZ VITO "},
    {"reg": "KT68 VYM", "model": "MERCEDES-BENZ E220D "},
    {"reg": "KU73 MVW", "model": "MERCEDES-BENZ E300 "},
    {"reg": "KL18 TMV", "model": "MERCEDES-BENZ VITO "},
    {"reg": "LA69 AXF", "model": "TESLA MODEL 3 "},
    {"reg": "LA69 AYB", "model": "TESLA MODEL 3 "},
    {"reg": "LB69 OFY", "model": "TESLA MODEL 3 "},
    {"reg": "LD20 COJ", "model": "TESLA MODEL 3 "},
    {"reg": "LD20 FCE", "model": "TESLA MODEL 3 "},
    {"reg": "LL68 CRZ", "model": "TOYOTA AURIS "},
    {"reg": "LL68 CRV", "model": "TOYOTA AURIS "},
    {"reg": "LL68 KRJ", "model": "TOYOTA AURIS "},
    {"reg": "LM68 KRG", "model": "TOYOTA AURIS "},
    {"reg": "LM68 KRJ", "model": "TOYOTA AURIS "},
    {"reg": "LM68 KRO", "model": "TOYOTA AURIS "},
    {"reg": "LM68 KRU", "model": "TOYOTA AURIS "},
    {"reg": "LR16 VTY", "model": "TOYOTA PRIUS "},
    {"reg": "LR69 UCG", "model": "MERCEDES-BENZ E220D "},
    {"reg": "LT69 GSU", "model": "TOYOTA COROLLA "},
    {"reg": "LT69 G5V", "model": "TOYOTA COROLLA "},
    {"reg": "LT69 GSV", "model": "TOYOTA COROLLA "},
    {"reg": "LT69 GSZ", "model": "TOYOTA COROLLA "},
    {"reg": "LT69 GTU", "model": "TOYOTA COROLLA "},
    {"reg": "MD25 AYY", "model": "FORD TOURNEO CUSTOM "},
    {"reg": "MD25 DCX", "model": "FORD TOURNEO CUSTOM "},
    {"reg": "MJ69 YPN", "model": "TESLA MODEL 3 "},
    {"reg": "MV68 OGF", "model": "MERCEDES-BENZ E220D "},
    {"reg": "MV68 OHB", "model": "MERCEDES-BENZ E220D "},
    {"reg": "DU68 SXP", "model": "MERCEDES-BENZ E220D "},
    {"reg": "OW19 XXN", "model": "MERCEDES-BENZ E220D "},
    {"reg": "PO18 UTT", "model": "MERCEDES-BENZ E220D "},
    {"reg": "RE21 NRV", "model": "MG 5 EV"},
    {"reg": "RE21 NRZ", "model": "MG 5 EV"},
    {"reg": "RE21 NSF", "model": "MG 5 EV"},
    {"reg": "RE21 NSU", "model": "MG 5 EV"},
    {"reg": "RX25 CME", "model": "FORD TOURNEO CUSTOM "},
    {"reg": "SF19 WPW", "model": "MERCEDES-BENZ VITO "},
    {"reg": "TD19 5NN", "model": "MERCEDES-BENZ E220D "},
    {"reg": "WG74 KFJ", "model": "MERCEDES-BENZ EQE 300"},
    {"reg": "IH74 E3F", "model": "MERCEDES-BENZ EQE 300 "},
    {"reg": "IHN2 0E3", "model": "TESLA MODEL 3 "},
    {"reg": "IN20 NKU", "model": "MERCEDES-BENZ E300 "},
    {"reg": "WR16 UED", "model": "MERCEDES-BENZ VITO T"},
    {"reg": "WR19 UFG", "model": "MERCEDES-BENZ VITO "},
    {"reg": "YC72 HZM", "model": "MG 5 EV"},
    {"reg": "YF22 UVZ", "model": "MG 5 EV"},
    {"reg": "YF22 UWK", "model": "MG 5 EV"},
    {"reg": "YF22 UWR", "model": "MG 5 EV"},
    {"reg": "YF22 UWT", "model": "MG 5 EV"},
    {"reg": "YF22 UWA", "model": "MG 5 EV"},
    {"reg": "YF22 UXA", "model": "MG 5 EV"},
    {"reg": "YF22 UXC", "model": "MG 5 EV"},
    {"reg": "YF22 UXY", "model": "MG 5 EV"},
    {"reg": "YH71 JHL", "model": "MG 5 EV"}
]

def format_uk_reg(text):
    clean = re.sub(r'[^A-Za-z0-9]', '', text).upper()
    if len(clean) >= 4:
        return f"{clean[:4]} {clean[4:]}".strip()
    return clean

def split_make_model(full_string):
    full_string = full_string.strip()
    parts = full_string.split(" ", 1)
    if len(parts) == 2:
        return parts[0].upper(), parts[1].upper()
    return parts[0].upper(), ""

# --- PDF Generation Modules (Speed Optimized via pageCompression) ---
def generate_permission_letter(data):
    output_filename = "Permission_Letter.pdf"
    c = canvas.Canvas(output_filename, pagesize=letter, pageCompression=1)
    width, height = letter
    bg_path = os.path.join("src", "image_f4efbe.png")
    sig_path = os.path.join("src", "signature.png")
    if os.path.exists(bg_path):
        c.drawImage(bg_path, 0, 0, width=width, height=height)
    c.setFont("Helvetica", 11)
    c.drawRightString(width - 54, 595, data["date"])
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width / 2, 550, "PERMISSION LETTER")
    c.setFont("Helvetica", 11)
    c.drawString(54, 520, "To Whom It May Concern,")
    c.drawString(54, 490, "We confirm that the below vehicle can be used for the carriage of passengers for hire and reward by prior")
    line2_text = f"appointments (private hire) as specified on insurance policy: {data['insurance_policy']}"
    c.drawString(54, 475, line2_text)
    c.drawString(54, 460, "We authorise and give permission to the following individual to use the vehicle for all private hire bookings")
    c.drawString(54, 445, "from UBER, BOLT, OLA , FREE NOW app , WHEELY and other private hire operators.")
    fields = [
        ("Vehicle Registration", data["registration"]),
        ("Make and Model", data["make_model"]),
        ("Driver Name", data["driver_name"]),
        ("Address", data["address"]),
        ("Driving Licence No", data["license_no"]),
    ]
    for i, (label, val) in enumerate(fields):
        y = 405 - (i * 22)
        c.setFont("Helvetica", 11)
        c.drawString(54, y, f"{label} :")
        c.drawString(180, y, val)
    c.drawString(54, 275, "Hire start date.")
    c.drawString(145, 275, ":")
    c.drawString(160, 275, data["start_date"])
    c.drawString(54, 260, "Hire end date")
    c.drawString(145, 260, ":")
    c.drawString(160, 260, data["end_date"])
    c.drawString(54, 220, "Regards,")
    if os.path.exists(sig_path):
        c.drawImage(sig_path, 40, 120, width=280, height=115, mask='auto')
    c.setFont("Helvetica", 11)
    c.drawString(54, 115, "Muhammad Sohail Qureshi")
    c.drawString(54, 100, "Director(FA-IBI LTD)")
    c.save()
    return output_filename

def generate_contract(data):
    output_filename = "FA_IBI_Contract.pdf"
    c = canvas.Canvas(output_filename, pagesize=letter, pageCompression=1)
    width, height = letter
    bg1_path = os.path.join("src", "Contract Blank.png")
    bg2_path = os.path.join("src", "Contarct Blank 2.png")

    if os.path.exists(bg1_path):
        c.drawImage(bg1_path, 0, 0, width=width, height=height)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(390, 715, f"{data['contract_no']}")
    c.setFont("Helvetica", 10)
    c.drawString(110, 663, f"{data['driver_name']}")
    c.drawString(505, 663, f"{data['dob']}")
    c.drawString(100, 627, f"{data['address']}")
    c.drawString(500, 627, f"{data['postcode']}")
    c.drawString(115, 591, f"{data['license_no']}")
    c.drawString(340, 591, f"{data['issuing_authority']}")
    c.drawString(495, 591, f"{data['expiry_date']}")
    c.drawString(75, 555, f"{data['phone']}")
    c.drawString(295, 555, f"{data['email']}")
    c.drawString(135, 417, f"{data['rent']}")
    c.drawString(75, 362, f"{data['rate']}")
    c.drawString(115, 319, f"{data['deposit']}")
    c.drawString(135, 261, f"{data['start_date']}")
    c.drawString(190, 246, f"{data['expected_return']}")
    c.drawString(100, 193, f"{data['car_make']}")
    c.drawString(440, 193, f"{data['registration']}")
    c.drawString(505, 193, f"{data['car_model']}")
    c.drawString(85, 108, f"{data['date']}")
    c.showPage()

    if os.path.exists(bg2_path):
        c.drawImage(bg2_path, 0, 0, width=width, height=height)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(145, 742, f"{data['contract_no']}")
    c.drawString(340, 742, f"{data['registration']}")
    c.drawString(235, 34, f"{data['date']}")
    c.save()
    return output_filename

# --- Web Interface Design Layout ---
st.set_page_config(page_title="FA-IBI Workspace", layout="centered")

st.markdown("""
    <style>
    #MainMenu, footer, header, [data-testid="stToolbar"], .viewerBadge_container__1743q, [class*="viewerBadge"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
    }
    .main .block-container {
        padding-top: 1rem !important;
        padding-bottom: 5rem !important;
        max-width: 100% !important;
    }
    .vch-branding-cover-fixed {
        position: fixed !important;
        bottom: 0 !important;
        right: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        background-color: #0e1117 !important;
        text-align: center !important;
        padding: 14px 0 !important;
        font-size: 14px !important;
        color: #888888 !important;
        border-top: 1px solid #1f2937 !important;
        z-index: 2147483647 !important;
    }
    .vch-branding-cover-fixed a {
        color: #FF8C00 !important;
        font-weight: bold !important;
        text-decoration: none !important;
    }
    
    [data-testid="stFileUploader"] {
        max-width: 100%;
    }
    [data-testid="stFileUploaderDropzone"] {
        padding: 0.5rem 1rem !important;
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: flex-start !important;
        gap: 15px !important;
    }
    [data-testid="stFileUploaderDropzone"] > div {
        margin: 0 !important;
        padding: 0 !important;
    }
    [data-testid="stFileUploaderDropzone"] [data-testid="stTypography"] {
        font-size: 11px !important;
        color: #888888 !important;
        margin-left: auto !important;
        white-space: nowrap;
    }
    
    @media screen and (max-width: 768px) {
        input, select, textarea, .stSelectbox, div[data-baseweb="select"] {
            font-size: 16px !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

# --- SECURE HARDWARE MEMORY AUTOLOGIN ENGINE ---
if "hardware_authenticated" not in st.session_state:
    st.session_state["hardware_authenticated"] = False

if st.query_params.get("session") == "active":
    st.session_state["hardware_authenticated"] = True

if not st.session_state["hardware_authenticated"]:
    col_gate, _ = st.columns([1, 2])
    with col_gate:
        access_code = st.text_input("System Access", type="password", label_visibility="collapsed", placeholder="Enter key...")
    if access_code == st.secrets["ACCESS_KEY"]:
        st.session_state["hardware_authenticated"] = True
        st.query_params["session"] = "active"
        st.rerun()
    else:
        st.stop()

# --- Core App Title ---
st.title("FA-IBI Master Document Workspace")

# Initialize Shared Memory Variables
for key in ["ocr_name", "ocr_licence", "ocr_address", "ocr_postcode", "ocr_dob", "ocr_expiry", "sel_reg", "sel_make", "sel_model", "scan_success", "db_success"]:
    if key not in st.session_state: st.session_state[key] = ""
if "scan_trigger" not in st.session_state: st.session_state["scan_trigger"] = False
if "db_trigger" not in st.session_state: st.session_state["db_trigger"] = False

# --- Workspace Navigation Tabs ---
tab1, tab2 = st.tabs(["📝 Permission Letter Creator", "📜 FA-IBI Contract Generator"])

def render_automation_controls(context_key):
    st.markdown("#### 🎛️ Data Automation Scanners")
    
    if st.session_state["scan_success"] and st.session_state["scan_trigger"] == context_key:
        st.success(st.session_state["scan_success"])
    if st.session_state["db_success"] and st.session_state["db_trigger"] == context_key:
        st.info(st.session_state["db_success"])
        
    col_scan, col_fleet = st.columns([1, 1])
    
    with col_scan:
        uploaded_license = st.file_uploader("📷 Driver's License Scanner", type=["jpg", "png", "jpeg"], key=f"uploader_{context_key}")
        if uploaded_license is not None and pytesseract is not None:
            with st.spinner("Scanning matrix arrays..."):
                img = Image.open(uploaded_license).convert("RGB")
                img_np = np.array(img)
                h, w = img_np.shape[:2]
                if max(h, w) > 1200:
                    scale = 1200 / max(h, w)
                    img_np = cv2.resize(img_np, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
                gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
                _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                custom_config = r'--oem 3 --psm 6'
                raw_ocr_string = pytesseract.image_to_string(thresh, config=custom_config)
                lines = [line.strip() for line in raw_ocr_string.split("\n") if line.strip()]
                
                extracted_last, extracted_first, extracted_licence, extracted_address_chunks = "", "", "", []
                extracted_dob, extracted_expiry = "", ""
                field1_re = re.compile(r'^[1lI]\.?\s+([A-Z][A-Z \'-]+)$')
                field2_re = re.compile(r'^2\.?\s+([A-Z][A-Z \'-]+)$')
                field4b_re = re.compile(r'^4[B8]\.?\s*([0-9./-]+)')
                field4a_re = re.compile(r'^4[A4]\.?\s*([0-9./-]+)')
                field5_re = re.compile(r'^5\.?\s+([A-Z0-9]{8,20})$')
                field8_re = re.compile(r'^[8B]\.?\s+(.+)$')
                stop_prefixes = ("3", "4", "5", "6", "7", "9", "UK", "DRIVING", "DVLA")
                
                for index, raw_line in enumerate(lines):
                    item_upper = raw_line.strip().upper()
                    if field1_re.match(item_upper) and not extracted_last: extracted_last = field1_re.match(item_upper).group(1).strip(); continue
                    if field2_re.match(item_upper) and not extracted_first: extracted_first = field2_re.match(item_upper).group(1).strip(); continue
                    if field4a_re.match(item_upper) and not extracted_dob: extracted_dob = field4a_re.match(item_upper).group(1).strip(); continue
                    if field4b_re.match(item_upper) and not extracted_expiry: extracted_expiry = field4b_re.match(item_upper).group(1).strip(); continue
                    if field5_re.match(item_upper) and not extracted_licence: extracted_licence = re.sub(r'\s', '', field5_re.match(item_upper).group(1)); continue
                    if field8_re.match(item_upper):
                        first_line_addr = field8_re.match(item_upper).group(1).strip()
                        if len(first_line_addr) > 2: extracted_address_chunks.append(first_line_addr)
                        for step in range(1, 5):
                            if index + step < len(lines):
                                next_chunk = lines[index + step].strip().upper()
                                if next_chunk.startswith(stop_prefixes): break
                                if len(next_chunk) > 3: extracted_address_chunks.append(next_chunk)
                        continue
                        
                full_addr_str = ", ".join(extracted_address_chunks)
                postcode_match = re.search(r'\b([A-Z]{1,2}[0-9][A-Z0-9]?\s?[0-9][A-Z]{2})\b', full_addr_str)
                if postcode_match:
                    st.session_state.ocr_postcode = postcode_match.group(1).strip()
                    full_addr_str = full_addr_str.replace(postcode_match.group(1), "").strip(", ")
                if extracted_first or extracted_last: st.session_state.ocr_name = f"{extracted_first} {extracted_last}".strip()
                if QQ := extracted_licence: st.session_state.ocr_licence = QQ
                if extracted_address_chunks: st.session_state.ocr_address = full_addr_str
                if extracted_dob: st.session_state.ocr_dob = extracted_dob
                if extracted_expiry: st.session_state.ocr_expiry = extracted_expiry
                
                st.session_state["scan_success"] = "✅ Driver's license successfully scanned and mapped to form fields!"
                st.session_state["scan_trigger"] = context_key
                st.rerun()
                
    with col_fleet:
        fleet_options = ["-- Manual Entry --"] + [f"{v['reg']} ({v['model']})" for v in FLEET_VEHICLES]
        current_sel_val = "-- Manual Entry --"
        if st.session_state.sel_reg:
            matched_opt = [o for o in fleet_options if o.startswith(st.session_state.sel_reg)]
            if matched_opt: current_sel_val = matched_opt[0]
            
        selected_vehicle = st.selectbox("🚗 Select Vehicle from Fleet", fleet_options, index=fleet_options.index(current_sel_val), key=f"fleet_{context_key}")
        if selected_vehicle != "-- Manual Entry --":
            reg_match = selected_vehicle.split(" (")[0]
            if st.session_state.sel_reg != reg_match:
                matched_car = next((v for v in FLEET_VEHICLES if v["reg"] == reg_match), None)
                if matched_car:
                    st.session_state.sel_reg = matched_car["reg"]
                    make_part, model_part = split_make_model(matched_car["model"])
                    st.session_state.sel_make = make_part
                    st.session_state.sel_model = model_part
                    st.session_state["db_success"] = f"✅ Vehicle {reg_match} pulled from Database successfully!"
                    st.session_state["db_trigger"] = context_key
                    st.rerun()
        else:
            if st.session_state.sel_reg != "":
                st.session_state.sel_reg, st.session_state.sel_make, st.session_state.sel_model = "", "", ""
                st.session_state["db_success"] = ""
                st.rerun()

# ==========================================
# --- TAB 1: PERMISSION LETTER WORKFLOW ---
# ==========================================
with tab1:
    render_automation_controls(context_key="tab1")
    st.markdown("---")
    with st.form("permission_letter_form_v5"):
        col1, col2 = st.columns(2)
        with col1:
            p_date = st.date_input("Document Issue Date", datetime.now(), format="DD/MM/YYYY")
            p_insurance = st.text_input("Insurance Policy No", "HAVFL-000211")
            p_reg = st.text_input("Vehicle Registration", value=st.session_state.sel_reg)
            p_model = st.text_input("Make & Model", value=f"{st.session_state.sel_make} {st.session_state.sel_model}".strip())
        with col2:
            p_name = st.text_input("Driver Full Name", value=st.session_state.ocr_name)
            p_licence = st.text_input("Driving Licence No", value=st.session_state.ocr_licence)
            p_start = st.date_input("Hire Start Date", datetime.now(), format="DD/MM/YYYY")
            p_end = st.date_input("Hire End Date", datetime.now(), format="DD/MM/YYYY")
        p_address = st.text_area("Driver Residential Address", value=st.session_state.ocr_address)
        p_submitted = st.form_submit_button("Generate Permission Letter PDF")

    if p_submitted:
        p_payload = {
            "date": p_date.strftime("%d/%m/%Y"),
            "insurance_policy": p_insurance,
            "registration": format_uk_reg(p_reg),
            "make_model": p_model.upper(),
            "driver_name": p_name.upper(),
            "address": p_address.upper(),
            "license_no": p_licence.upper(),
            "start_date": p_start.strftime("%d/%m/%Y"),
            "end_date": p_end.strftime("%d/%m/%Y")
        }
        pdf_out = generate_permission_letter(p_payload)
        with open(pdf_out, "rb") as f:
            st.download_button("Download Permission Letter PDF", data=f, file_name="Permission_Letter.pdf", mime="application/pdf")

# ==========================================
# --- TAB 2: FA-IBI CONTRACT WORKFLOW ----
# ==========================================
with tab2:
    render_automation_controls(context_key="tab2")
    st.markdown("---")
    
    # Store payload globally in session state to handle form button life cycle refreshes natively
    if "contract_payload" not in st.session_state:
        st.session_state.contract_payload = None

    with st.form("contract_generation_form_v4"):
        st.subheader("Hirer Details Section")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            c_contract_no = st.text_input("Contract Number", value="1608/MANJESH/LA69AXF/2026")
            c_name = st.text_input("Full Name", value=st.session_state.ocr_name)
            c_address = st.text_area("Address Line", value=st.session_state.ocr_address)
            c_postcode = st.text_input("Postcode", value=st.session_state.ocr_postcode)
            c_dob = st.text_input("Date of Birth", value=st.session_state.ocr_dob)
        with col_c2:
            c_date = st.date_input("Contract Signing Date", datetime.now(), format="DD/MM/YYYY")
            c_licence_no = st.text_input("License No", value=st.session_state.ocr_licence)
            c_expiry = st.text_input("Date of Expiry", value=st.session_state.ocr_expiry)
            c_authority = st.text_input("Issuing Authority", value="DVLA")
            c_phone = st.text_input("Ph")
            c_email = st.text_input("Email")

        st.markdown("---")
        st.subheader("Hire Payment Parameters")
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1: c_rent = st.text_input("The Rent (£ / Week)", value="250/-")
        with col_p2: c_rate = st.text_input("The Rate (Excess Charge)", value="20/-")
        with col_p3: c_deposit = st.text_input("Deposit Paid (£)", value="500/-")

        st.markdown("---")
        st.subheader("Hire Period Tracking")
        col_t1, col_t2 = st.columns(2)
        with col_t1: c_start = st.date_input("Date Hire Start", datetime.now(), format="DD/MM/YYYY")
        with col_
