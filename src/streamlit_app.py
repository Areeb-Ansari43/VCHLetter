import streamlit as st
import os, re, io
from PIL import Image, ImageFilter, ImageOps, ImageEnhance
from datetime import datetime, date
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

try:
    import pytesseract
except ImportError:
    pytesseract = None

SRC_DIR = os.path.dirname(os.path.abspath(__file__))

FLEET_VEHICLES = [
    {"reg": "AF70 MYK", "model": "TESLA MODEL 3"},
    {"reg": "BD20 XPU", "model": "MERCEDES-BENZ E300"},
    {"reg": "BJ20 L6X", "model": "TESLA MODEL 3"},
    {"reg": "BK70 WYM", "model": "TESLA MODEL 3"},
    {"reg": "BL19 JDZ", "model": "MERCEDES-BENZ E220D"},
    {"reg": "BN17 CVA", "model": "MERCEDES-BENZ VITO"},
    {"reg": "BN20 MXL", "model": "JAGUAR I-PACE"},
    {"reg": "BN60 MYZ", "model": "MERCEDES-BENZ E220D"},
    {"reg": "BN60 NHP", "model": "MERCEDES-BENZ E220D"},
    {"reg": "BT69 TEJ", "model": "TESLA MODEL 3"},
    {"reg": "RE21 NRX", "model": "MG 5 EV"},
    {"reg": "BU19 ACJ", "model": "MERCEDES-BENZ E220D"},
    {"reg": "BV18 WNA", "model": "MERCEDES-BENZ E220D"},
    {"reg": "BX19 ZMY", "model": "MERCEDES-BENZ E220D"},
    {"reg": "CA19 UTF", "model": "MERCEDES-BENZ E220D"},
    {"reg": "EF70 ZPZ", "model": "HYUNDAI IONIQ"},
    {"reg": "EF70 ZVM", "model": "HYUNDAI IONIQ"},
    {"reg": "EF70 ZYD", "model": "HYUNDAI IONIQ"},
    {"reg": "EK70 AG0", "model": "HYUNDAI IONIQ"},
    {"reg": "EN73 UBZ", "model": "MERCEDES-BENZ EQE 300"},
    {"reg": "FL70 EUV", "model": "HYUNDAI IONIQ"},
    {"reg": "FX19 FXC", "model": "MERCEDES-BENZ E220D"},
    {"reg": "GU72 DVP", "model": "HYUNDAI IONIQ"},
    {"reg": "GX70 UBD", "model": "JAGUAR I-PACE"},
    {"reg": "GY69 NVL", "model": "MERCEDES-BENZ E300"},
    {"reg": "HX19 VXB", "model": "MERCEDES-BENZ E220D"},
    {"reg": "HX19 VZG", "model": "MERCEDES-BENZ E220D"},
    {"reg": "KF19 UCJ", "model": "TOYOTA COROLLA"},
    {"reg": "KF19 UCN", "model": "TOYOTA COROLLA"},
    {"reg": "KN73 XLA", "model": "MERCEDES-BENZ EQE 300"},
    {"reg": "KN73 XLB", "model": "MERCEDES-BENZ EQE 300"},
    {"reg": "KO18 HKE", "model": "MERCEDES-BENZ VITO"},
    {"reg": "KP69 WOR", "model": "MERCEDES-BENZ E220D"},
    {"reg": "KR74 WDL", "model": "MERCEDES-BENZ EQE 350+"},
    {"reg": "AK69 CKJ", "model": "MERCEDES-BENZ E220D"},
    {"reg": "KT18 ATF", "model": "MERCEDES-BENZ VITO"},
    {"reg": "KT68 VYM", "model": "MERCEDES-BENZ E220D"},
    {"reg": "KU73 MVW", "model": "MERCEDES-BENZ E300"},
    {"reg": "KL18 TMV", "model": "MERCEDES-BENZ VITO"},
    {"reg": "LA69 AXF", "model": "TESLA MODEL 3"},
    {"reg": "LA69 AYB", "model": "TESLA MODEL 3"},
    {"reg": "LB69 OFY", "model": "TESLA MODEL 3"},
    {"reg": "LD20 COJ", "model": "TESLA MODEL 3"},
    {"reg": "LD20 FCE", "model": "TESLA MODEL 3"},
    {"reg": "LL68 CRZ", "model": "TOYOTA AURIS"},
    {"reg": "LL68 CRV", "model": "TOYOTA AURIS"},
    {"reg": "LL68 KRJ", "model": "TOYOTA AURIS"},
    {"reg": "LM68 KRG", "model": "TOYOTA AURIS"},
    {"reg": "LM68 KRJ", "model": "TOYOTA AURIS"},
    {"reg": "LM68 KRO", "model": "TOYOTA AURIS"},
    {"reg": "LM68 KRU", "model": "TOYOTA AURIS"},
    {"reg": "LR16 VTY", "model": "TOYOTA PRIUS"},
    {"reg": "LR69 UCG", "model": "MERCEDES-BENZ E220D"},
    {"reg": "LT69 GSU", "model": "TOYOTA COROLLA"},
    {"reg": "LT69 G5V", "model": "TOYOTA COROLLA"},
    {"reg": "LT69 GSV", "model": "TOYOTA COROLLA"},
    {"reg": "LT69 GSZ", "model": "TOYOTA COROLLA"},
    {"reg": "LT69 GTU", "model": "TOYOTA COROLLA"},
    {"reg": "MD25 AYY", "model": "FORD TOURNEO CUSTOM"},
    {"reg": "MD25 DCX", "model": "FORD TOURNEO CUSTOM"},
    {"reg": "MJ69 YPN", "model": "TESLA MODEL 3"},
    {"reg": "MV68 OGF", "model": "MERCEDES-BENZ E220D"},
    {"reg": "MV68 OHB", "model": "MERCEDES-BENZ E220D"},
    {"reg": "DU68 SXP", "model": "MERCEDES-BENZ E220D"},
    {"reg": "OW19 XXN", "model": "MERCEDES-BENZ E220D"},
    {"reg": "PO18 UTT", "model": "MERCEDES-BENZ E220D"},
    {"reg": "RE21 NRV", "model": "MG 5 EV"},
    {"reg": "RE21 NRZ", "model": "MG 5 EV"},
    {"reg": "RE21 NSF", "model": "MG 5 EV"},
    {"reg": "RE21 NSU", "model": "MG 5 EV"},
    {"reg": "RX25 CME", "model": "FORD TOURNEO CUSTOM"},
    {"reg": "SF19 WPW", "model": "MERCEDES-BENZ VITO"},
    {"reg": "TD19 5NN", "model": "MERCEDES-BENZ E220D"},
    {"reg": "WG74 KFJ", "model": "MERCEDES-BENZ EQE 300"},
    {"reg": "IH74 E3F", "model": "MERCEDES-BENZ EQE 300"},
    {"reg": "IHN2 0E3", "model": "TESLA MODEL 3"},
    {"reg": "IN20 NKU", "model": "MERCEDES-BENZ E300"},
    {"reg": "WR16 UED", "model": "MERCEDES-BENZ VITO"},
    {"reg": "WR19 UFG", "model": "MERCEDES-BENZ VITO"},
    {"reg": "YC72 HZM", "model": "MG 5 EV"},
    {"reg": "YF22 UVZ", "model": "MG 5 EV"},
    {"reg": "YF22 UWK", "model": "MG 5 EV"},
    {"reg": "YF22 UWR", "model": "MG 5 EV"},
    {"reg": "YF22 UWT", "model": "MG 5 EV"},
    {"reg": "YF22 UWA", "model": "MG 5 EV"},
    {"reg": "YF22 UXA", "model": "MG 5 EV"},
    {"reg": "YF22 UXC", "model": "MG 5 EV"},
    {"reg": "YF22 UXY", "model": "MG 5 EV"},
    {"reg": "YH71 JHL", "model": "MG 5 EV"},
]

# ─────────────────────────────────────────────
#  HELPERS & PARSERS
# ─────────────────────────────────────────────
def format_uk_reg(text):
    clean = re.sub(r"[^A-Za-z0-9]", "", text).upper()
    return f"{clean[:4]} {clean[4:]}".strip() if len(clean) >= 4 else clean

def split_make_model(s):
    parts = s.strip().split(" ", 1)
    return (parts[0].upper(), parts[1].upper()) if len(parts) == 2 else (parts[0].upper(), "")

def clean_name(s):
    s = re.sub(r"[^A-Z '\-]", " ", s.upper())
    words = [w for w in s.split() if len(w) > 1 and not re.match(r"^\d+$", w)]
    return " ".join(words).strip()

def normalize_date(s: str) -> str:
    if not s: return ""
    return re.sub(r"[.\-]", "/", s.strip())

def first_date(fragment: str) -> str:
    m = re.search(r"\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}", fragment)
    return normalize_date(m.group(0)) if m else ""

def strip_address_noise(s: str) -> str:
    s = s.upper()
    s = re.sub(r"UNITED\s+\w*\s*KINGDOM", "", s)
    s = re.sub(r"\b(ENGLAND|SCOTLAND|WALES|NORTHERN\s+IRELAND)\b", "", s)
    s = re.sub(r"\bDVLA\b|\bDVLNI\b", "", s)
    s = re.sub(r"\b[1-9][ABCDE58]?\.?\s*", " ", s) 
    s = re.sub(r"\b(19|20)\d{2}\b", " ", s)
    s = re.sub(r"[A-Z]{5}\d{6}[A-Z0-9]{4,8}", " ", s)
    s = re.sub(r"[^A-Z0-9 ,'\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip().strip(",").strip()
    return s

def extract_postcode(text: str) -> str:
    m = re.search(r"\b([A-Z]{1,2}[0-9][A-Z0-9]?\s*[0-9][A-Z]{2})\b", text.upper())
    return m.group(1).strip() if m else ""

def _grab(blob, start_pats, end_pats):
    for sp in start_pats:
        for ep in end_pats:
            m = re.search(sp + r"\s*(.*?)\s*" + ep, blob, re.DOTALL)
            if m and m.group(1).strip():
                return m.group(1).strip()
    return ""

# ─────────────────────────────────────────────
#  OCR CORE ENGINE 
# ─────────────────────────────────────────────
def run_ocr(uploaded_file) -> str:
    img = Image.open(uploaded_file).convert("RGB")
    w, h = img.size
    if max(w, h) < 1800:
        scale = 1800 / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    img = ImageOps.grayscale(img)
    img = ImageEnhance.Contrast(img).enhance(2.5) 
    img = img.filter(ImageFilter.SHARPEN)
    import numpy as np
    arr = np.array(img)
    hist, _ = np.histogram(arr.flatten(), 256, (0, 256))
    total = arr.size; ts = int(np.dot(np.arange(256), hist))
    sb, wb, bv, thresh = 0, 0, 0, 128
    for i in range(256):
        wb += hist[i]
        if not wb: continue
        wf = total - wb
        if not wf: break
        sb += i * hist[i]
        mb = sb / wb; mf = (ts - sb) / wf
        v = wb * wf * (mb - mf) ** 2
        if v > bv: bv = v; thresh = i
    img = img.point(lambda p: 255 if p > thresh else 0)
    return pytesseract.image_to_string(img, config=r"--oem 3 --psm 6")

def parse_licence(raw: str) -> dict:
    blob = " " + re.sub(r"\s+", " ", raw.upper()) + " "

    # 1. Surname
    surname = clean_name(_grab(blob, [r"1\."], [r"2\."]))
    if not surname:
        m = re.search(r"1\.\s*([A-Z\-]+)", blob)
        if m: surname = m.group(1).strip()

    # 2. Forename
    forename = clean_name(_grab(blob, [r"2\."], [r"3\."]))
    if not forename:
        m = re.search(r"2\.\s*([A-Z\-]+)", blob)
        if m: forename = m.group(1).strip()

    # 3. DOB
    raw_3 = _grab(blob, [r"3\."], [r"4[Aa]\b"])
    dob = first_date(raw_3)
    if not dob:
        m = re.search(r"3\.\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})", blob)
        if m: dob = normalize_date(m.group(1))

    # 4b. Date of Expiry
    raw_4b = _grab(blob, [r"4[Bb]\.?"], [r"4[Cc]", r"5\."])
    expiry = first_date(raw_4b)
    if not expiry:
        m = re.search(r"4[Bb]\.?\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})", blob)
        if m: expiry = normalize_date(m.group(1))

    # 5. Licence Number (Supports custom ANDE012345678 and official structures)
    licence = ""
    raw_5 = _grab(blob, [r"5\."], [r"6\.", r"7\."])
    if raw_5:
        licence = re.sub(r"[^A-Z0-9]", "", raw_5.split()[0])
    if not licence or len(licence) < 5:
        m = re.search(r"5\.\s*([A-Z0-9]{5,18})", blob)
        if m: licence = m.group(1).strip()

    # 8. Address Separation Block
    raw_8 = _grab(blob, [r"8\."], [r"9\."])
    if not raw_8:
        m = re.search(r"8\.\s*(.*?)(?=\s*9\.)", blob, re.DOTALL)
        if m: raw_8 = m.group(1).strip()
        
    address_block = raw_8 if raw_8 else blob
    postcode = extract_postcode(address_block)
    
    # Clean noise away explicitly from Address string context
    addr_clean = strip_address_noise(address_block)
    if postcode:
        addr_clean = re.sub(re.escape(postcode), "", addr_clean, flags=re.I)
    
    # Eliminate leading field tags from the final text view box
    addr_clean = re.sub(r"^[0-9]\.?\s*", "", addr_clean.strip()).strip(", ").strip()

    return {
        "surname": surname, "forename": forename,
        "dob": dob, "expiry": expiry,
        "licence": licence,
        "address": addr_clean, "postcode": postcode,
    }

# ─────────────────────────────────────────────
#  PDF GENERATION ENGINE (Restored Coordinate Set)
# ─────────────────────────────────────────────
def _find_img(base_name):
    for ext in [".jpg", ".png", ".jpeg", ".JPG", ".PNG"]:
        p = os.path.join(SRC_DIR, base_name + ext)
        if os.path.exists(p): return p
    return None

def generate_permission_letter(data: dict) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter, pageCompression=1)
    pw, ph = letter
    bg = _find_img("image_f4efbe")
    sig = _find_img("signature")
    if bg: c.drawImage(bg, 0, 0, width=pw, height=ph)
    
    c.setFont("Helvetica", 11)
    c.drawRightString(pw - 54, 595, data["date"])
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(pw / 2, 550, "PERMISSION LETTER")
    c.setFont("Helvetica", 11)
    c.drawString(54, 520, "To Whom It May Concern,")
    c.drawString(54, 490, "We confirm that the below vehicle can be used for the carriage of passengers for hire and reward by prior")
    c.drawString(54, 475, f"appointments (private hire) as specified on insurance policy: {data['insurance_policy']}")
    c.drawString(54, 460, "We authorise and give permission to the following individual to use the vehicle for all private hire bookings")
    c.drawString(54, 445, "from UBER, BOLT, OLA, FREE NOW app, WHEELY and other private hire operators.")
    
    for i, (label, val) in enumerate([
        ("Vehicle Registration", data["registration"]),
        ("Make and Model",       data["make_model"]),
        ("Driver Name",          data["driver_name"]),
        ("Address",              data["address"]),
        ("Driving Licence No",   data["license_no"]),
    ]):
        y = 405 - i * 22
        c.drawString(54, y, f"{label} :"); c.drawString(180, y, val)
        
    c.drawString(54, 275, "Hire start date. :"); c.drawString(160, 275, data["start_date"])
    c.drawString(54, 260, "Hire end date    :"); c.drawString(160, 260, data["end_date"])
    c.drawString(54, 220, "Regards,")
    
    if os.path.exists(sig) if sig else False: 
        c.drawImage(sig, 40, 120, width=280, height=115, mask="auto")
    c.drawString(54, 115, "Muhammad Sohail Qureshi")
    c.drawString(54, 100, "Director (FA-IBI LTD)")
    c.save(); buf.seek(0); return buf.getvalue()

def generate_contract(data: dict) -> bytes:
    buf = io.BytesIO()
    cv = canvas.Canvas(buf, pagesize=letter, pageCompression=1)
    W, H = 612, 792
    
    bg1 = _find_img("1")
    bg2 = _find_img("2")

    # PAGE 1 Background Setup
    if bg1: cv.drawImage(bg1, 0, 0, width=W, height=H)
    
    cv.setFont("Helvetica-Bold", 9)
    cv.drawString(312, 712, data.get("contract_no", ""))
    cv.drawString(510, 712, data.get("date", ""))
    
    # Offset coordinates mapped directly over form line regions
    cv.setFont("Helvetica", 8)
    cv.drawString(115, 665, data.get("driver_name", ""))
    cv.drawString(465, 665, data.get("dob", ""))
    cv.drawString(115, 641, data.get("address", ""))
    cv.drawString(455, 641, data.get("postcode", ""))
    cv.drawString(115, 618, data.get("license_no", ""))
    cv.drawString(290, 618, data.get("issuing_authority", ""))
    cv.drawString(485, 618, data.get("expiry_date", ""))
    cv.drawString(115, 594, data.get("phone", ""))
    cv.drawString(260, 594, data.get("email", ""))

    # Financial Parameter Strings
    cv.setFont("Helvetica-Bold", 9)
    cv.drawString(125, 516, data.get("rent", ""))
    cv.drawString(145, 462, data.get("rate", ""))
    cv.drawString(125, 396, data.get("deposit", ""))

    # Hire Duration Strings
    cv.setFont("Helvetica", 8)
    cv.drawString(125, 268, data.get("start_date", ""))
    cv.drawString(210, 252, data.get("expected_return", ""))

    # Vehicle Parameter Strings
    cv.setFont("Helvetica-Bold", 8.5)
    cv.drawString(80, 166, data.get("car_make", ""))
    cv.drawString(285, 166, data.get("registration", ""))
    cv.drawString(460, 166, data.get("car_model", ""))

    # PAGE 2 Background Setup
    cv.showPage()
    if bg2: cv.drawImage(bg2, 0, 0, width=W, height=H)
        
    cv.setFont("Helvetica-Bold", 9)
    cv.drawString(145, 713, data.get("contract_no", ""))
    cv.drawString(390, 713, data.get("registration", ""))

    cv.save(); buf.seek(0); return buf.getvalue()

# ─────────────────────────────────────────────
#  STREAMLIT APPLICATION RENDERING ENGINE
# ─────────────────────────────────────────────
st.set_page_config(page_title="FA-IBI Workspace", layout="centered")
st.markdown("<style>#MainMenu,footer,header,[data-testid='stToolbar']{display:none!important;}</style>", unsafe_allow_html=True)

if "authenticated" not in st.session_state: st.session_state.authenticated = False
if st.query_params.get("session") == "active": st.session_state.authenticated = True
if not st.session_state.authenticated:
    code = st.text_input("System Access", type="password", placeholder="Enter key…")
    if code == st.secrets.get("ACCESS_KEY", ""):
        st.session_state.authenticated = True
        st.query_params["session"] = "active"; st.rerun()
    else: st.stop()

# Initialize State Keys with explicitly bound active tab controller
for k, v in dict(
    ocr_name="", ocr_licence="", ocr_address="", ocr_postcode="",
    ocr_dob="", ocr_expiry="", last_scan_id="",
    sel_reg="", sel_make="", sel_model="",
    scan_msg="", fleet_msg="",
    perm_pdf=None, contract_pdf=None, contract_no="",
    pending_contract=None, current_tab=0
).items():
    if k not in st.session_state: st.session_state[k] = v

st.title("FA-IBI Master Document Workspace")

# GLOBAL DATA AUTOMATION PANEL
st.markdown("### 🎛️ Shared Data Automation Panel")
if st.session_state.scan_msg:  st.success(st.session_state.scan_msg)
if st.session_state.fleet_msg: st.info(st.session_state.fleet_msg)
col_scan, col_fleet = st.columns(2)

with col_scan:
    uploaded = st.file_uploader("📷 Driver's Licence Scanner", type=["jpg","png","jpeg"], key="global_engine_scanner")
    if uploaded and pytesseract:
        fid = f"{uploaded.name}_{uploaded.size}"
        if st.session_state.last_scan_id != fid:
            with st.spinner("Processing Elements..."):
                try:
                    raw = run_ocr(uploaded)
                    p = parse_licence(raw)
                    st.session_state.ocr_name     = f"{p['forename']} {p['surname']}".strip()
                    st.session_state.ocr_licence  = p["licence"]
                    st.session_state.ocr_address  = p["address"]
                    st.session_state.ocr_postcode = p["postcode"]
                    st.session_state.ocr_dob      = p["dob"]
                    st.session_state.ocr_expiry   = p["expiry"]
                    st.session_state.scan_msg     = "✅ Licence scanned successfully!"
                except Exception as e:
                    st.session_state.scan_msg = f"⚠️ Scan parsing failed: {e}"
                st.session_state.last_scan_id = fid
            st.rerun()

with col_fleet:
    opts = ["-- Manual Entry --"] + [f"{v['reg']} ({v['model']})" for v in FLEET_VEHICLES]
    cur = "-- Manual Entry --"
    if st.session_state.sel_reg:
        hit = [o for o in opts if o.startswith(st.session_state.sel_reg)]
        if hit: cur = hit[0]
    chosen = st.selectbox("🚗 Select Fleet Vehicle", opts, index=opts.index(cur), key="global_engine_fleet")
    if chosen != "-- Manual Entry --":
        rk = chosen.split(" (")[0]
        if st.session_state.sel_reg != rk:
            car = next((v for v in FLEET_VEHICLES if v["reg"] == rk), None)
            if car:
                mk, mo = split_make_model(car["model"])
                st.session_state.sel_reg = car["reg"]
                st.session_state.sel_make = mk; st.session_state.sel_model = mo
                st.session_state.fleet_msg = f"✅ Vehicle fields sync verified!"; st.rerun()
    else:
        if st.session_state.sel_reg:
            st.session_state.sel_reg = st.session_state.sel_make = st.session_state.sel_model = ""
            st.session_state.fleet_msg = ""; st.rerun()

st.markdown("---")

if st.session_state.pending_contract:
    try:
        st.session_state.contract_pdf = generate_contract(st.session_state.pending_contract)
        st.session_state.contract_no  = st.session_state.pending_contract["contract_no"]
    except Exception as e:
        st.error(f"Render Error: {e}")
    finally:
        st.session_state.pending_contract = None

# Tab controller callbacks to preserve current selection index view
def set_active_tab(tab_index):
    st.session_state.current_tab = tab_index

tab1, tab2 = st.tabs(["📝 Permission Letter", "📜 Contract Generator"])

with tab1:
    # Trigger active index capture context
    if st.session_state.current_tab != 0:
        set_active_tab(0)
        
    with st.form("perm_form"):
        c1, c2 = st.columns(2)
        with c1:
            p_date = st.date_input("Document Date", datetime.now(), format="DD/MM/YYYY", key="p_form_date")
            p_ins  = st.text_input("Insurance Policy No", "HAVFL-000211")
            p_reg  = st.text_input("Vehicle Registration", value=st.session_state.sel_reg)
            p_mod  = st.text_input("Make & Model", value=f"{st.session_state.sel_make} {st.session_state.sel_model}".strip())
        with c2:
            p_name  = st.text_input("Driver Full Name",   value=st.session_state.ocr_name)
            p_lic   = st.text_input("Driving Licence No", value=st.session_state.ocr_licence)
            p_start = st.date_input("Hire Start Date", datetime.now(), format="DD/MM/YYYY", key="p_form_start")
            p_end   = st.date_input("Hire End Date",   datetime.now(), format="DD/MM/YYYY", key="p_form_end")
        p_addr = st.text_area("Driver Address", value=st.session_state.ocr_address)
        go_p = st.form_submit_button("🖨️ Generate Permission Letter PDF")

    if go_p:
        st.session_state.perm_pdf = generate_permission_letter({
            "date": p_date.strftime("%d/%m/%Y"), "insurance_policy": p_ins,
            "registration": format_uk_reg(p_reg), "make_model": p_mod.upper(),
            "driver_name": p_name.upper(), "address": p_addr.upper(), "license_no": p_lic.upper(),
            "start_date": p_start.strftime("%d/%m/%Y"), "end_date": p_end.strftime("%d/%m/%Y"),
        })
        st.rerun()

    if st.session_state.perm_pdf:
        st.download_button("📥 Download Permission Letter PDF", data=st.session_state.perm_pdf, file_name="Permission_Letter.pdf", mime="application/pdf", key="dl_perm_btn")

with tab2:
    # Trigger active index capture context
    if st.session_state.current_tab != 1:
        set_active_tab(1)

    if st.session_state.contract_pdf:
        st.success(f"🎉 Contract PDF Created Successfully!")
        st.download_button("📥 Download Generated Contract PDF", data=st.session_state.contract_pdf, file_name=f"Contract_{st.session_state.contract_no}.pdf", mime="application/pdf", key="dl_contract_btn")
        st.markdown("---")

    with st.form("contract_form"):
        st.subheader("Hirer Details")
        cc1, cc2 = st.columns(2)
        with cc1:
            c_no   = st.text_input("Contract Number", "1608/DRIVER/REG/2026")
            c_name = st.text_input("Full Name",     value=st.session_state.ocr_name)
            c_addr = st.text_area("Address",        value=st.session_state.ocr_address)
            c_post = st.text_input("Postcode",      value=st.session_state.ocr_postcode)
            c_dob  = st.text_input("Date of Birth (DD/MM/YYYY)", value=normalize_date(st.session_state.ocr_dob))
        with cc2:
            c_date = st.date_input("Contract Date", datetime.now(), format="DD/MM/YYYY", key="c_form_date")
            c_lic  = st.text_input("Licence No",  value=st.session_state.ocr_licence)
            c_exp  = st.text_input("Date of Expiry (DD/MM/YYYY)", value=normalize_date(st.session_state.ocr_expiry))
            c_auth = st.text_input("Issuing Authority", "DVLA")
            c_ph   = st.text_input("Phone")
            c_em   = st.text_input("Email")

        st.markdown("---"); st.subheader("Payment Parameters")
        pp1, pp2, pp3 = st.columns(3)
        with pp1: c_rent = st.text_input("Rent (£/week)", "250/-")
        with pp2: c_rate = st.text_input("Excess (pence/mile)", "20/-")
        with pp3: c_dep  = st.text_input("Deposit (£)", "500/-")

        st.markdown("---"); st.subheader("Hire Period")
        pt1, pt2 = st.columns(2)
        with pt1: c_st  = st.date_input("Hire Start",       datetime.now(), format="DD/MM/YYYY", key="c_form_start")
        with pt2: c_ret = st.date_input("Expected Return",   datetime.now(), format="DD/MM/YYYY", key="c_form_return")

        st.markdown("---"); st.subheader("Vehicle")
        pv1, pv2, pv3 = st.columns(3)
        with pv1: c_mk  = st.text_input("Make",  value=st.session_state.sel_make)
        with pv2: c_rv  = st.text_input("Reg",   value=st.session_state.sel_reg)
        with pv3: c_mv  = st.text_input("Model", value=st.session_state.sel_model)

        go_c = st.form_submit_button("🖨️ Generate 2-Page Contract PDF", type="primary")

    if go_c:
        st.session_state.pending_contract = {
            "contract_no":       c_no.strip().upper() or "N/A",
            "date":              c_date.strftime("%d/%m/%Y"),
            "driver_name":       c_name.strip().upper(),
            "address":           c_addr.strip().upper(),
            "postcode":          c_post.strip().upper(),
            "dob":               c_dob.strip(),
            "license_no":        c_lic.strip().upper(),
            "expiry_date":       c_exp.strip(),
            "issuing_authority": c_auth.strip().upper(),
            "phone":             c_ph.strip(),
            "email":             c_em.strip().upper(),
            "rent":              c_rent.strip(),
            "rate":              c_rate.strip(),
            "deposit":           c_dep.strip(),
            "start_date":        c_st.strftime("%d/%m/%Y"),
            "expected_return":   c_ret.strftime("%d/%m/%Y"),
            "registration":      format_uk_reg(c_rv),
            "car_make":          c_mk.strip().upper(),
            "car_model":         c_mv.strip().upper(),
        }
        st.rerun()
