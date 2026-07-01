import streamlit as st
import os, re, io
import numpy as np
from PIL import Image, ImageFilter, ImageOps, ImageEnhance
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

try:
    import pytesseract
except ImportError:
    pytesseract = None

SRC_DIR = os.path.dirname(os.path.abspath(__file__))

# ─────────────────────────────────────────────
#  FLEET DATABASE
# ─────────────────────────────────────────────
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
#  HELPERS
# ─────────────────────────────────────────────

def format_uk_reg(text):
    clean = re.sub(r"[^A-Za-z0-9]", "", text).upper()
    return f"{clean[:4]} {clean[4:]}".strip() if len(clean) >= 4 else clean

def split_make_model(s):
    parts = s.strip().split(" ", 1)
    return (parts[0].upper(), parts[1].upper()) if len(parts) == 2 else (parts[0].upper(), "")

def clean_name(s):
    s = re.sub(r"[^A-Z '\-]", " ", s.upper())
    return " ".join(w for w in s.split() if len(w) > 1).strip()

def clean_address(s):
    s = s.upper()
    for noise in ["UNITED KINGDOM", "ENGLAND", "SCOTLAND", "WALES"]:
        s = s.replace(noise, "")
    s = re.sub(r"[^A-Z0-9 ,'\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip().strip(",").strip()
    s = re.sub(r",\s*,+", ",", s)
    return s

def extract_postcode(text):
    m = re.search(r"\b([A-Z]{1,2}[0-9][A-Z0-9]?\s*[0-9][A-Z]{2})\b", text.upper())
    return m.group(1).strip() if m else ""

def first_date(fragment):
    m = re.search(r"\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}", fragment)
    return m.group(0) if m else ""

def _grab(blob, start_pats, end_pats):
    for sp in start_pats:
        for ep in end_pats:
            m = re.search(sp + r"\s*(.*?)\s*" + ep, blob, re.DOTALL)
            if m and m.group(1).strip():
                return m.group(1).strip()
    return ""

# ─────────────────────────────────────────────
#  OCR — PIL only, no cv2
# ─────────────────────────────────────────────

def run_ocr(uploaded_file) -> str:
    img = Image.open(uploaded_file).convert("RGB")

    # Upscale small images
    w, h = img.size
    if max(w, h) < 1800:
        scale = 1800 / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    # Greyscale → boost contrast → sharpen → threshold to pure B&W
    img = ImageOps.grayscale(img)
    img = ImageEnhance.Contrast(img).enhance(2.5)
    img = img.filter(ImageFilter.SHARPEN)
    img = img.point(lambda p: 255 if p > 140 else 0)

    return pytesseract.image_to_string(img, config=r"--oem 3 --psm 6")


def parse_licence(raw: str) -> dict:
    blob = " " + re.sub(r"\s+", " ", raw.upper()) + " "

    raw_1 = _grab(blob, [r"1\.", r"[Il]\."], [r"2\."])
    surname = clean_name(raw_1)

    raw_2 = _grab(blob, [r"2\."], [r"3\."])
    forename = clean_name(raw_2)

    raw_3 = _grab(blob, [r"3\."], [r"4[Aa]", r"4\b", r"4\."])
    dob = first_date(raw_3)

    raw_4b = _grab(blob, [r"4[Bb][\.\s]", r"4[Bb]\b"], [r"5\."])
    expiry = first_date(raw_4b)

    raw_5 = _grab(blob, [r"5\."], [r"[67]\.", r"8\."])
    raw_5_clean = re.sub(r"\s+", "", raw_5)
    m5 = re.search(r"[A-Z0-9]{8,20}", raw_5_clean)
    licence = m5.group(0) if m5 else ""

    if not licence:
        bare = re.search(r"[A-Z9]{5}\d{6}[A-Z9]{2}[A-Z0-9]{2,3}", blob.replace(" ", ""))
        if bare:
            licence = bare.group(0)

    raw_8 = _grab(blob, [r"8\."], [r"9\."])
    if not raw_8:
        lines = [l.strip() for l in raw.split("\n") if l.strip()]
        pc_re = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b", re.I)
        for idx, line in enumerate(lines):
            if pc_re.search(line.upper()):
                raw_8 = " ".join(lines[max(0, idx - 3):idx + 1])
                break

    address_full = clean_address(raw_8)
    postcode = extract_postcode(address_full)
    addr_clean = re.sub(re.escape(postcode), "", address_full, flags=re.I).strip().strip(",").strip() if postcode else address_full

    return {
        "surname":  surname,
        "forename": forename,
        "dob":      dob,
        "expiry":   expiry,
        "licence":  licence,
        "address":  addr_clean,
        "postcode": postcode,
    }

# ─────────────────────────────────────────────
#  PDF GENERATORS (BytesIO — no disk writes)
# ─────────────────────────────────────────────

def _src(filename):
    return os.path.join(SRC_DIR, filename)

def generate_permission_letter(data: dict) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter, pageCompression=1)
    w, h = letter

    bg  = _src("image_f4efbe.png")
    sig = _src("signature.png")

    if os.path.exists(bg):
        c.drawImage(bg, 0, 0, width=w, height=h)

    c.setFont("Helvetica", 11)
    c.drawRightString(w - 54, 595, data["date"])
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(w / 2, 550, "PERMISSION LETTER")
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
        c.drawString(54,  y, f"{label} :")
        c.drawString(180, y, val)

    c.drawString(54,  275, "Hire start date. :")
    c.drawString(160, 275, data["start_date"])
    c.drawString(54,  260, "Hire end date    :")
    c.drawString(160, 260, data["end_date"])
    c.drawString(54,  220, "Regards,")

    if os.path.exists(sig):
        c.drawImage(sig, 40, 120, width=280, height=115, mask="auto")

    c.drawString(54, 115, "Muhammad Sohail Qureshi")
    c.drawString(54, 100, "Director (FA-IBI LTD)")
    c.save()
    buf.seek(0)
    return buf.getvalue()


def generate_contract(data: dict) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter, pageCompression=1)
    w, h = letter

    bg1 = _src("Contract Blank.png")
    bg2 = _src("Contarct Blank 2.png")

    if os.path.exists(bg1):
        c.drawImage(bg1, 0, 0, width=w, height=h)

    c.setFont("Helvetica-Bold", 10)
    c.drawString(390, 715, data["contract_no"])
    c.setFont("Helvetica", 10)
    c.drawString(110, 663, data["driver_name"])
    c.drawString(505, 663, data["dob"])
    c.drawString(100, 627, data["address"])
    c.drawString(500, 627, data["postcode"])
    c.drawString(115, 591, data["license_no"])
    c.drawString(340, 591, data["issuing_authority"])
    c.drawString(495, 591, data["expiry_date"])
    c.drawString(75,  555, data["phone"])
    c.drawString(295, 555, data["email"])
    c.drawString(135, 417, data["rent"])
    c.drawString(75,  362, data["rate"])
    c.drawString(115, 319, data["deposit"])
    c.drawString(135, 261, data["start_date"])
    c.drawString(190, 246, data["expected_return"])
    c.drawString(100, 193, data["car_make"])
    c.drawString(440, 193, data["registration"])
    c.drawString(505, 193, data["car_model"])
    c.drawString(85,  108, data["date"])
    c.showPage()

    if os.path.exists(bg2):
        c.drawImage(bg2, 0, 0, width=w, height=h)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(145, 742, data["contract_no"])
    c.drawString(340, 742, data["registration"])
    c.drawString(235,  34, data["date"])
    c.save()
    buf.seek(0)
    return buf.getvalue()

# ─────────────────────────────────────────────
#  STREAMLIT UI
# ─────────────────────────────────────────────

st.set_page_config(page_title="FA-IBI Workspace", layout="centered")

st.markdown("""
<style>
#MainMenu,footer,header,[data-testid="stToolbar"],
.viewerBadge_container__1743q,[class*="viewerBadge"]{
    display:none!important;visibility:hidden!important;opacity:0!important;}
.main .block-container{padding-top:1rem!important;max-width:100%!important;}
.vch-footer{position:fixed;bottom:0;left:0;right:0;width:100vw;
    background:#0e1117;text-align:center;padding:12px 0;font-size:14px;
    color:#888;border-top:1px solid #1f2937;z-index:9999;}
.vch-footer a{color:#FF8C00;font-weight:bold;text-decoration:none;}
@media(max-width:768px){input,select,textarea,.stSelectbox{font-size:16px!important;}}
</style>
""", unsafe_allow_html=True)

# ── Authentication ────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if st.query_params.get("session") == "active":
    st.session_state.authenticated = True
if not st.session_state.authenticated:
    code = st.text_input("System Access", type="password",
                         label_visibility="collapsed", placeholder="Enter key…")
    if code == st.secrets.get("ACCESS_KEY", ""):
        st.session_state.authenticated = True
        st.query_params["session"] = "active"
        st.rerun()
    else:
        st.stop()

# ── Session defaults ──────────────────────────
DEFAULTS = dict(
    ocr_name="", ocr_licence="", ocr_address="", ocr_postcode="",
    ocr_dob="", ocr_expiry="", ocr_raw="",
    last_scan_id="",
    sel_reg="", sel_make="", sel_model="",
    scan_msg="", fleet_msg="",
    perm_pdf=None, contract_pdf=None, contract_no="",
)
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

st.title("FA-IBI Master Document Workspace")

# ─────────────────────────────────────────────
#  SHARED AUTOMATION PANEL
# ─────────────────────────────────────────────

def render_automation(ctx: str):
    st.markdown("#### 🎛️ Data Automation")

    if st.session_state.scan_msg:
        st.success(st.session_state.scan_msg)
    if st.session_state.fleet_msg:
        st.info(st.session_state.fleet_msg)

    col_scan, col_fleet = st.columns(2)

    with col_scan:
        uploaded = st.file_uploader(
            "📷 Driver's Licence Scanner",
            type=["jpg", "png", "jpeg"],
            key=f"uploader_{ctx}",
        )

        if uploaded is not None and pytesseract is not None:
            file_id = f"{uploaded.name}_{uploaded.size}"
            if st.session_state.last_scan_id != file_id:
                with st.spinner("Scanning licence…"):
                    try:
                        raw = run_ocr(uploaded)
                        st.session_state.ocr_raw = raw
                        parsed = parse_licence(raw)
                        st.session_state.ocr_name     = f"{parsed['forename']} {parsed['surname']}".strip()
                        st.session_state.ocr_licence  = parsed["licence"]
                        st.session_state.ocr_address  = parsed["address"]
                        st.session_state.ocr_postcode = parsed["postcode"]
                        st.session_state.ocr_dob      = parsed["dob"]
                        st.session_state.ocr_expiry   = parsed["expiry"]
                        st.session_state.scan_msg     = "✅ Licence scanned — fields populated!"
                        st.session_state.last_scan_id = file_id
                    except Exception as e:
                        st.session_state.scan_msg     = f"⚠️ Scan error: {e}"
                        st.session_state.last_scan_id = file_id
                st.rerun()

        if st.session_state.ocr_raw:
            with st.expander("🔍 Raw OCR (debug)"):
                st.text(st.session_state.ocr_raw)

    with col_fleet:
        options = ["-- Manual Entry --"] + [
            f"{v['reg']} ({v['model']})" for v in FLEET_VEHICLES
        ]
        current = "-- Manual Entry --"
        if st.session_state.sel_reg:
            hit = [o for o in options if o.startswith(st.session_state.sel_reg)]
            if hit:
                current = hit[0]

        chosen = st.selectbox(
            "🚗 Select Vehicle", options,
            index=options.index(current),
            key=f"fleet_{ctx}",
        )

        if chosen != "-- Manual Entry --":
            reg_key = chosen.split(" (")[0]
            if st.session_state.sel_reg != reg_key:
                car = next((v for v in FLEET_VEHICLES if v["reg"] == reg_key), None)
                if car:
                    mk, mo = split_make_model(car["model"])
                    st.session_state.sel_reg   = car["reg"]
                    st.session_state.sel_make  = mk
                    st.session_state.sel_model = mo
                    st.session_state.fleet_msg = f"✅ {reg_key} loaded!"
                    st.rerun()
        else:
            if st.session_state.sel_reg:
                st.session_state.sel_reg = st.session_state.sel_make = st.session_state.sel_model = ""
                st.session_state.fleet_msg = ""
                st.rerun()

# ─────────────────────────────────────────────
#  TABS
# ─────────────────────────────────────────────
tab1, tab2 = st.tabs(["📝 Permission Letter", "📜 Contract Generator"])

# ══════════════════════════════════
#  TAB 1 — PERMISSION LETTER
# ══════════════════════════════════
with tab1:
    render_automation("tab1")
    st.markdown("---")

    with st.form("perm_form"):
        c1, c2 = st.columns(2)
        with c1:
            p_date      = st.date_input("Document Date", datetime.now(), format="DD/MM/YYYY")
            p_insurance = st.text_input("Insurance Policy No", "HAVFL-000211")
            p_reg       = st.text_input("Vehicle Registration", value=st.session_state.sel_reg)
            p_model     = st.text_input("Make & Model",
                            value=f"{st.session_state.sel_make} {st.session_state.sel_model}".strip())
        with c2:
            p_name    = st.text_input("Driver Full Name",   value=st.session_state.ocr_name)
            p_licence = st.text_input("Driving Licence No", value=st.session_state.ocr_licence)
            p_start   = st.date_input("Hire Start Date", datetime.now(), format="DD/MM/YYYY")
            p_end     = st.date_input("Hire End Date",   datetime.now(), format="DD/MM/YYYY")

        p_address = st.text_area("Driver Address", value=st.session_state.ocr_address)
        go_p = st.form_submit_button("🖨️ Generate Permission Letter PDF")

    if go_p:
        try:
            st.session_state.perm_pdf = generate_permission_letter({
                "date":             p_date.strftime("%d/%m/%Y"),
                "insurance_policy": p_insurance,
                "registration":     format_uk_reg(p_reg),
                "make_model":       p_model.upper(),
                "driver_name":      p_name.upper(),
                "address":          p_address.upper(),
                "license_no":       p_licence.upper(),
                "start_date":       p_start.strftime("%d/%m/%Y"),
                "end_date":         p_end.strftime("%d/%m/%Y"),
            })
        except Exception as e:
            st.error(f"PDF error: {e}")

    if st.session_state.perm_pdf:
        st.download_button(
            "📥 Download Permission Letter PDF",
            data=st.session_state.perm_pdf,
            file_name="Permission_Letter.pdf",
            mime="application/pdf",
            key="dl_perm",
        )

# ══════════════════════════════════
#  TAB 2 — CONTRACT
# ══════════════════════════════════
with tab2:
    render_automation("tab2")
    st.markdown("---")

    with st.form("contract_form"):
        st.subheader("Hirer Details")
        cc1, cc2 = st.columns(2)
        with cc1:
            c_no      = st.text_input("Contract Number", "1608/DRIVER/REG/2026")
            c_name    = st.text_input("Full Name",        value=st.session_state.ocr_name)
            c_address = st.text_area("Address",           value=st.session_state.ocr_address)
            c_post    = st.text_input("Postcode",         value=st.session_state.ocr_postcode)
            c_dob     = st.text_input("Date of Birth",    value=st.session_state.ocr_dob)
        with cc2:
            c_date    = st.date_input("Contract Date", datetime.now(), format="DD/MM/YYYY")
            c_lic     = st.text_input("Licence No",   value=st.session_state.ocr_licence)
            c_exp     = st.text_input("Expiry Date",  value=st.session_state.ocr_expiry)
            c_auth    = st.text_input("Issuing Authority", "DVLA")
            c_phone   = st.text_input("Phone")
            c_email   = st.text_input("Email")

        st.markdown("---")
        st.subheader("Payment Parameters")
        pp1, pp2, pp3 = st.columns(3)
        with pp1: c_rent    = st.text_input("Rent (£/week)", "250/-")
        with pp2: c_rate    = st.text_input("Excess Charge", "20/-")
        with pp3: c_deposit = st.text_input("Deposit (£)",   "500/-")

        st.markdown("---")
        st.subheader("Hire Period")
        pt1, pt2 = st.columns(2)
        with pt1: c_start  = st.date_input("Hire Start",       datetime.now(), format="DD/MM/YYYY")
        with pt2: c_return = st.date_input("Expected Return",   datetime.now(), format="DD/MM/YYYY")

        st.markdown("---")
        st.subheader("Vehicle")
        pv1, pv2, pv3 = st.columns(3)
        with pv1: c_make  = st.text_input("Make",  value=st.session_state.sel_make)
        with pv2: c_reg_v = st.text_input("Reg",   value=st.session_state.sel_reg)
        with pv3: c_mod_v = st.text_input("Model", value=st.session_state.sel_model)

        go_c = st.form_submit_button("🖨️ Generate 2-Page Contract PDF")

    if go_c:
        try:
            cpay = {
                "contract_no":       c_no.upper(),
                "date":              c_date.strftime("%d/%m/%Y"),
                "driver_name":       c_name.upper(),
                "address":           c_address.upper(),
                "postcode":          c_post.upper(),
                "dob":               c_dob,
                "license_no":        c_lic.upper(),
                "expiry_date":       c_exp,
                "issuing_authority": c_auth.upper(),
                "phone":             c_phone,
                "email":             c_email.upper(),
                "rent":              c_rent,
                "rate":              c_rate,
                "deposit":           c_deposit,
                "start_date":        c_start.strftime("%d/%m/%Y"),
                "expected_return":   c_return.strftime("%d/%m/%Y"),
                "registration":      format_uk_reg(c_reg_v),
                "car_make":          c_make.upper(),
                "car_model":         c_mod_v.upper(),
            }
            st.session_state.contract_pdf = generate_contract(cpay)
            st.session_state.contract_no  = cpay["contract_no"]
        except Exception as e:
            st.error(f"PDF error: {e}")

    if st.session_state.contract_pdf:
        st.download_button(
            "📥 Download Contract PDF",
            data=st.session_state.contract_pdf,
            file_name=f"FA_IBI_Contract_{st.session_state.contract_no}.pdf",
            mime="application/pdf",
            key="dl_contract",
        )

st.markdown('<div class="vch-footer">Powered By '
            '<a href="https://virtualcarhire.pages.dev/" target="_blank">Virtual Car Hire</a>'
            '</div>', unsafe_allow_html=True)
