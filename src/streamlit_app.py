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

def normalize_date(date_str: str) -> str:
    """Convert DD.MM.YYYY or DD-MM-YYYY to DD/MM/YYYY."""
    if not date_str:
        return ""
    return re.sub(r"[.\-]", "/", date_str.strip())

def first_date(fragment: str) -> str:
    """Extract first date-like token and return as DD/MM/YYYY."""
    m = re.search(r"\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}", fragment)
    if not m:
        return ""
    return normalize_date(m.group(0))

def parse_date_value(s: str):
    """Try to parse a date string to a date object for st.date_input."""
    if not s:
        return None
    for fmt in ["%d/%m/%Y", "%d.%m.%Y", "%d-%m-%Y", "%d/%m/%y"]:
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            pass
    return None

def date_to_str(d) -> str:
    """Format a date or datetime as DD/MM/YYYY string."""
    if d is None:
        return ""
    if isinstance(d, (date, datetime)):
        return d.strftime("%d/%m/%Y")
    return str(d)

def strip_address_noise(s: str) -> str:
    s = s.upper()
    s = re.sub(r"UNITED\s+\w*\s*KINGDOM", "", s)
    s = re.sub(r"\b(ENGLAND|SCOTLAND|WALES|NORTHERN\s+IRELAND)\b", "", s)
    s = re.sub(r"\bDVLA\b|\bDVLNI\b|\bDVLA\b", "", s)
    # Remove field labels 3. 4. 4a. 4b. 4c. 5. 6. 7.
    s = re.sub(r"\b[3-7][ABC]?\.?\s*", " ", s)
    # Remove standalone year fragments
    s = re.sub(r"\b(19|20)\d{2}\b", " ", s)
    # Remove date patterns dd.mm.yyyy / dd/mm/yyyy
    s = re.sub(r"\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}", " ", s)
    # Remove licence number patterns
    s = re.sub(r"[A-Z]{5}\d{6}[A-Z0-9]{4,8}", " ", s)
    s = re.sub(r"[^A-Z0-9 ,'\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip().strip(",").strip()
    s = re.sub(r"(,\s*){2,}", ", ", s)
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

def validate_uk_licence(candidate: str) -> str:
    c = re.sub(r"\s", "", candidate.upper())
    m = re.search(r"[A-Z9]{5}\d{6}[A-Z9]{2}[A-Z0-9]{2,3}", c)
    return m.group(0) if m else ""

# ─────────────────────────────────────────────
#  OCR ENGINE
# ─────────────────────────────────────────────
def run_ocr(uploaded_file) -> str:
    img = Image.open(uploaded_file).convert("RGB")
    w, h = img.size
    if max(w, h) < 1800:
        scale = 1800 / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    img = ImageOps.grayscale(img)
    img = ImageEnhance.Contrast(img).enhance(2.0)
    img = img.filter(ImageFilter.SHARPEN)
    import numpy as np
    arr = np.array(img)
    hist, _ = np.histogram(arr.flatten(), bins=256, range=(0, 256))
    total = arr.size
    total_sum = int(np.dot(np.arange(256), hist))
    sb, wb, best_var, thresh = 0, 0, 0, 128
    for i in range(256):
        wb += hist[i]
        if wb == 0: continue
        wf = total - wb
        if wf == 0: break
        sb += i * hist[i]
        mb = sb / wb; mf = (total_sum - sb) / wf
        var = wb * wf * (mb - mf) ** 2
        if var > best_var: best_var = var; thresh = i
    img = img.point(lambda p: 255 if p > thresh else 0)
    return pytesseract.image_to_string(img, config=r"--oem 3 --psm 6")

def parse_licence(raw: str) -> dict:
    blob = " " + re.sub(r"\s+", " ", raw.upper()) + " "

    surname  = clean_name(_grab(blob, [r"1\.", r"[Il]\."], [r"2\."]))
    forename = clean_name(_grab(blob, [r"2\."], [r"3\."]))

    # DOB field 3
    raw_3 = _grab(blob, [r"3\."], [r"4[Aa]\.?", r"4[Aa]\b", r"4\b"])
    dob = first_date(raw_3)

    # Expiry field 4b — flexible end patterns
    raw_4b = _grab(blob,
                   [r"4[Bb]\.?\s*", r"4[Bb]\b"],
                   [r"5\.", r"5\b", r"7\.", r"7\b", r"8\.", r"8\b"])
    expiry = first_date(raw_4b)

    # Licence field 5
    raw_5 = _grab(blob, [r"5\."], [r"[678]\.", r"7\b", r"8\b"])
    licence = validate_uk_licence(raw_5)
    if not licence:
        for cand in re.findall(r"[A-Z9]{5}\d{6}[A-Z9]{2}[A-Z0-9]{2,4}", blob.replace(" ", "")):
            licence = cand[:18]; break

    # Address field 8
    raw_8 = _grab(blob, [r"8\."], [r"9\."])

    if not raw_8:
        lines = [l.strip() for l in raw.split("\n") if l.strip()]
        pc_re = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b", re.I)
        for idx, line in enumerate(lines):
            if pc_re.search(line.upper()):
                window = lines[max(0, idx - 4): idx + 1]
                addr_lines = []
                for wl in window:
                    u = wl.upper().strip()
                    if re.match(r"^\d{1,2}[./\-]\d{1,2}[./\-]\d{4}", u): continue
                    if re.match(r"^(19|20)\d{2}", u): continue
                    if re.match(r"^[3-7][ABC]?[\.\s]", u): continue
                    if re.search(r"[A-Z]{5}\d{6}", u): continue
                    if "DVLA" in u: continue
                    if len(u) < 4: continue
                    addr_lines.append(wl)
                raw_8 = " ".join(addr_lines)
                break

    address_full = strip_address_noise(raw_8)
    postcode = extract_postcode(address_full)
    addr_clean = re.sub(re.escape(postcode), "", address_full, flags=re.I).strip().strip(",").strip() if postcode else address_full

    return {
        "surname": surname, "forename": forename,
        "dob": dob, "expiry": expiry,
        "licence": licence,
        "address": addr_clean, "postcode": postcode,
    }

# ─────────────────────────────────────────────
#  PDF — PERMISSION LETTER
# ─────────────────────────────────────────────
def _src(fn): return os.path.join(SRC_DIR, fn)

def generate_permission_letter(data: dict) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter, pageCompression=1)
    pw, ph = letter
    bg = _src("image_f4efbe.png"); sig = _src("signature.png")
    if os.path.exists(bg): c.drawImage(bg, 0, 0, width=pw, height=ph)
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
    if os.path.exists(sig): c.drawImage(sig, 40, 120, width=280, height=115, mask="auto")
    c.drawString(54, 115, "Muhammad Sohail Qureshi")
    c.drawString(54, 100, "Director (FA-IBI LTD)")
    c.save(); buf.seek(0); return buf.getvalue()

# ─────────────────────────────────────────────
#  PDF — CONTRACT  (built from scratch, matches reference layout)
# ─────────────────────────────────────────────
def generate_contract(data: dict) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter, pageCompression=1)
    W, H = 612, 792
    L, R = 36, 576

    def hline(y): c.line(L, y, R, y)
    def vline(x, y1, y2): c.line(x, y1, x, y2)

    def grey_header(y, text, h=13):
        c.setFillColorRGB(0.82, 0.82, 0.82)
        c.rect(L, y - h, R - L, h, fill=1, stroke=1)
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(W / 2, y - h + 3, text)
        return y - h

    # ── PAGE 1 ─────────────────────────────────────────────
    y = H - 18
    c.rect(L, 36, R - L, H - 54, stroke=1, fill=0)  # outer border

    # Title
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(W / 2, y, "FA-IBI LTD")
    y -= 13; hline(y)

    # Company address row
    y -= 10
    c.setFont("Helvetica", 7)
    c.drawString(L + 2, y, "50-SALISBURY ROAD HOUNSLOW TW4 6JQ")
    c.drawString(215, y, "Ph: 07861838162")
    c.setFillColorRGB(0, 0, 0.75)
    c.drawString(305, y, "Email:info@fa-ibi.co.uk")
    c.setFillColorRGB(0, 0, 0)
    c.drawString(422, y, "Company Registration No: 8844002")
    y -= 12; hline(y)

    # Contract number banner
    y -= 10
    c.setFillColorRGB(0.9, 0.9, 0.9)
    c.rect(L, y - 12, R - L, 12, fill=1, stroke=0)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 7.5)
    c.drawString(L + 2, y - 9, "THIS CONTRACT CONTAINS 2 PAGES.")
    c.drawString(205, y - 9, "CONTRACT NUMBER:")
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(285, y - 9, data["contract_no"])
    c.setFont("Helvetica", 7.5)
    c.drawString(R - 42, y - 9, "Page: 1/2")
    y -= 12; hline(y)

    # ── HIRER DETAILS ──────────────────────────────────────
    y = grey_header(y, "HIRER DETAILS"); hline(y)

    def field_row(y_top, height, pairs):
        """Draw labeled fields in one row. pairs = [(label, value, x_label, x_value, x_line_end), ...]"""
        for label, value, xl, xv, xe in pairs:
            c.setFont("Helvetica", 8)
            c.drawString(xl, y_top - height + 5, label)
            c.setFont("Helvetica-Bold", 8.5)
            c.drawString(xv, y_top - height + 5, value)
            c.line(xv - 2, y_top - height + 3, xe, y_top - height + 3)
        hline(y_top - height)
        return y_top - height

    # Row: Name | DOB
    y -= 1
    c.setFont("Helvetica", 8); c.drawString(L+2, y-12, "Full Name")
    c.setFont("Helvetica-Bold", 8.5); c.drawString(L+47, y-12, data["driver_name"])
    c.line(L+45, y-13, 305, y-13)
    c.setFont("Helvetica", 8); c.drawString(310, y-12, "Date of Birth")
    c.setFont("Helvetica-Bold", 8.5); c.drawString(368, y-12, data["dob"])
    c.line(366, y-13, R-2, y-13)
    y -= 20; hline(y)

    # Row: Address | Postcode
    y -= 1
    c.setFont("Helvetica", 8); c.drawString(L+2, y-12, "Address")
    c.setFont("Helvetica-Bold", 8.5); c.drawString(L+38, y-12, data["address"])
    c.line(L+36, y-13, 305, y-13)
    c.setFont("Helvetica", 8); c.drawString(310, y-12, "Postcode")
    c.setFont("Helvetica-Bold", 8.5); c.drawString(348, y-12, data["postcode"])
    c.line(346, y-13, R-2, y-13)
    y -= 20; hline(y)

    # Row: Licence | Issuing Auth | Expiry
    y -= 1
    c.setFont("Helvetica", 8); c.drawString(L+2, y-12, "License No")
    c.setFont("Helvetica-Bold", 8.5); c.drawString(L+47, y-12, data["license_no"])
    c.line(L+45, y-13, 205, y-13)
    c.setFont("Helvetica", 8); c.drawString(210, y-12, "Issuing authority")
    c.setFont("Helvetica-Bold", 8.5); c.drawString(275, y-12, data["issuing_authority"])
    c.line(273, y-13, 355, y-13)
    c.setFont("Helvetica", 8); c.drawString(360, y-12, "Date of Expiry")
    c.setFont("Helvetica-Bold", 8.5); c.drawString(415, y-12, data["expiry_date"])
    c.line(413, y-13, R-2, y-13)
    y -= 20; hline(y)

    # Row: Ph | Email
    y -= 1
    c.setFont("Helvetica", 8); c.drawString(L+2, y-12, "Ph")
    c.setFont("Helvetica-Bold", 8.5); c.drawString(L+16, y-12, data["phone"])
    c.line(L+14, y-13, 235, y-13)
    c.setFont("Helvetica", 8); c.drawString(240, y-12, "Email")
    c.setFont("Helvetica-Bold", 8.5); c.drawString(260, y-12, data["email"])
    c.line(258, y-13, R-2, y-13)
    y -= 20; hline(y)

    # ── PERSONAL DETAILS ───────────────────────────────────
    y = grey_header(y, "Personal Details - Driving History"); hline(y)

    def yn_row(question, continuation=None):
        nonlocal y
        y -= 1
        c.setFont("Helvetica", 7.5)
        c.drawString(L+2, y-10, question)
        if continuation:
            c.drawString(L+2, y-19, continuation)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(R-44, y-10, "YES / NO")
        drop = 28 if continuation else 18
        y -= drop; hline(y)

    yn_row("(A) Have you any physical defect or infirmity")
    yn_row("(B) Have you been convicted or have a prosecution pending for any motoring offence",
           "     or has your license been suspended or endorsed?")
    yn_row("(C) Have you ever been refused or declined motor insurance or increased premiums",
           "     or terms imposed?")

    y -= 1
    c.setFont("Helvetica", 7.5)
    c.drawString(L+2, y-10, "If answer Yes to any of the above, please give Details")
    c.line(262, y-11, R-2, y-11)
    y -= 17; hline(y)

    y -= 1
    c.setFont("Helvetica", 7.5)
    c.drawString(L+2, y-10, "Purpose for which the vehicle is to be used")
    c.line(232, y-11, 395, y-11)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(400, y-10, "SDP / Private Hire")
    y -= 17; hline(y)

    # Legal paragraph
    legal = ("I hereby warrant the truth of the above statements and I declare that I have withheld no information "
             "whatsoever which might tend in a way to increase the risk of the insurers or influence the acceptance "
             "of the proposal. I agree that this proposal shall be the basis of the contract between me and the "
             "insurers and I further agree to be bound by the terms and conditions and exceptions of the policy, "
             "which I have the opportunity to see and read. I further declare that my occupation and personal details "
             "and driving do not render me ineligible to hire.")
    y -= 2
    c.setFont("Helvetica", 7)
    for line in simpleSplit(legal, "Helvetica", 7, R - L - 4):
        c.drawString(L+2, y-9, line); y -= 9
    y -= 3; hline(y)

    # ── PAYMENT SECTION ────────────────────────────────────
    MID = 338
    pay_top = y

    # Column headers
    c.setFillColorRGB(0.82, 0.82, 0.82)
    c.rect(L, pay_top-13, MID-L, 13, fill=1, stroke=1)
    c.rect(MID, pay_top-13, R-MID, 13, fill=1, stroke=1)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString((L+MID)//2, pay_top-10, "HIRE PAYMENT")
    c.drawCentredString((MID+R)//2, pay_top-10, "METHOD OF PAYMENT")
    pay_top -= 13

    PAY_H = 100  # height of payment block
    vline(MID, pay_top, pay_top - PAY_H)
    hline(pay_top - PAY_H)

    # Left payment column
    lx, ly = L+2, pay_top
    c.setFont("Helvetica", 7.5)
    c.drawString(lx, ly-10, "The rental of £")
    c.setFont("Helvetica-Bold", 8); c.drawString(lx+58, ly-10, data["rent"])
    c.setFont("Helvetica", 7.5); c.drawString(lx+85, ly-10, "Per week at the prevailing rate")
    c.drawString(lx, ly-19, "multiplied by the number of weeks of hire / rental")
    c.drawString(lx, ly-29, "On termination of the hire / rental the Hirer will pay the Lessor an")
    c.drawString(lx, ly-38, "excess mileage charge at the rate of")
    c.setFont("Helvetica-Bold", 8); c.drawString(lx+143, ly-38, data["rate"])
    c.setFont("Helvetica", 7.5); c.drawString(lx+162, ly-38, "Pence per mile. (4500 mpm)")
    c.drawString(lx, ly-47, "Maximum hire under this agreement shall be")
    c.drawString(lx, ly-56, "THIS IS BASED ON THE MAXIMUM HIRE PERIOD")
    c.setFillColorRGB(0.8, 0, 0); c.setFont("Helvetica-Bold", 7.5)
    c.drawString(lx, ly-66, "ROAD SIDE RECOVERY IS NOT INCLUDED.")
    c.drawString(lx+80, ly-78, "TYRE MAINTENANCE NOT INCLUDED")
    c.setFillColorRGB(0, 0, 0); c.setFont("Helvetica", 7.5)
    c.drawString(lx, ly-88, "Deposit paid £")
    c.setFont("Helvetica-Bold", 8); c.drawString(lx+54, ly-88, data["deposit"])

    # Right payment column
    rx, ry = MID+4, pay_top
    c.setFont("Helvetica", 7.5)
    c.drawString(rx, ry-10, "Method of Payment: CASH")
    c.drawString(rx, ry-19, "CHEQUE    BANK TRANSFER")
    c.drawString(rx, ry-28, "*delete as necessary")
    c.setFont("Helvetica-Bold", 8)
    c.drawString(rx, ry-39, "Please make cheque payable to:  FA-IBI LTD")
    c.drawString(rx, ry-49, "ACC   43605086")
    c.drawString(rx, ry-59, "SORT CODE: 20-42-73")
    c.setFont("Helvetica", 7.5)
    c.drawString(rx, ry-69, "Please set standing order to avoid late payment penalty.")
    c.drawString(rx, ry-79, "Late payment surcharge is £5/ day.")

    y = pay_top - PAY_H

    # Acceptance + signed
    y -= 1
    c.setFont("Helvetica-Bold", 7)
    c.drawString(L+2, y-9, "I ACCEPT AND AGREE THAT THE FINANCIAL DETAILS ABOVE HERE HAVE BEEN COMPLETED PRIOR TO MY SIGNATURE.")
    y -= 12
    c.drawString(L+2, y-9, "I FURTHER ACCEPT THE ABOVE CHARGES ARE MY RESPONSIBILITY AT ALL TIMES")
    y -= 12
    c.setFont("Helvetica-Bold", 9); c.drawString(L+2, y-9, "SIGNED X")
    c.line(L+48, y-10, R-2, y-10)
    y -= 14; hline(y)

    # ── HIRE PERIOD ────────────────────────────────────────
    y = grey_header(y, "HIRE PERIOD"); hline(y)

    def hp(label, val, right_text=""):
        nonlocal y
        y -= 1
        c.setFont("Helvetica", 8); c.drawString(L+2, y-12, label)
        c.setFont("Helvetica-Bold", 9); c.drawString(L+2+len(label)*4.6, y-12, val)
        c.line(L+2+len(label)*4.6-2, y-13, 255, y-13)
        if right_text:
            c.setFont("Helvetica", 8); c.drawString(260, y-12, right_text)
        y -= 17; hline(y)

    hp("Date Hire start:   ", data["start_date"], "Time: 1100 HOURS")
    hp("Expected date of Vehicle Return:   ", data["expected_return"], "Time: 1700 HOURS")

    y -= 1
    c.setFont("Helvetica", 8); c.drawString(L+2, y-12, "Actual Date of Vehicle Return.")
    c.line(170, y-13, 250, y-13)
    c.drawString(255, y-12, "Time:"); c.line(276, y-13, R-2, y-13)
    y -= 17; hline(y)

    y -= 1
    c.setFont("Helvetica", 8); c.drawString(L+2, y-12, "extension of hiring period . Time and date :")
    c.line(222, y-13, R-2, y-13)
    y -= 17; hline(y)

    # ── HIRE VEHICLE DETAILS ───────────────────────────────
    y = grey_header(y, "HIRE VEHICLE DETAILS"); hline(y)
    C2 = L + (R-L)//3; C3 = L + 2*(R-L)//3

    y -= 1
    vline(C2, y, y-19); vline(C3, y, y-19)
    c.setFont("Helvetica", 8); c.drawString(L+2, y-12, "Vehicle")
    c.line(L+34, y-13, C2-4, y-13)
    c.setFont("Helvetica-Bold", 9); c.drawString(L+38, y-12, data["car_make"])
    c.setFont("Helvetica", 8); c.drawString(C2+2, y-12, "Reg No")
    c.line(C2+32, y-13, C3-4, y-13)
    c.setFont("Helvetica-Bold", 9); c.drawString(C2+36, y-12, data["registration"])
    c.setFont("Helvetica", 8); c.drawString(C3+2, y-12, "Model")
    c.line(C3+28, y-13, R-2, y-13)
    c.setFont("Helvetica-Bold", 9); c.drawString(C3+32, y-12, data["car_model"])
    y -= 19; hline(y)

    y -= 1
    vline(C2, y, y-18); vline(C3, y, y-18)
    c.setFont("Helvetica", 8)
    c.drawString(L+2, y-12, "Tools Yes/No"); c.line(L+56, y-13, C2-4, y-13)
    c.drawString(C2+2, y-12, "Spare Yes/ No"); c.line(C2+60, y-13, C3-4, y-13)
    c.drawString(C3+2, y-12, "Mileage Out: ................")
    c.drawString(C3+100, y-12, "Mileage In: ................")
    y -= 18; hline(y)

    # Signatures
    y -= 2
    c.setFont("Helvetica", 8)
    c.drawString(L+2, y-12, "Hirers Signature X"); c.line(L+84, y-13, 285, y-13)
    c.drawString(290, y-12, "Owners Signatur"); c.line(358, y-13, R-2, y-13)
    y -= 19; hline(y)
    c.setFont("Helvetica-Bold", 8); c.drawString(L+2, y-12, "DATE:")
    c.line(L+28, y-13, 200, y-13)
    y -= 16; hline(y)
    c.setFont("Helvetica", 9); c.drawCentredString(W/2, 42, "1")

    # ══════════════════════════════════════════
    #  PAGE 2 — TERMS AND CONDITIONS
    # ══════════════════════════════════════════
    c.showPage()
    y = H - 18
    c.rect(L, 36, R-L, H-54, stroke=1, fill=0)

    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(W/2, y, "TERMS AND CONDITIONS OF FA-IBI LTD")
    y -= 12; hline(y)

    # Sub banner
    c.setFillColorRGB(0.82, 0.82, 0.82)
    c.rect(L, y-13, R-L, 13, fill=1, stroke=1)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(L+2, y-10, "CONTRACT NUMBER:")
    c.drawString(L+90, y-10, data["contract_no"])
    c.drawString(275, y-10, "CAR REG :")
    c.drawString(312, y-10, data["registration"])
    c.drawString(R-42, y-10, "Page: 2/2")
    y -= 13; hline(y)

    # Definitions line
    y -= 1
    c.setFont("Helvetica", 7)
    c.drawString(L+2, y-9, "Hirer means the person or entity which contracts to hire a Vehicle.")
    c.drawString(310, y-9, "Lessor means the hire company FA-IBI LTD")
    y -= 11; hline(y)

    # Two-column terms
    CM = (L + R) // 2
    vline(CM, y, 55)

    terms_l = [
        ("b","1.  At no time the vehicle be used, operated or driven."),
        ("n","(a) For the damage of persons for hire or reward whether Express or implied, (unless approval has been agreed)."),
        ("n","(b) By a person who is less than 22 years of age or more then 65 years of age (unless such age has been agreed) or By any person who has given to the lessor any false particulars."),
        ("n","(c) Knowingly for any unlawful purpose."),
        ("n","(d) To propel or tow any vehicle or trailer."),
        ("n","(e) For racing, reliability trials speed testing or driving tuition."),
        ("n","(f) By any person except the hire unless the lessor provides Permission beforehand."),
        ("n","(g) To carry a greater number of passengers and on more baggage Than is recommended by the manufacturer."),
        ("n","(h) After the expiry of the period of hire of as stated overleaf."),
        ("n","(I) Outside the British Isles except with prior notice agreed with the lessor."),
        ("n","(J) The vehicle must not be driven in manner which would render void any insurance and/or other contract of insurance or in contravention of any road or traffic act or contravention of road use regulations, nor must it be driven in the event of mechanical, electrical or structural failure which might cause further damage."),
        ("b","2.  The hirer will return the vehicle to the lessor's address shown together with all tyres, tools, accessories and equipment in the condition as when received (ordinary wear and tear excepted)."),
        ("b","3.  The hirer shall not use the vehicle if any damage or fault shall arise so as to make the vehicle unroadworthy or liable to cause damage to any person or property until such damage or fault has been repaired and corrected. In the event of any such fault arising which can be repaired at a total cost of less than £10, the hirer shall either return the vehicle to the lessor or authorise the carrying out of such repair by a reputable and properly qualified motor repairer. Authorisation for expenditure in excess of £25 must be obtained from the lessor prior to commencement of the repair."),
        ("b","4.  In case of accident the hirer is responsible for the cost of repair of the car whether the hirer is responsible for the cause of accident or not.In case of vehicle write off, hirer shall pay the total value of the vehicle less salvage value to lesser and cannot claim the salvage vehicle."),
        ("b","the hirer can recover the cost from the third party insurance"),
        ("n","In case of non fault the cost of vehicle damage and depreciation will be determine by the independent engineer report from a reputed company and hirer is responsible to pay according to that report the hirer is authorising the insurance company to issue the payment related to vehicle repair or write off value to the lessor."),
        ("n","5.  The hirer shall be liable as owner of the vehicle in respect of,"),
        ("n","(a) Any of the following offences which may be committed in relation to that vehicle when it is stationary and when a penalty notice is issued being on a road during the hours of darkness without the light or reflections required by law, or being left or park, or being loaded or unloaded and the non-payment of charge made at a street parking place and/or pay & displays."),
        ("n","(b) Any fixed penalty offence including congestion charge committed in respect of that vehicle under part iii and section 66 of the road traffic act 1988"),
    ]
    terms_r = [
        ("n","and  schedule 2 to the road traffic regulation 2000 as amended, replaced or extended by any subsequent legislation or orders any such offence committed under the equivalent applicable to Scotland Northern Ireland or other parts of the British Isles upon which the vehicle is being used"),
        ("n","(c) Any access charge which may be incurred in respect of that vehicle in pursuance of an order under section 45 and 46 of the road Traffic Act1984, as amended, replaced or extended by any subsequent legislation or orders and under the equivalent legislation applicable to Scotland, Northern Ireland or other parts of the British Isles upon which the vehicle is being used."),
        ("b","6.  The hirer shall immediately report to the lessor any accident which the vehicle is involved in and shall deliver to the lessor every process, pleading or notice on paper of any kind received by the hirer or the vehicle relating to any claim or proceeding connected with any such accident or event involving the vehicle."),
        ("b","7.  The hirer shall defend and indemnify the lessor from and against any and all losses, liabilities, damages, injuries, claims, demands cost and expenses arising out of connected with the possession or use of the vehicle during the rental term (except those covered by the insurance providing here under by the lessor) and caused by negligence and non-observance of the agreement on the part of the hirer, his driver, agents or employees including but not limited to any and claims liabilities third parties arising out of the disposal of the vehicle by government authority for illegal or improper use of said vehicle."),
        ("b","8.  Notwithstanding the period of hire shown overleaf."),
        ("n","(a) The lessor may demand the return of the vehicle at any time so long as at all material times the lessor is aware or becomes aware of any activity on the part of the lessor in relation to the vehicle which could reasonably lead the lessor to believe that the hirer is acting or likely to act in a manner prejudicial to the preservation, maintenance or good upkeep of the vehicle."),
        ("n","(b) If the vehicle is not returned within the minimum hire period and/or in accordance with paragraph (a) of this clause the hirer will pay the Lessor hire charges at the lessor's published tariffs for such period as the vehicle shall be wrongfully retained by the hirer, his servant and/or agents, including any administration charges incurred."),
        ("b","9.  The hirer shall pay to the lessor, hire charges and/or other such charges that become due under this agreement, by one single instalment within one month beginning with the date of this agreement."),
        ("b","10. Any addition to or alternative of the terms and conditions of agreement shall be null and void unless agreed upon in writing by by the lessor and hirer."),
        ("b","11. The hirer agrees to compensate the lessor in full for any loss in case of fire or theft."),
        ("b","12. Minimum hire period is 4 weeks."),
        ("b","13. The hirer may terminate the hire of the vehicle by giving 2 weeks notice and returning the vehicle to the lessor."),
        ("b","14. BULBS AND TYRES are hirer responsabalty ."),
        ("b","15. I(Hirer) fully agree to check OIL and Water on daily basis."),
        ("b","16. I(Hirer) give my consent to share my details with third party"),
        ("b","17. I (Hirer) give my consent to transfer all liabilities and penalty charges  including Congestion Charge on my name."),
    ]

    CW = CM - L - 6
    FS = 6.8

    def draw_col(terms, x, start_y, col_w):
        ty = start_y
        for style, text in terms:
            fn = "Helvetica-Bold" if style == "b" else "Helvetica"
            c.setFont(fn, FS)
            for line in simpleSplit(text, fn, FS, col_w):
                if ty < 62: break
                c.drawString(x, ty, line); ty -= 8
            ty -= 2
        return ty

    content_y = y - 3
    draw_col(terms_l, L+2, content_y, CW)
    draw_col(terms_r, CM+4, content_y, CW)

    # Signature footer
    sig_y = 54
    hline(sig_y)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(L+2, sig_y-13, "Hirer Signature"); c.line(L+72, sig_y-14, 218, sig_y-14)
    c.drawString(223, sig_y-13, "DATE:"); c.line(248, sig_y-14, 380, sig_y-14)
    c.drawString(385, sig_y-13, "Owner's Signature"); c.line(460, sig_y-14, R-2, sig_y-14)
    c.setFont("Helvetica", 9); c.drawCentredString(W/2, 42, "2")

    c.save(); buf.seek(0); return buf.getvalue()

# ─────────────────────────────────────────────
#  STREAMLIT UI
# ─────────────────────────────────────────────
st.set_page_config(page_title="FA-IBI Workspace", layout="centered")
st.markdown("""
<style>
#MainMenu,footer,header,[data-testid="stToolbar"],
.viewerBadge_container__1743q,[class*="viewerBadge"]{
    display:none!important;visibility:hidden!important;opacity:0!important;}
.main .block-container{padding-top:1rem!important;max-width:100%!important;padding-bottom:5rem!important;}
.vch-footer{position:fixed;bottom:0;left:0;right:0;width:100vw;background:#0e1117;
    text-align:center;padding:12px 0;font-size:14px;color:#888;
    border-top:1px solid #1f2937;z-index:9999;}
.vch-footer a{color:#FF8C00;font-weight:bold;text-decoration:none;}
@media(max-width:768px){input,select,textarea,.stSelectbox{font-size:16px!important;}}
</style>
""", unsafe_allow_html=True)

# ── Auth ──────────────────────────────────────
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if st.query_params.get("session") == "active": st.session_state.authenticated = True
if not st.session_state.authenticated:
    code = st.text_input("System Access", type="password",
                         label_visibility="collapsed", placeholder="Enter key…")
    if code == st.secrets.get("ACCESS_KEY", ""):
        st.session_state.authenticated = True
        st.query_params["session"] = "active"; st.rerun()
    else: st.stop()

# ── Session defaults ──────────────────────────
for k, v in dict(
    ocr_name="", ocr_licence="", ocr_address="", ocr_postcode="",
    ocr_dob="", ocr_expiry="", last_scan_id="",
    sel_reg="", sel_make="", sel_model="",
    scan_msg="", fleet_msg="",
    perm_pdf=None, contract_pdf=None, contract_no="",
).items():
    if k not in st.session_state: st.session_state[k] = v

st.title("FA-IBI Master Document Workspace")

# ─────────────────────────────────────────────
#  AUTOMATION PANEL
# ─────────────────────────────────────────────
def render_automation(ctx):
    st.markdown("#### 🎛️ Data Automation")
    if st.session_state.scan_msg:  st.success(st.session_state.scan_msg)
    if st.session_state.fleet_msg: st.info(st.session_state.fleet_msg)

    col_scan, col_fleet = st.columns(2)
    with col_scan:
        uploaded = st.file_uploader("📷 Driver's Licence Scanner",
                                    type=["jpg","png","jpeg"],
                                    key=f"uploader_{ctx}")
        if uploaded and pytesseract:
            fid = f"{uploaded.name}_{uploaded.size}"
            if st.session_state.last_scan_id != fid:
                with st.spinner("Scanning…"):
                    try:
                        raw = run_ocr(uploaded)
                        p = parse_licence(raw)
                        st.session_state.ocr_name     = f"{p['forename']} {p['surname']}".strip()
                        st.session_state.ocr_licence  = p["licence"]
                        st.session_state.ocr_address  = p["address"]
                        st.session_state.ocr_postcode = p["postcode"]
                        st.session_state.ocr_dob      = p["dob"]
                        st.session_state.ocr_expiry   = p["expiry"]
                        st.session_state.scan_msg     = "✅ Licence scanned — fields populated!"
                    except Exception as e:
                        st.session_state.scan_msg = f"⚠️ Scan error: {e}"
                    st.session_state.last_scan_id = fid
                st.rerun()

    with col_fleet:
        options = ["-- Manual Entry --"] + [f"{v['reg']} ({v['model']})" for v in FLEET_VEHICLES]
        current = "-- Manual Entry --"
        if st.session_state.sel_reg:
            hit = [o for o in options if o.startswith(st.session_state.sel_reg)]
            if hit: current = hit[0]
        chosen = st.selectbox("🚗 Select Vehicle", options,
                              index=options.index(current), key=f"fleet_{ctx}")
        if chosen != "-- Manual Entry --":
            rk = chosen.split(" (")[0]
            if st.session_state.sel_reg != rk:
                car = next((v for v in FLEET_VEHICLES if v["reg"] == rk), None)
                if car:
                    mk, mo = split_make_model(car["model"])
                    st.session_state.sel_reg = car["reg"]
                    st.session_state.sel_make = mk; st.session_state.sel_model = mo
                    st.session_state.fleet_msg = f"✅ {rk} loaded!"; st.rerun()
        else:
            if st.session_state.sel_reg:
                st.session_state.sel_reg = st.session_state.sel_make = st.session_state.sel_model = ""
                st.session_state.fleet_msg = ""; st.rerun()

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

    # Show download above form if already generated
    if st.session_state.perm_pdf:
        st.download_button("📥 Download Permission Letter PDF",
                           data=st.session_state.perm_pdf,
                           file_name="Permission_Letter.pdf",
                           mime="application/pdf", key="dl_perm_top")

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
            st.success("✅ Permission Letter ready!")
            st.download_button("📥 Download Permission Letter PDF",
                               data=st.session_state.perm_pdf,
                               file_name="Permission_Letter.pdf",
                               mime="application/pdf", key="dl_perm_bottom")
        except Exception as e:
            st.error(f"PDF error: {e}")

# ══════════════════════════════════
#  TAB 2 — CONTRACT
# ══════════════════════════════════
with tab2:
    render_automation("tab2")
    st.markdown("---")

    # Show download ABOVE form so it's always visible after generation
    if st.session_state.contract_pdf:
        st.success("✅ Contract ready to download!")
        st.download_button("📥 Download Contract PDF",
                           data=st.session_state.contract_pdf,
                           file_name=f"FA_IBI_Contract_{st.session_state.contract_no}.pdf",
                           mime="application/pdf", key="dl_contract_top")
        st.markdown("---")

    go_c = False

    # Parse OCR dates for default values
    dob_default    = parse_date_value(st.session_state.ocr_dob) or date(2000, 1, 1)
    expiry_default = parse_date_value(st.session_state.ocr_expiry) or date(2030, 1, 1)

    with st.form("contract_form"):
        st.subheader("Hirer Details")
        cc1, cc2 = st.columns(2)
        with cc1:
            c_no      = st.text_input("Contract Number", "1608/DRIVER/REG/2026")
            c_name    = st.text_input("Full Name", value=st.session_state.ocr_name)
            c_address = st.text_area("Address",    value=st.session_state.ocr_address)
            c_post    = st.text_input("Postcode",  value=st.session_state.ocr_postcode)
            # DOB as date picker — auto-populated from OCR
            c_dob_d   = st.date_input("Date of Birth", dob_default,
                                       min_value=date(1920,1,1),
                                       max_value=date.today(),
                                       format="DD/MM/YYYY")
        with cc2:
            c_date    = st.date_input("Contract Date", datetime.now(), format="DD/MM/YYYY")
            c_lic     = st.text_input("Licence No",  value=st.session_state.ocr_licence)
            # Expiry as date picker — auto-populated from OCR
            c_exp_d   = st.date_input("Expiry Date", expiry_default,
                                       min_value=date(2020,1,1),
                                       max_value=date(2099,12,31),
                                       format="DD/MM/YYYY")
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
        with pt1: c_start  = st.date_input("Hire Start",      datetime.now(), format="DD/MM/YYYY")
        with pt2: c_return = st.date_input("Expected Return",  datetime.now(), format="DD/MM/YYYY")

        st.markdown("---")
        st.subheader("Vehicle")
        pv1, pv2, pv3 = st.columns(3)
        with pv1: c_make  = st.text_input("Make",  value=st.session_state.sel_make)
        with pv2: c_reg_v = st.text_input("Reg",   value=st.session_state.sel_reg)
        with pv3: c_mod_v = st.text_input("Model", value=st.session_state.sel_model)

        go_c = st.form_submit_button("🖨️ Generate 2-Page Contract PDF", type="primary")

    if go_c:
        try:
            cpay = {
                "contract_no":       c_no.upper(),
                "date":              c_date.strftime("%d/%m/%Y"),
                "driver_name":       c_name.upper(),
                "address":           c_address.upper(),
                "postcode":          c_post.upper(),
                "dob":               c_dob_d.strftime("%d/%m/%Y"),
                "license_no":        c_lic.upper(),
                "expiry_date":       c_exp_d.strftime("%d/%m/%Y"),
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
            st.success("✅ Contract generated!")
            st.download_button("📥 Download Contract PDF",
                               data=st.session_state.contract_pdf,
                               file_name=f"FA_IBI_Contract_{cpay['contract_no']}.pdf",
                               mime="application/pdf", key="dl_contract_bottom")
        except Exception as e:
            st.error(f"Contract PDF error: {e}")
            import traceback
            st.code(traceback.format_exc())

st.markdown('<div class="vch-footer">Powered By '
            '<a href="https://virtualcarhire.pages.dev/" target="_blank">Virtual Car Hire</a>'
            '</div>', unsafe_allow_html=True)
