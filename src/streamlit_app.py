import streamlit as st
import os, re, io
import numpy as np
from PIL import Image, ImageOps, ImageEnhance
from datetime import datetime, date, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import extra_streamlit_components as stx
except ImportError:
    stx = None

SRC_DIR = os.path.dirname(os.path.abspath(__file__))

def _find_img(base_name):
    for ext in [".jpg", ".png", ".jpeg", ".JPG", ".PNG"]:
        p = os.path.join(SRC_DIR, base_name + ext)
        if os.path.exists(p): return p
    return None

fav_path = _find_img("Screenshot 2026-06-09 230035") or "🚗"

# ─────────────────────────────────────────────
#  STREAMLIT CONFIGURATION & BRAND HIDING
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="FA-IBI Workspace",
    page_icon=fav_path,
    layout="centered"
)

st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
[data-testid="stToolbar"] {visibility: hidden !important;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  REAL COOKIE-BASED AUTH (no URL params, no full-page reload hacks)
#
#  Requires: pip install extra-streamlit-components
#  This stores an actual HTTP cookie in the browser via a proper
#  Streamlit component, instead of poking window.parent.location
#  and localStorage from an injected <script>. That old approach
#  had to force a full page navigation (?auth_token=verified) just
#  to get the value back into Python, which is why it felt flaky.
#  A CookieManager component gives Python the cookie value directly
#  on rerun, so nothing ever touches the URL.
# ─────────────────────────────────────────────
AUTH_COOKIE_NAME = "fa_ibi_auth"
AUTH_COOKIE_DAYS = 30

if stx is not None:
    # NOTE: CookieManager() creates a widget the moment it's constructed,
    # so it must NOT be wrapped in @st.cache_data / @st.cache_resource —
    # doing that triggers Streamlit's CachedWidgetWarning and can produce
    # stale cookie reads. Just instantiate it plainly each run; the
    # component itself is cheap and Streamlit reuses it by key.
    cookie_manager = stx.CookieManager(key="fa_ibi_cookie_manager")
else:
    cookie_manager = None
    st.warning(
        "⚠️ `extra-streamlit-components` isn't installed, so login can't persist "
        "across refreshes. Add `extra-streamlit-components` to requirements.txt "
        "and redeploy to fix this.",
        icon="⚠️",
    )

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    if cookie_manager is not None:
        cookies = cookie_manager.get_all(key="init_cookie_read") or {}
        st.session_state.authenticated = cookies.get(AUTH_COOKIE_NAME) == "true"

# ── Fleet data, parsing engines, PDF generators are unchanged below ──

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
#  PARSING AND GENERATION ENGINES
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
    s = re.sub(r"\b\d{1,2}\s+\d{1,2}\s+\d{2,4}\b", " ", s)
    s = re.sub(r"\b\d{5,}\b", " ", s)
    s = re.sub(r"\b[1-9][ABCDE58]?\.?\s*", " ", s)
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
#  OCR ENGINE — rebuilt for accuracy
#
#  What was wrong before:
#   • Contrast was boosted 2.5x then sharpened then globally thresholded
#     (Otsu). On a photographed plastic ID card with any glare, shadow,
#     or uneven lighting, a *single* global threshold either blows out
#     half the card to white or crushes it to black — Tesseract sees
#     garbage either way.
#   • Sharpening BEFORE thresholding amplifies noise/JPEG artefacts,
#     which then get baked into the black/white split.
#   • Only one PSM (page segmentation mode) was tried, so a layout
#     Tesseract wasn't expecting produced no fallback.
#   • No rotation/orientation correction for photos taken at an angle.
#
#  Fix: denoise → adaptive (local) threshold instead of global → try
#  several PSM modes and keep whichever gives Tesseract the highest
#  confidence score → auto-correct orientation first.
# ─────────────────────────────────────────────
def _deskew_and_orient(img: Image.Image) -> Image.Image:
    if pytesseract is None:
        return img
    try:
        osd = pytesseract.image_to_osd(img)
        m = re.search(r"Rotate:\s*(\d+)", osd)
        if m:
            angle = int(m.group(1))
            if angle in (90, 180, 270):
                img = img.rotate(-angle, expand=True)
    except Exception:
        pass  # OSD fails on very low-text images — just skip it
    return img

def _best_ocr_text(bw_img: Image.Image) -> str:
    configs = [r"--oem 3 --psm 6", r"--oem 3 --psm 4", r"--oem 3 --psm 11", r"--oem 3 --psm 3"]
    best_text, best_conf = "", -1.0
    for cfg in configs:
        try:
            data = pytesseract.image_to_data(bw_img, config=cfg, output_type=pytesseract.Output.DICT)
            confs = [float(c) for c in data.get("conf", []) if str(c) not in ("-1", "")]
            avg_conf = sum(confs) / len(confs) if confs else 0.0
            text = " ".join(w for w in data.get("text", []) if w.strip())
            if text.strip() and avg_conf > best_conf:
                best_conf = avg_conf
                best_text = pytesseract.image_to_string(bw_img, config=cfg)
        except Exception:
            continue
    if not best_text:
        best_text = pytesseract.image_to_string(bw_img, config=r"--oem 3 --psm 6")
    return best_text

def run_ocr(uploaded_file) -> str:
    img = Image.open(uploaded_file).convert("RGB")
    img = _deskew_and_orient(img)

    w, h = img.size
    target = 2200
    if max(w, h) < target:
        scale = target / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    gray = ImageOps.grayscale(img)

    if cv2 is not None:
        arr = np.array(gray)
        arr = cv2.fastNlMeansDenoising(arr, h=10)
        # Adaptive threshold reacts to *local* lighting, unlike the old
        # single global Otsu cut — this is what actually fixes glare/
        # shadow issues on photographed cards.
        bw_arr = cv2.adaptiveThreshold(
            arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 35, 11
        )
        bw = Image.fromarray(bw_arr)
    else:
        # Fallback if opencv isn't installed — milder than before
        gray = ImageEnhance.Contrast(gray).enhance(1.6)
        bw = gray.point(lambda p: 255 if p > 150 else 0)

    return _best_ocr_text(bw)

def parse_licence(raw: str) -> dict:
    blob = " " + re.sub(r"\s+", " ", raw.upper()) + " "
    surname = clean_name(_grab(blob, [r"1\."], [r"2\."])) or (re.search(r"1\.\s*([A-Z\-]+)", blob).group(1).strip() if re.search(r"1\.\s*([A-Z\-]+)", blob) else "")
    forename = clean_name(_grab(blob, [r"2\."], [r"3\."])) or (re.search(r"2\.\s*([A-Z\-]+)", blob).group(1).strip() if re.search(r"2\.\s*([A-Z\-]+)", blob) else "")
    dob = first_date(_grab(blob, [r"3\."], [r"4[Aa]\b"])) or (normalize_date(re.search(r"3\.\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})", blob).group(1)) if re.search(r"3\.\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})", blob) else "")
    expiry = first_date(_grab(blob, [r"4[Bb]\.?"], [r"4[Cc]", r"5\."])) or (normalize_date(re.search(r"4[Bb]\.?\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})", blob).group(1)) if re.search(r"4[Bb]\.?\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})", blob) else "")

    licence = ""
    clean_strip = re.sub(r"\s", "", blob)
    # Primary: look for the number right after the "5." field marker
    lic_match = re.search(r"5\.?([A-Z9]{5}\d{6}[A-Z9]{2}[A-Z0-9]{3,5})", clean_strip)
    if not lic_match:
        # Fallback: the UK licence number format itself is distinctive
        # enough to find anywhere in the text, even if OCR mangled the
        # "5." field marker in front of it.
        lic_match = re.search(r"([A-Z9]{5}\d{6}[A-Z9]{2}[A-Z0-9]{3,5})", clean_strip)
    if lic_match: licence = lic_match.group(1)[:16]

    raw_8 = _grab(blob, [r"8\."], [r"9\."]) or (re.search(r"8\.\s*(.*?)(?=\s*9\.)", blob, re.DOTALL).group(1).strip() if re.search(r"8\.\s*(.*?)(?=\s*9\.)", blob, re.DOTALL) else blob)
    postcode = extract_postcode(raw_8)
    addr_clean = strip_address_noise(raw_8.replace(licence, ""))
    if postcode: addr_clean = re.sub(re.escape(postcode), "", addr_clean, flags=re.I)
    addr_clean = re.sub(r"^[0-9A-Z]{1,2}\b\.?\s*", "", addr_clean.strip()).strip(", ").strip()

    return {"surname": surname, "forename": forename, "dob": dob, "expiry": expiry, "licence": licence, "address": addr_clean, "postcode": postcode}

def generate_permission_letter(data: dict) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter, pageCompression=1)
    pw, ph = letter
    bg = _find_img("image_f4efbe"); sig = _find_img("signature")
    if bg: c.drawImage(bg, 0, 0, width=pw, height=ph)
    c.setFont("Helvetica", 11)
    c.drawRightString(pw - 54, 595, data["date"])
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(pw / 2, 550, "PERMISSION LETTER")
    c.setFont("Helvetica", 11)
    c.drawString(54, 520, "To Whom It May Concern,")
    c.drawString(54, 490, f"We confirm that the below vehicle can be used for the carriage of passengers for hire and reward by prior appointments (private hire) as specified on insurance policy: {data['insurance_policy']}")
    for i, (label, val) in enumerate([("Vehicle Registration", data["registration"]), ("Make and Model", data["make_model"]), ("Driver Name", data["driver_name"]), ("Address", data["address"]), ("Driving Licence No", data["license_no"])]):
        c.drawString(54, 405 - i * 22, f"{label} :"); c.drawString(180, 405 - i * 22, val)
    c.drawString(54, 275, "Hire start date. :"); c.drawString(160, 275, data["start_date"])
    c.drawString(54, 260, "Hire end date    :"); c.drawString(160, 260, data["end_date"])
    if sig: c.drawImage(sig, 40, 120, width=280, height=115, mask="auto")
    c.save(); buf.seek(0); return buf.getvalue()

# ─────────────────────────────────────────────
#  CONTRACT PDF — coordinates centralised & calibratable
#
#  The old code had hardcoded (x, y) guesses baked directly into
#  drawString calls, which is exactly why fields ended up overlapping
#  your printed labels ("CONTRACT NUMBER:", "Deposit Paid", etc.) —
#  nobody could see where they landed without generating a full PDF
#  each time.
#
#  Now: every field's position lives in one dict below, and there's a
#  "Calibration Grid" button in the Contract tab that overlays a
#  ruled 20pt grid on YOUR actual template images. Open that PDF,
#  read off the x/y where each label's blank line sits, and update
#  the numbers below. Takes a few minutes and you'll never have to
#  guess again.
#
#  Units: PDF points, origin (0,0) at BOTTOM-LEFT of the page,
#  page size is 612 x 792 (US Letter).
# ─────────────────────────────────────────────
CONTRACT_PAGE1_FIELDS = {
    # key:               (x,   y,   font_size)
    "contract_no":       (400, 704, 8.0),
    "date":               (548, 704, 8.0),
    "driver_name":        (120, 650, 8.8),
    "dob":                (465, 650, 8.8),
    "address":            (120, 628, 8.8),
    "postcode":           (455, 628, 8.8),
    "license_no":         (120, 606, 8.8),
    "issuing_authority":  (290, 606, 8.8),
    "expiry_date":        (485, 606, 8.8),
    "phone":              (120, 584, 8.8),
    "email":              (260, 584, 8.8),
    "rent":               (130, 478, 8.8),
    "rate":               (145, 440, 8.8),
    "deposit":            (130, 386, 8.8),
    "start_date":         (130, 310, 8.8),
    "expected_return":    (215, 294, 8.8),
    "car_make":           (85, 133, 8.8),
    "registration":       (290, 133, 8.8),
    "car_model":          (465, 133, 8.8),
}
CONTRACT_PAGE2_FIELDS = {
    "contract_no":  (145, 715, 8.8),
    "registration": (390, 715, 8.8),
}
# Optional per-field max width (points) so long values (long names,
# addresses, contract numbers) auto-shrink instead of overrunning
# into the next field / template artwork.
CONTRACT_FIELD_MAXW = {
    "contract_no": 130,
    "date": 55,
    "driver_name": 300,
    "address": 300,
    "car_make": 180,
    "car_model": 130,
}

def _draw_fit(c, text, x, y, base_size=8.8, max_width=None, font="Helvetica"):
    text = str(text)
    if not text:
        return
    size = base_size
    if max_width:
        while size > 5.0 and stringWidth(text, font, size) > max_width:
            size -= 0.3
    c.setFont(font, size)
    c.drawString(x, y, text)

def generate_contract(data: dict) -> bytes:
    buf = io.BytesIO()
    cv = canvas.Canvas(buf, pagesize=letter, pageCompression=1)
    W, H = 612, 792
    bg1, bg2 = _find_img("1"), _find_img("2")

    if bg1: cv.drawImage(bg1, 0, 0, width=W, height=H)
    cv.setFont("Helvetica-Bold", 8.8)
    for key, (x, y, size) in CONTRACT_PAGE1_FIELDS.items():
        cv.setFont("Helvetica-Bold" if key in ("contract_no", "rent", "rate", "deposit", "car_make", "registration", "car_model") else "Helvetica", size)
        _draw_fit(cv, data.get(key, ""), x, y, base_size=size, max_width=CONTRACT_FIELD_MAXW.get(key),
                  font="Helvetica-Bold" if key in ("contract_no", "rent", "rate", "deposit", "car_make", "registration", "car_model") else "Helvetica")
    cv.showPage()

    if bg2: cv.drawImage(bg2, 0, 0, width=W, height=H)
    for key, (x, y, size) in CONTRACT_PAGE2_FIELDS.items():
        _draw_fit(cv, data.get(key, ""), x, y, base_size=size, font="Helvetica-Bold")

    cv.save(); buf.seek(0); return buf.getvalue()

def generate_calibration_grid() -> bytes:
    """Overlays a red 20pt-spaced ruler grid on your actual contract
    template pages so you can read off exact x/y coordinates for each
    field and plug them into CONTRACT_PAGE1_FIELDS / PAGE2_FIELDS above."""
    buf = io.BytesIO()
    cv = canvas.Canvas(buf, pagesize=letter)
    W, H = 612, 792
    for i, bg in enumerate([_find_img("1"), _find_img("2")]):
        if i > 0:
            cv.showPage()
        if bg:
            cv.drawImage(bg, 0, 0, width=W, height=H)
        cv.setStrokeColorRGB(1, 0, 0)
        cv.setFillColorRGB(1, 0, 0)
        cv.setFont("Helvetica", 5)
        for x in range(0, int(W) + 1, 20):
            cv.line(x, 0, x, H)
            cv.drawString(x + 1, H - 8, str(x))
        for y in range(0, int(H) + 1, 20):
            cv.line(0, y, W, y)
            cv.drawString(2, y + 1, str(y))
    cv.save(); buf.seek(0); return buf.getvalue()

# ─────────────────────────────────────────────
#  GATEKEEPER SECURITY PORTAL
# ─────────────────────────────────────────────
if not st.session_state.authenticated:
    st.subheader("🔐 System Security Verification")
    code = st.text_input("Access PIN", type="password", placeholder="Enter key…")
    if st.button("Verify Key"):
        if code == st.secrets.get("ACCESS_KEY", ""):
            st.session_state.authenticated = True
            if cookie_manager is not None:
                cookie_manager.set(
                    AUTH_COOKIE_NAME, "true",
                    expires_at=datetime.now() + timedelta(days=AUTH_COOKIE_DAYS),
                    key="set_auth_cookie",
                )
            st.rerun()
        else:
            st.error("Invalid Security Verification Pin Code")
    st.stop()

with st.sidebar:
    if st.button("🚪 Log out"):
        st.session_state.authenticated = False
        if cookie_manager is not None:
            cookie_manager.delete(AUTH_COOKIE_NAME, key="delete_auth_cookie")
        st.rerun()

# ─────────────────────────────────────────────
#  SECURED MASTER WORKSPACE
# ─────────────────────────────────────────────
for k, v in dict(ocr_name="", ocr_licence="", ocr_address="", ocr_postcode="", ocr_dob="", ocr_expiry="", last_scan_id="", sel_reg="", sel_make="", sel_model="", scan_msg="", fleet_msg="", perm_pdf=None, contract_pdf=None, contract_no="", pending_contract=None).items():
    if k not in st.session_state: st.session_state[k] = v

st.markdown("### 🎛️ Shared Data Automation Panel")
if st.session_state.scan_msg: st.success(st.session_state.scan_msg)
if st.session_state.fleet_msg: st.info(st.session_state.fleet_msg)
col_scan, col_fleet = st.columns(2)

with col_scan:
    uploaded = st.file_uploader("📷 Driver's Licence Scanner", type=["jpg","png","jpeg"], key="global_engine_scanner")
    if uploaded and pytesseract:
        fid = f"{uploaded.name}_{uploaded.size}"
        if st.session_state.last_scan_id != fid:
            with st.spinner("Processing Elements..."):
                try:
                    raw = run_ocr(uploaded); p = parse_licence(raw)
                    st.session_state.ocr_name, st.session_state.ocr_licence, st.session_state.ocr_address, st.session_state.ocr_postcode, st.session_state.ocr_dob, st.session_state.ocr_expiry = f"{p['forename']} {p['surname']}".strip(), p["licence"], p["address"], p["postcode"], p["dob"], p["expiry"]
                    st.session_state.scan_msg = "✅ Licence scanned successfully! Please double-check the fields below before generating documents."
                except Exception as e: st.session_state.scan_msg = f"⚠️ Scan parsing failed: {e}"
                st.session_state.last_scan_id = fid
            st.rerun()
    elif uploaded and not pytesseract:
        st.error("pytesseract isn't installed on this server, so scanning is unavailable.")

with col_fleet:
    opts = ["-- Manual Entry --"] + [f"{v['reg']} ({v['model']})" for v in FLEET_VEHICLES]
    cur = next((o for o in opts if o.startswith(st.session_state.sel_reg)), "-- Manual Entry --") if st.session_state.sel_reg else "-- Manual Entry --"
    chosen = st.selectbox("🚗 Select Fleet Vehicle", opts, index=opts.index(cur), key="global_engine_fleet")
    if chosen != "-- Manual Entry --":
        rk = chosen.split(" (")[0]
        if st.session_state.sel_reg != rk:
            car = next((v for v in FLEET_VEHICLES if v["reg"] == rk), None)
            if car:
                st.session_state.sel_reg = car["reg"]; st.session_state.sel_make, st.session_state.sel_model = split_make_model(car["model"])
                st.session_state.fleet_msg = f"✅ Fleet specs synchronized!"; st.rerun()
    elif st.session_state.sel_reg:
        st.session_state.sel_reg = st.session_state.sel_make = st.session_state.sel_model = ""; st.session_state.fleet_msg = ""; st.rerun()

st.markdown("---")
if st.session_state.pending_contract:
    try:
        st.session_state.contract_pdf = generate_contract(st.session_state.pending_contract)
        st.session_state.contract_no = st.session_state.pending_contract["contract_no"]
    except Exception as e: st.error(f"Render Error: {e}")
    finally: st.session_state.pending_contract = None

tab1, tab2 = st.tabs(["📝 Permission Letter", "📜 Contract Generator"])
with tab1:
    with st.form("perm_form"):
        c1, c2 = st.columns(2)
        with c1:
            p_date, p_ins, p_reg, p_mod = st.date_input("Document Date", datetime.now(), format="DD/MM/YYYY", key="p_form_date"), st.text_input("Insurance Policy No", "HAVFL-000211"), st.text_input("Vehicle Registration", value=st.session_state.sel_reg), st.text_input("Make & Model", value=f"{st.session_state.sel_make} {st.session_state.sel_model}".strip())
        with c2:
            p_name, p_lic, p_start, p_end = st.text_input("Driver Full Name", value=st.session_state.ocr_name), st.text_input("Driving Licence No", value=st.session_state.ocr_licence), st.date_input("Hire Start Date", datetime.now(), format="DD/MM/YYYY", key="p_form_start"), st.date_input("Hire End Date", datetime.now(), format="DD/MM/YYYY", key="p_form_end")
        p_addr = st.text_area("Driver Address", value=st.session_state.ocr_address)
        go_p = st.form_submit_button("🖨️ Generate Permission Letter PDF")
    if go_p:
        st.session_state.perm_pdf = generate_permission_letter({"date": p_date.strftime("%d/%m/%Y"), "insurance_policy": p_ins, "registration": format_uk_reg(p_reg), "make_model": p_mod.upper(), "driver_name": p_name.upper(), "address": p_addr.upper(), "license_no": p_lic.upper(), "start_date": p_start.strftime("%d/%m/%Y"), "end_date": p_end.strftime("%d/%m/%Y")})
        st.rerun()
    if st.session_state.perm_pdf: st.download_button("📥 Download Permission Letter PDF", data=st.session_state.perm_pdf, file_name="Permission_Letter.pdf", mime="application/pdf", key="dl_perm_btn")

with tab2:
    with st.expander("🧭 Field positions off? Calibrate them"):
        st.caption(
            "Download this to see a red 20pt grid drawn over your actual "
            "contract template. Read off the x/y where each field's blank "
            "line sits, then update `CONTRACT_PAGE1_FIELDS` / "
            "`CONTRACT_PAGE2_FIELDS` near the top of app.py."
        )
        st.download_button("📐 Download Calibration Grid PDF", data=generate_calibration_grid(),
                            file_name="Calibration_Grid.pdf", mime="application/pdf", key="dl_cal_btn")

    if st.session_state.contract_pdf:
        st.success(f"🎉 Contract PDF Created Successfully!")
        st.download_button("📥 Download Generated Contract PDF", data=st.session_state.contract_pdf, file_name=f"Contract_{st.session_state.contract_no}.pdf", mime="application/pdf", key="dl_contract_btn")
        st.markdown("---")
    with st.form("contract_form"):
        st.subheader("Hirer Details")
        cc1, cc2 = st.columns(2)
        with cc1:
            c_no, c_name, c_addr, c_post, c_dob = st.text_input("Contract Number", "1608/DRIVER/REG/2026"), st.text_input("Full Name", value=st.session_state.ocr_name), st.text_area("Address", value=st.session_state.ocr_address), st.text_input("Postcode", value=st.session_state.ocr_postcode), st.text_input("Date of Birth (DD/MM/YYYY)", value=normalize_date(st.session_state.ocr_dob))
        with cc2:
            c_date, c_lic, c_exp, c_auth, c_ph, c_em = st.date_input("Contract Date", datetime.now(), format="DD/MM/YYYY", key="c_form_date"), st.text_input("Licence No", value=st.session_state.ocr_licence), st.text_input("Date of Expiry (DD/MM/YYYY)", value=normalize_date(st.session_state.ocr_expiry)), st.text_input("Issuing Authority", "DVLA"), st.text_input("Phone"), st.text_input("Email")
        st.markdown("---"); pp1, pp2, pp3 = st.columns(3)
        with pp1: c_rent = st.text_input("Rent (£/week)", "250/-")
        with pp2: c_rate = st.text_input("Excess (pence/mile)", "20/-")
        with pp3: c_dep = st.text_input("Deposit (£)", "500/-")
        st.markdown("---"); pt1, pt2 = st.columns(2)
        with pt1: c_st = st.date_input("Hire Start", datetime.now(), format="DD/MM/YYYY", key="c_form_start")
        with pt2: c_ret = st.date_input("Expected Return", datetime.now(), format="DD/MM/YYYY", key="c_form_return")
        st.markdown("---"); pv1, pv2, pv3 = st.columns(3)
        with pv1: c_mk = st.text_input("Make", value=st.session_state.sel_make)
        with pv2: c_rv = st.text_input("Reg", value=st.session_state.sel_reg)
        with pv3: c_mv = st.text_input("Model", value=st.session_state.sel_model)
        go_c = st.form_submit_button("🖨️ Generate 2-Page Contract PDF", type="primary")
    if go_c:
        st.session_state.pending_contract = {"contract_no": c_no.strip().upper() or "N/A", "date": c_date.strftime("%d/%m/%Y"), "driver_name": c_name.strip().upper(), "address": c_addr.strip().upper(), "postcode": c_post.strip().upper(), "dob": c_dob.strip(), "license_no": c_lic.strip().upper(), "expiry_date": c_exp.strip(), "issuing_authority": c_auth.strip().upper(), "phone": c_ph.strip(), "email": c_em.strip().upper(), "rent": c_rent.strip(), "rate": c_rate.strip(), "deposit": c_dep.strip(), "start_date": c_st.strftime("%d/%m/%Y"), "expected_return": c_ret.strftime("%d/%m/%Y"), "registration": format_uk_reg(c_rv), "car_make": c_mk.strip().upper(), "car_model": c_mv.strip().upper()}
        st.rerun()
