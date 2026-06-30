import streamlit as st
import os
import re
import cv2
import tempfile
import numpy as np
from PIL import Image
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

try:
    import pytesseract
except ImportError:
    pytesseract = None

# --- Full Fleet Database ---
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
    if len(clean) >= 4:
        return f"{clean[:4]} {clean[4:]}".strip()
    return clean


def split_make_model(full_string):
    parts = full_string.strip().split(" ", 1)
    if len(parts) == 2:
        return parts[0].upper(), parts[1].upper()
    return parts[0].upper(), ""


def clean_name(s):
    """Keep only letters, spaces, hyphens, apostrophes; drop single-char noise."""
    s = re.sub(r"[^A-Z '\-]", " ", s.upper())
    return " ".join(w for w in s.split() if len(w) > 1).strip()


def clean_address(s):
    """Strip noise, remove UNITED KINGDOM, collapse whitespace."""
    s = s.upper()
    s = re.sub(r"\bUNITED\s+KINGDOM\b", "", s)
    s = re.sub(r"[^A-Z0-9 ,'\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip().strip(",").strip()
    s = re.sub(r",\s*,+", ",", s)
    return s


def extract_postcode(text):
    m = re.search(r"\b([A-Z]{1,2}[0-9][A-Z0-9]?\s*[0-9][A-Z]{2})\b", text.upper())
    return m.group(1).strip() if m else ""


def between(text, start_marker, end_marker):
    """Return text between two regex markers in the collapsed OCR blob."""
    pat = re.compile(
        re.escape(start_marker) + r"\s*(.*?)\s*" + re.escape(end_marker),
        re.DOTALL | re.IGNORECASE,
    )
    m = pat.search(text)
    return m.group(1).strip() if m else ""


def first_date(fragment):
    """Pull the first date-like token from a fragment (dd.mm.yyyy or dd/mm/yyyy)."""
    m = re.search(r"\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}", fragment)
    return m.group(0) if m else fragment.strip()


def extract_licence_no(fragment):
    """Pull the first plausible UK licence-number token."""
    fragment = re.sub(r"\s+", "", fragment.upper())
    m = re.search(r"[A-Z0-9]{8,20}", fragment)
    return m.group(0) if m else ""


# ─────────────────────────────────────────────
#  CORE OCR EXTRACTOR  (blob-based, not line-by-line)
#  Fields: 1 surname · 2 forename · 3 DOB · 4b expiry · 5 licence · 8 address
# ─────────────────────────────────────────────

def run_ocr(uploaded_file):
    """Run Tesseract on the uploaded image and return raw string."""
    img = Image.open(uploaded_file).convert("RGB")
    img_np = np.array(img)

    h, w = img_np.shape[:2]
    # Upscale small images so characters have enough pixels
    if max(h, w) < 1800:
        scale = 1800 / max(h, w)
        img_np = cv2.resize(
            img_np, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC
        )

    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    # Otsu works well on printed card text; no blur (blur smears thin strokes)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return pytesseract.image_to_string(thresh, config=r"--oem 3 --psm 6")


def parse_licence(raw: str) -> dict:
    """
    Extract fields by finding the text *between* field markers in the
    collapsed OCR blob.  Much more robust than line-by-line parsing because
    OCR frequently breaks lines in unexpected places.
    """
    # Collapse newlines → spaces so every field sits on one searchable line
    blob = " " + re.sub(r"\s+", " ", raw.upper()) + " "

    # ── surnames (field 1): text between "1." and "2."
    raw_1 = between(blob, "1.", "2.")
    surname = clean_name(raw_1)

    # ── forenames (field 2): text between "2." and "3."
    raw_2 = between(blob, "2.", "3.")
    forename = clean_name(raw_2)

    # ── DOB (field 3): text between "3." and "4" — grab first date token
    raw_3 = between(blob, "3.", "4")
    dob = first_date(raw_3)

    # ── expiry (field 4b): text between "4B." and "4C" or "5." — first date token
    raw_4b = between(blob, "4B.", "5.")
    if not raw_4b:
        raw_4b = between(blob, "4B", "5.")
    expiry = first_date(raw_4b)

    # ── licence number (field 5): text between "5." and "6." or "7." or "8."
    raw_5 = between(blob, "5.", "6.")
    if not raw_5:
        raw_5 = between(blob, "5.", "7.")
    if not raw_5:
        raw_5 = between(blob, "5.", "8.")
    licence = extract_licence_no(raw_5)

    # Fallback bare-pattern scan if field 5 marker was garbled
    if not licence:
        bare = re.search(r"\b[A-Z9]{5}\d{6}[A-Z9]{2}[A-Z0-9]{2,3}\b", blob.replace(" ", ""))
        if bare:
            licence = bare.group(0)

    # ── address (field 8): text between "8." and "9."
    raw_8 = between(blob, "8.", "9.")
    if not raw_8:
        # Fallback: find a UK postcode and grab surrounding lines
        lines = [l.strip() for l in raw.split("\n") if l.strip()]
        postcode_re = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b", re.I)
        for idx, line in enumerate(lines):
            if postcode_re.search(line.upper()):
                chunk = lines[max(0, idx - 3) : idx + 1]
                raw_8 = " ".join(chunk)
                break

    address_full = clean_address(raw_8)

    # ── split postcode out of address
    postcode = extract_postcode(address_full)
    if postcode:
        address_clean = re.sub(re.escape(postcode), "", address_full, flags=re.I)
        address_clean = address_clean.strip().strip(",").strip()
    else:
        address_clean = address_full

    return {
        "surname": surname,
        "forename": forename,
        "dob": dob,
        "expiry": expiry,
        "licence": licence,
        "address": address_clean,
        "postcode": postcode,
    }


# ─────────────────────────────────────────────
#  PDF GENERATORS
# ─────────────────────────────────────────────

def pdf_path(filename):
    """Return a writable path in /tmp (required on Streamlit Cloud)."""
    return os.path.join(tempfile.gettempdir(), filename)


def generate_permission_letter(data):
    out = pdf_path("Permission_Letter.pdf")
    c = canvas.Canvas(out, pagesize=letter, pageCompression=1)
    width, height = letter

    bg = os.path.join("src", "image_f4efbe.png")
    sig = os.path.join("src", "signature.png")

    if os.path.exists(bg):
        c.drawImage(bg, 0, 0, width=width, height=height)

    c.setFont("Helvetica", 11)
    c.drawRightString(width - 54, 595, data["date"])
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width / 2, 550, "PERMISSION LETTER")
    c.setFont("Helvetica", 11)
    c.drawString(54, 520, "To Whom It May Concern,")
    c.drawString(54, 490, "We confirm that the below vehicle can be used for the carriage of passengers for hire and reward by prior")
    c.drawString(54, 475, f"appointments (private hire) as specified on insurance policy: {data['insurance_policy']}")
    c.drawString(54, 460, "We authorise and give permission to the following individual to use the vehicle for all private hire bookings")
    c.drawString(54, 445, "from UBER, BOLT, OLA, FREE NOW app, WHEELY and other private hire operators.")

    fields = [
        ("Vehicle Registration", data["registration"]),
        ("Make and Model",       data["make_model"]),
        ("Driver Name",          data["driver_name"]),
        ("Address",              data["address"]),
        ("Driving Licence No",   data["license_no"]),
    ]
    for i, (label, val) in enumerate(fields):
        y = 405 - (i * 22)
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
    return out


def generate_contract(data):
    out = pdf_path("FA_IBI_Contract.pdf")
    c = canvas.Canvas(out, pagesize=letter, pageCompression=1)
    width, height = letter

    bg1 = os.path.join("src", "Contract Blank.png")
    bg2 = os.path.join("src", "Contarct Blank 2.png")

    if os.path.exists(bg1):
        c.drawImage(bg1, 0, 0, width=width, height=height)

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
        c.drawImage(bg2, 0, 0, width=width, height=height)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(145, 742, data["contract_no"])
    c.drawString(340, 742, data["registration"])
    c.drawString(235,  34, data["date"])
    c.save()
    return out


# ─────────────────────────────────────────────
#  STREAMLIT UI
# ─────────────────────────────────────────────

st.set_page_config(page_title="FA-IBI Workspace", layout="centered")

st.markdown("""
<style>
#MainMenu, footer, header, [data-testid="stToolbar"],
.viewerBadge_container__1743q, [class*="viewerBadge"] {
    display: none !important; visibility: hidden !important; opacity: 0 !important;
}
.main .block-container {
    padding-top: 1rem !important; padding-bottom: 5rem !important; max-width: 100% !important;
}
.vch-branding-cover-fixed {
    position: fixed !important; bottom: 0 !important; right: 0 !important; left: 0 !important;
    width: 100vw !important; background-color: #0e1117 !important;
    text-align: center !important; padding: 14px 0 !important;
    font-size: 14px !important; color: #888888 !important;
    border-top: 1px solid #1f2937 !important; z-index: 2147483647 !important;
}
.vch-branding-cover-fixed a { color: #FF8C00 !important; font-weight: bold !important; text-decoration: none !important; }
@media screen and (max-width: 768px) {
    input, select, textarea, .stSelectbox, div[data-baseweb="select"] { font-size: 16px !important; }
}
</style>
""", unsafe_allow_html=True)

# ── Auth ──────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if st.query_params.get("session") == "active":
    st.session_state["authenticated"] = True

if not st.session_state["authenticated"]:
    code = st.text_input("System Access", type="password",
                         label_visibility="collapsed", placeholder="Enter key...")
    if code == st.secrets.get("ACCESS_KEY", ""):
        st.session_state["authenticated"] = True
        st.query_params["session"] = "active"
        st.rerun()
    else:
        st.stop()

# ── Session defaults ──────────────────────────
DEFAULTS = dict(
    ocr_name="", ocr_licence="", ocr_address="", ocr_postcode="",
    ocr_dob="", ocr_expiry="", ocr_raw="",
    sel_reg="", sel_make="", sel_model="",
    scan_msg="", fleet_msg="",
    scan_ctx="", fleet_ctx="",
    contract_payload=None,
)
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

st.title("FA-IBI Master Document Workspace")


# ── Shared automation panel (reused in both tabs) ────────────────────────────
def render_scanner_and_fleet(ctx):
    st.markdown("#### 🎛️ Data Automation")

    if st.session_state.scan_msg and st.session_state.scan_ctx == ctx:
        st.success(st.session_state.scan_msg)
    if st.session_state.fleet_msg and st.session_state.fleet_ctx == ctx:
        st.info(st.session_state.fleet_msg)

    col_scan, col_fleet = st.columns(2)

    # ── Licence scanner ─────────────────────────────────────
    with col_scan:
        uploaded = st.file_uploader(
            "📷 Driver's Licence Scanner", type=["jpg", "png", "jpeg"],
            key=f"upload_{ctx}"
        )
        if uploaded and pytesseract:
            with st.spinner("Scanning…"):
                raw = run_ocr(uploaded)
                st.session_state.ocr_raw = raw
                parsed = parse_licence(raw)

                st.session_state.ocr_name     = f"{parsed['forename']} {parsed['surname']}".strip()
                st.session_state.ocr_licence  = parsed["licence"]
                st.session_state.ocr_address  = parsed["address"]
                st.session_state.ocr_postcode = parsed["postcode"]
                st.session_state.ocr_dob      = parsed["dob"]
                st.session_state.ocr_expiry   = parsed["expiry"]
                st.session_state.scan_msg     = "✅ Licence scanned and fields mapped!"
                st.session_state.scan_ctx     = ctx
            st.rerun()

        if st.session_state.ocr_raw:
            with st.expander("🔍 Raw OCR (debug)"):
                st.text(st.session_state.ocr_raw)

    # ── Fleet selector ──────────────────────────────────────
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
            key=f"fleet_{ctx}"
        )

        if chosen != "-- Manual Entry --":
            reg_key = chosen.split(" (")[0]
            if st.session_state.sel_reg != reg_key:
                car = next((v for v in FLEET_VEHICLES if v["reg"] == reg_key), None)
                if car:
                    st.session_state.sel_reg   = car["reg"]
                    mk, mo = split_make_model(car["model"])
                    st.session_state.sel_make  = mk
                    st.session_state.sel_model = mo
                    st.session_state.fleet_msg = f"✅ {reg_key} loaded from database!"
                    st.session_state.fleet_ctx = ctx
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

# ══════════════════════════════════════════════
#  TAB 1 — PERMISSION LETTER
# ══════════════════════════════════════════════
with tab1:
    render_scanner_and_fleet("tab1")
    st.markdown("---")

    with st.form("perm_letter_form"):
        c1, c2 = st.columns(2)
        with c1:
            p_date      = st.date_input("Document Date", datetime.now(), format="DD/MM/YYYY")
            p_insurance = st.text_input("Insurance Policy No", "HAVFL-000211")
            p_reg       = st.text_input("Vehicle Registration", value=st.session_state.sel_reg)
            p_model     = st.text_input("Make & Model",
                                        value=f"{st.session_state.sel_make} {st.session_state.sel_model}".strip())
        with c2:
            p_name    = st.text_input("Driver Full Name",    value=st.session_state.ocr_name)
            p_licence = st.text_input("Driving Licence No",  value=st.session_state.ocr_licence)
            p_start   = st.date_input("Hire Start Date", datetime.now(), format="DD/MM/YYYY")
            p_end     = st.date_input("Hire End Date",   datetime.now(), format="DD/MM/YYYY")

        p_address = st.text_area("Driver Address", value=st.session_state.ocr_address)
        go = st.form_submit_button("Generate Permission Letter PDF")

    if go:
        payload = {
            "date":             p_date.strftime("%d/%m/%Y"),
            "insurance_policy": p_insurance,
            "registration":     format_uk_reg(p_reg),
            "make_model":       p_model.upper(),
            "driver_name":      p_name.upper(),
            "address":          p_address.upper(),
            "license_no":       p_licence.upper(),
            "start_date":       p_start.strftime("%d/%m/%Y"),
            "end_date":         p_end.strftime("%d/%m/%Y"),
        }
        out_file = generate_permission_letter(payload)
        with open(out_file, "rb") as f:
            st.download_button(
                "📥 Download Permission Letter PDF",
                data=f,
                file_name="Permission_Letter.pdf",
                mime="application/pdf",
            )

# ══════════════════════════════════════════════
#  TAB 2 — CONTRACT
# ══════════════════════════════════════════════
with tab2:
    render_scanner_and_fleet("tab2")
    st.markdown("---")

    with st.form("contract_form"):
        st.subheader("Hirer Details")
        cc1, cc2 = st.columns(2)
        with cc1:
            c_contract_no = st.text_input("Contract Number", "1608/DRIVER/REG/2026")
            c_name        = st.text_input("Full Name",        value=st.session_state.ocr_name)
            c_address     = st.text_area("Address",           value=st.session_state.ocr_address)
            c_postcode    = st.text_input("Postcode",         value=st.session_state.ocr_postcode)
            c_dob         = st.text_input("Date of Birth",    value=st.session_state.ocr_dob)
        with cc2:
            c_date      = st.date_input("Contract Date", datetime.now(), format="DD/MM/YYYY")
            c_licence   = st.text_input("Licence No",     value=st.session_state.ocr_licence)
            c_expiry    = st.text_input("Expiry Date",    value=st.session_state.ocr_expiry)
            c_authority = st.text_input("Issuing Authority", "DVLA")
            c_phone     = st.text_input("Phone")
            c_email     = st.text_input("Email")

        st.markdown("---")
        st.subheader("Payment Parameters")
        cp1, cp2, cp3 = st.columns(3)
        with cp1: c_rent    = st.text_input("Rent (£/week)",    "250/-")
        with cp2: c_rate    = st.text_input("Excess Charge",    "20/-")
        with cp3: c_deposit = st.text_input("Deposit (£)",      "500/-")

        st.markdown("---")
        st.subheader("Hire Period")
        ct1, ct2 = st.columns(2)
        with ct1: c_start  = st.date_input("Hire Start",  datetime.now(), format="DD/MM/YYYY")
        with ct2: c_return = st.date_input("Expected Return", datetime.now(), format="DD/MM/YYYY")

        st.markdown("---")
        st.subheader("Vehicle")
        cv1, cv2, cv3 = st.columns(3)
        with cv1: c_make     = st.text_input("Make",  value=st.session_state.sel_make)
        with cv2: c_reg_v    = st.text_input("Reg",   value=st.session_state.sel_reg)
        with cv3: c_model_v  = st.text_input("Model", value=st.session_state.sel_model)

        go_c = st.form_submit_button("Generate 2-Page Contract PDF")

    if go_c:
        cpayload = {
            "contract_no":       c_contract_no.upper(),
            "date":              c_date.strftime("%d/%m/%Y"),
            "driver_name":       c_name.upper(),
            "address":           c_address.upper(),
            "postcode":          c_postcode.upper(),
            "dob":               c_dob,
            "license_no":        c_licence.upper(),
            "expiry_date":       c_expiry,
            "issuing_authority": c_authority.upper(),
            "phone":             c_phone,
            "email":             c_email.upper(),
            "rent":              c_rent,
            "rate":              c_rate,
            "deposit":           c_deposit,
            "start_date":        c_start.strftime("%d/%m/%Y"),
            "expected_return":   c_return.strftime("%d/%m/%Y"),
            "registration":      format_uk_reg(c_reg_v),
            "car_make":          c_make.upper(),
            "car_model":         c_model_v.upper(),
        }
        out_file = generate_contract(cpayload)
        with open(out_file, "rb") as f:
            st.download_button(
                "📥 Download Contract PDF",
                data=f,
                file_name=f"FA_IBI_Contract_{cpayload['contract_no']}.pdf",
                mime="application/pdf",
            )

# ── Footer ────────────────────────────────────
st.markdown("""
<div class="vch-branding-cover-fixed">
  Powered By <a href="https://virtualcarhire.pages.dev/" target="_blank">Virtual Car Hire</a>
</div>
""", unsafe_allow_html=True)
