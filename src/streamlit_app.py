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
    s = re.sub(r"\b[3-7][ABC]?\.?\s*", " ", s)
    s = re.sub(r"\b(19|20)\d{2}\b", " ", s)
    s = re.sub(r"\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}", " ", s)
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
#  OCR  (works for all licence types)
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

STREET_TYPES = ["ROAD","STREET","AVENUE","LANE","DRIVE","CLOSE","WAY","GARDENS",
                "CRESCENT","PLACE","COURT","GROVE","TERRACE","WALK","SQUARE","HILL",
                "VALE","VIEW","RISE","MEWS","PARADE","AVENUE","BOULEVARD","CIRCUS"]

def parse_licence(raw: str) -> dict:
    blob = " " + re.sub(r"\s+", " ", raw.upper()) + " "

    # ── Surnames (field 1) ──────────────────
    surname = clean_name(_grab(blob, [r"1\.", r"[Il]\."], [r"2\."]))
    if not surname:
        m = re.search(r"\b(?:SURNAME|LAST\s+NAME)[:\s]+([A-Z][A-Z\s'\-]{1,40}?)(?=\s+(?:2\.|FIRST|GIVEN|FORENAME|3\.))", blob)
        if m: surname = clean_name(m.group(1))

    # ── Forenames (field 2) ─────────────────
    raw_2 = _grab(blob, [r"2\."], [r"3\."])
    # Remove any digit-dot sequences (field markers) from the forename region
    raw_2 = re.sub(r"\b\d[A-Ca-c]?\.?\s*", " ", raw_2)
    forename = clean_name(raw_2)
    if not forename:
        m = re.search(r"\b(?:FORENAME|FIRST\s+NAME|GIVEN\s+NAME)[S]?[:\s]+([A-Z][A-Z\s'\-]{1,40}?)(?=\s+(?:3\.|DOB|DATE|SURNAME))", blob)
        if m: forename = clean_name(m.group(1))

    # ── DOB (field 3) ───────────────────────
    raw_3 = _grab(blob, [r"3\."], [r"4[Aa]\.?", r"4\b"])
    dob = first_date(raw_3)
    if not dob:
        m = re.search(r"(?:D\.?O\.?B|DATE\s+OF\s+BIRTH|BIRTH)[:\s]+(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})", blob)
        if m: dob = normalize_date(m.group(1))
    if not dob:
        # Take the FIRST date found that looks like a birth year (before 2010)
        for m in re.finditer(r"\b(\d{1,2}[./\-]\d{1,2}[./\-](19|20)\d{2})\b", blob):
            candidate = normalize_date(m.group(1))
            year = int(candidate.split("/")[2]) if "/" in candidate else 0
            if year < 2010: dob = candidate; break

    # ── Expiry (field 4b) ───────────────────
    raw_4b = _grab(blob, [r"4[Bb][\.\s]?", r"4[Bb]\b"],
                   [r"5\.", r"5\b", r"7\.", r"7\b", r"8\.", r"8\b"])
    expiry = first_date(raw_4b)
    if not expiry:
        m = re.search(r"(?:EXPIRY|EXPIR[YE]S?|VALID\s+UNTIL|DATE\s+OF\s+EXPIRY)[:\s]+(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})", blob)
        if m: expiry = normalize_date(m.group(1))
    if not expiry:
        # Last date found (expiry dates are usually latest)
        dates_found = [(normalize_date(m.group(0)), int(normalize_date(m.group(0)).split("/")[2]) if "/" in m.group(0) else 0)
                       for m in re.finditer(r"\b\d{1,2}[./\-]\d{1,2}[./\-](20)\d{2}\b", blob)]
        if dates_found:
            expiry = max(dates_found, key=lambda x: x[1])[0]

    # ── Licence number (field 5) ────────────
    raw_5 = _grab(blob, [r"5\."], [r"[678]\.", r"7\b", r"8\b"])
    licence = validate_uk_licence(raw_5)
    if not licence:
        for cand in re.findall(r"[A-Z9]{5}\d{6}[A-Z9]{2}[A-Z0-9]{2,4}", blob.replace(" ", "")):
            licence = cand[:18]; break

    # ── Address (field 8) ───────────────────
    raw_8 = _grab(blob, [r"8\."], [r"9\."])

    if not raw_8:
        lines = [l.strip() for l in raw.split("\n") if l.strip()]
        pc_re = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b", re.I)

        # Strategy 1: find postcode line, grab clean lines above it
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

        # Strategy 2: find a line with a street-type keyword
        if not raw_8:
            for idx, line in enumerate(lines):
                u = line.upper()
                if any(f" {kw} " in f" {u} " or u.endswith(f" {kw}") for kw in STREET_TYPES):
                    window = lines[max(0, idx): min(len(lines), idx + 3)]
                    raw_8 = " ".join(window)
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
#  PDF — PERMISSION LETTER  (unchanged)
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
#  PDF — CONTRACT  (new template matching 1.png / 2.png)
# ─────────────────────────────────────────────
def generate_contract(data: dict) -> bytes:
    buf = io.BytesIO()
    cv = canvas.Canvas(buf, pagesize=letter, pageCompression=1)
    W, H = 612, 792
    L, R = 28, 584
    BW = R - L   # body width

    def hl(y): cv.line(L, y, R, y)
    def vl(x, y1, y2): cv.line(x, y1, x, y2)
    def grey_bar(y, h, txt, fs=9):
        cv.setFillColorRGB(0.78, 0.78, 0.78)
        cv.rect(L, y - h, BW, h, fill=1, stroke=1)
        cv.setFillColorRGB(0, 0, 0)
        cv.setFont("Helvetica-Bold", fs)
        cv.drawCentredString(W/2, y - h + (h - fs) / 2 + 1, txt)
        return y - h

    # ══════════════════════════════════════════
    #  PAGE 1
    # ══════════════════════════════════════════
    y = H - 16
    cv.rect(L, 30, BW, H - 46, stroke=1, fill=0)

    # ── Title ─────────────────────────────────
    cv.setFont("Helvetica-Bold", 20)
    cv.drawCentredString(W/2, y - 2, "FA-IBI LTD")
    y -= 20; hl(y)

    # ── Company info ──────────────────────────
    y -= 9
    cv.setFont("Helvetica", 7.5)
    cv.drawString(L+3, y, "50 SALISBURY RAOD HOUNSLOW TW4 6JQ")
    cv.drawString(255, y, "PH: 07861838162")
    cv.setFillColorRGB(0, 0, 0.8)
    cv.drawString(392, y, "Email:info@fa-ibi.co.uk")
    cv.setFillColorRGB(0, 0, 0)
    y -= 9
    cv.drawString(392, y, "Company Registration No: 8844002")
    y -= 3; hl(y)

    # ── Contract number banner ────────────────
    y -= 1
    cv.setFillColorRGB(0.88, 0.88, 0.88)
    cv.rect(L, y-14, BW, 14, fill=1, stroke=0); hl(y); hl(y-14)
    cv.setFillColorRGB(0, 0, 0)
    cv.setFont("Helvetica-Bold", 8)
    cv.drawString(L+3, y-10, "THIS CONTRACT CONTAINS 2 PAGES")
    cv.drawString(225, y-10, "CONTRACT NUMBER:")
    cv.drawString(308, y-10, data["contract_no"])
    cv.drawString(R-50, y-10, "PAGE: 1/2")
    y -= 14

    # ── HIRER DETAILS ─────────────────────────
    y = grey_bar(y, 16, "HIRER DETAILS", 10); hl(y)

    def labelled(y_top, h, items):
        """items = [(label, value, x_label, x_val_start, x_line_end), ...]"""
        for lbl, val, xl, xv, xe in items:
            cv.setFont("Helvetica-Bold", 8)
            cv.drawString(xl, y_top - h + 4, lbl)
            cv.setFont("Helvetica", 8.5)
            cv.drawString(xv, y_top - h + 4, str(val))
            cv.line(xv - 2, y_top - h + 2, xe, y_top - h + 2)
        hl(y_top - h)
        return y_top - h

    # Full Name | DOB
    y -= 1
    y = labelled(y, 22, [
        ("Full Name:", data["driver_name"], L+3, L+52, 350),
        ("Date Of Birth:", data["dob"],     355, 430, R-3),
    ])
    # Address | Postcode
    y -= 1
    y = labelled(y, 22, [
        ("Address:", data["address"], L+3, L+42, 350),
        ("Postcode:", data["postcode"], 355, 415, R-3),
    ])
    # Licence | Issuing Auth | Expiry
    y -= 1
    C2, C3 = L + BW//3, L + 2*BW//3
    vl(C2, y, y-22); vl(C3, y, y-22)
    y = labelled(y, 22, [
        ("License No:", data["license_no"],     L+3,   L+50,  C2-3),
        ("Issuing Authority:", data["issuing_authority"], C2+3, C2+82, C3-3),
        ("Date Of Expiry:", data["expiry_date"], C3+3, C3+70, R-3),
    ])
    # Ph | Email
    y -= 1
    vl(200, y, y-22)
    y = labelled(y, 22, [
        ("Ph:", data["phone"], L+3, L+20, 198),
        ("Email:", data["email"], 203, 228, R-3),
    ])

    # ── PERSONAL DETAILS ──────────────────────
    y = grey_bar(y, 14, "Personal Details - Driving History", 9); hl(y)

    def yn_row(q1, q2=None):
        nonlocal y
        y -= 1
        cv.setFont("Helvetica", 7.5)
        cv.drawString(L+3, y-10, q1)
        if q2: cv.drawString(L+3, y-19, q2)
        cv.setFont("Helvetica-Bold", 8)
        cv.drawString(R-44, y-10, "YES / NO")
        drop = 28 if q2 else 18
        y -= drop; hl(y)

    yn_row("(A) Do you have any physical defect or infirmity")
    yn_row("(B) Have you been convicted or have a prosecution pending for any motoring offence",
           "or has your license been suspended or endorsed?")
    yn_row("(C) Have you been refused or declined motor insurance or increased premiums",
           "or terms imposed?")

    y -= 1
    cv.setFont("Helvetica", 7.5)
    cv.drawString(L+3, y-10, "If Answer yes to any of the above please give details :")
    cv.line(270, y-11, R-3, y-11)
    y -= 16; hl(y)

    y -= 1
    cv.setFont("Helvetica", 7.5)
    cv.drawString(L+3, y-10, "Purpose For which the vehicle is to be used")
    cv.setFont("Helvetica-Bold", 8)
    cv.drawString(R-95, y-10, "SDP / Private Hire")
    y -= 16; hl(y)

    legal = ("I hereby warrant the truth of the above statements and I declare that I have withheld no information "
             "whatsoever which might tend in a way to increase the risk of the insurers or influence the acceptance "
             "of the proposal. I agree that this proposal shall be the basis of the contract between me and the "
             "insurers and I further agree to be bound by the terms and conditions and exceptions of the policy, "
             "which I have the opportunity to see and read. I further declare that my occupation and personal details "
             "and driving do not render me ineligible to hire.")
    y -= 2; cv.setFont("Helvetica", 7)
    for ln in simpleSplit(legal, "Helvetica", 7, BW - 6):
        cv.drawString(L+3, y-8, ln); y -= 8
    y -= 3; hl(y)

    # ── HIRE PAYMENT / METHOD OF PAYMENT ──────
    MID = L + int(BW * 0.55)
    ph_top = y
    # headers
    cv.setFillColorRGB(0.78, 0.78, 0.78)
    cv.rect(L, ph_top-13, MID-L, 13, fill=1, stroke=1)
    cv.rect(MID, ph_top-13, R-MID, 13, fill=1, stroke=1)
    cv.setFillColorRGB(0, 0, 0)
    cv.setFont("Helvetica-Bold", 8)
    cv.drawCentredString((L+MID)//2, ph_top-9, "HIRE PAYMENT")
    cv.drawCentredString((MID+R)//2, ph_top-9, "METHOD OF PAYMENT")
    ph_top -= 13

    PH = 115  # block height
    vl(MID, ph_top, ph_top - PH)
    hl(ph_top - PH)

    lx, ly = L+3, ph_top
    cv.setFont("Helvetica", 7.5)
    cv.drawString(lx, ly-10, "The Rental of \u00a3")
    cv.setFont("Helvetica-Bold", 8); cv.drawString(lx+56, ly-10, data["rent"])
    cv.setFont("Helvetica", 7.5); cv.drawString(lx+85, ly-10, "Per week at the prevailing rate")
    cv.drawString(lx, ly-19, "multiplied by the number of weeks of hire / rental")
    cv.drawString(lx, ly-29, "on termination of the hire / renatl the hirer will pay the lessor an excess mileage")
    cv.drawString(lx, ly-38, "charge at the rate of")
    cv.setFont("Helvetica-Bold", 8); cv.drawString(lx+80, ly-38, data["rate"])
    cv.setFont("Helvetica", 7.5); cv.drawString(lx+105, ly-38, "Pence per mile. 4000 / 5000 per month")
    cv.drawString(lx, ly-47, "Mxiumum hire under this agreement shall be")
    cv.setFont("Helvetica-Bold", 7.5); cv.drawString(lx, ly-56, "THIS IS BASED ON THE MAXIMUM HIRE PERIOD")
    cv.setFillColorRGB(0.8, 0, 0); cv.setFont("Helvetica-Bold", 8)
    cv.drawString(lx+155, ly-62, "ROAD SIDE RECOVERY")
    cv.drawString(lx+165, ly-71, "IS NOT INCLUDED")
    cv.drawString(lx+155, ly-82, "TYRE MANINTENANCE")
    cv.drawString(lx+162, ly-91, "IS NOT INCLUDED")
    cv.setFillColorRGB(0, 0, 0); cv.setFont("Helvetica-Bold", 7.5)
    cv.drawString(lx, ly-65, "Deposit Paid \u00a3")
    cv.setFont("Helvetica", 7.5); cv.drawString(lx+55, ly-65, data["deposit"])
    cv.setFont("Helvetica-Bold", 7)
    cv.drawString(lx, ly-76, "I ACCEPT AND AGREE THAT THE FINANCIAL DETAILS")
    cv.drawString(lx, ly-84, "ABOVE HERE HAVE BEEN COMPLETED PRIOR TO MY")
    cv.drawString(lx, ly-92, "SIGNATURE.")
    cv.setFont("Helvetica", 7)
    cv.drawString(lx, ly-100, "I FURTHER ACCEPT THE ABOVE CHARGES ARE MY RESPONSIBILITY AT ALL TIMES")
    cv.setFont("Helvetica-Bold", 8)
    cv.drawString(lx, ly-110, "SIGNED X:")
    cv.line(lx+42, ly-111, MID-5, ly-111)

    rx, ry = MID+4, ph_top
    cv.setFont("Helvetica", 7.5)
    cv.drawString(rx, ry-10, "Method of Payment: CASH")
    cv.drawString(rx, ry-19, "CHEQUE BANK TRANSFER")
    cv.drawString(rx, ry-28, "*delete as necessary")
    cv.setFont("Helvetica-Bold", 8)
    cv.drawString(rx, ry-39, "Please make cheque payable")
    cv.drawString(rx, ry-48, "to: FA-IBI LTD")
    cv.drawString(rx, ry-57, "ACC: 843605086")
    cv.drawString(rx, ry-66, "SORT CODE: 20-42-73")
    cv.setFont("Helvetica", 7.5)
    cv.drawString(rx, ry-76, "Please set standing order to")
    cv.drawString(rx, ry-85, "avoid any late payment penalty.")
    cv.drawString(rx, ry-94, "Late payment surcharge is \u00a310/ day.")

    y = ph_top - PH

    # ── HIRE PERIOD ───────────────────────────
    y = grey_bar(y, 13, "HIRE PERIOD", 8); hl(y)

    def hp_row(label, val="", time_label="Time:"):
        nonlocal y
        y -= 1
        cv.setFont("Helvetica", 8)
        cv.drawString(L+3, y-10, label)
        cv.setFont("Helvetica", 8.5)
        cv.drawString(L+3+len(label)*4.4, y-10, val)
        cv.line(L+3+len(label)*4.4-2, y-11, 310, y-11)
        cv.setFont("Helvetica", 8)
        cv.drawString(315, y-10, time_label)
        y -= 16; hl(y)

    hp_row("Date Hire Start:", data["start_date"])
    hp_row("Expected Date of Vehicle Return:", data["expected_return"])
    hp_row("Actual Date of Vehicle Return:")
    y -= 1; cv.setFont("Helvetica", 8)
    cv.drawString(L+3, y-10, "Extention Of Hiring Period Time And Date:")
    cv.line(220, y-11, R-3, y-11)
    y -= 16; hl(y)

    # ── HIRE VEHICLE DETAILS ──────────────────
    y = grey_bar(y, 13, "HIRE VEHICLE DETAILS", 8); hl(y)
    C2V = L + BW//3; C3V = L + 2*BW//3
    vl(C2V, y, y-20); vl(C3V, y, y-20)

    y -= 1
    cv.setFont("Helvetica-Bold", 8); cv.drawString(L+3, y-13, "Make:")
    cv.setFont("Helvetica", 8.5); cv.drawString(L+28, y-13, data["car_make"])
    cv.line(L+26, y-14, C2V-4, y-14)
    cv.setFont("Helvetica-Bold", 8); cv.drawString(C2V+3, y-13, "REG No:")
    cv.setFont("Helvetica", 8.5); cv.drawString(C2V+34, y-13, data["registration"])
    cv.line(C2V+32, y-14, C3V-4, y-14)
    cv.setFont("Helvetica-Bold", 8); cv.drawString(C3V+3, y-13, "Model:")
    cv.setFont("Helvetica", 8.5); cv.drawString(C3V+30, y-13, data["car_model"])
    cv.line(C3V+28, y-14, R-3, y-14)
    y -= 20; hl(y)

    y -= 1
    vl(C2V, y, y-24)
    cv.setFont("Helvetica", 8)
    cv.drawString(L+3, y-10, "Tools: "); cv.setFont("Helvetica-Bold", 8); cv.drawString(L+26, y-10, "YES / NO")
    cv.setFont("Helvetica", 8); cv.drawString(C2V+3, y-10, "Spare: "); cv.setFont("Helvetica-Bold", 8); cv.drawString(C2V+26, y-10, "YES / NO")
    cv.setFont("Helvetica", 7.5)
    cv.drawString(L+3, y-18, "Mileage Out: ......................................................")
    cv.drawString(C2V+3, y-18, "Mileage In: ...........................................")
    y -= 24; hl(y)

    # ── Signatures ────────────────────────────
    y -= 3
    cv.setFont("Helvetica-Bold", 9)
    cv.drawString(L+3, y-14, "Hirers Signature X :")
    cv.line(L+90, y-15, 320, y-15)
    cv.drawString(325, y-14, "Owners Signature X :")
    cv.line(420, y-15, R-3, y-15)
    y -= 22; hl(y)
    cv.setFont("Helvetica-Bold", 9)
    cv.drawString(L+3, y-14, "Date:")
    cv.line(L+30, y-15, 200, y-15)
    y -= 18; hl(y)

    cv.setFont("Helvetica", 10); cv.drawCentredString(W/2, 36, "1")

    # ══════════════════════════════════════════
    #  PAGE 2 — TERMS AND CONDITIONS
    # ══════════════════════════════════════════
    cv.showPage()
    y = H - 20
    cv.rect(L, 30, BW, H - 50, stroke=1, fill=0)

    # Title
    cv.setFont("Helvetica-Bold", 14)
    cv.drawCentredString(W/2, y-2, "TERMS AND CONDITIONS OF FA-IBI LTD")
    y -= 18; hl(y)

    # Contract / Car Reg row
    vl(W//2, y, y-14)
    cv.setFillColorRGB(0.88, 0.88, 0.88)
    cv.rect(L, y-14, BW, 14, fill=1, stroke=0)
    hl(y); hl(y-14)
    cv.setFillColorRGB(0, 0, 0)
    cv.setFont("Helvetica-Bold", 8.5)
    cv.drawString(L+3, y-10, "CONTRACT NUMBER:")
    cv.setFont("Helvetica", 8.5)
    cv.drawString(L+100, y-10, data["contract_no"])
    cv.setFont("Helvetica-Bold", 8.5)
    cv.drawString(W//2+3, y-10, "CAR REG:")
    cv.setFont("Helvetica", 8.5)
    cv.drawString(W//2+50, y-10, data["registration"])
    y -= 14

    # Definitions
    y -= 2
    cv.setFont("Helvetica-Bold", 8.5)
    cv.drawString(L+3, y-10, "Hirer means the person or entity which contracts to hire a Vehicle")
    cv.drawString(310, y-10, "Lessor means the hire company FA-IBI LTD")
    y -= 14; hl(y)

    # Two-column terms
    CM = (L + R) // 2
    vl(CM, y, 48)
    CW = CM - L - 5
    FS = 6.8

    LEFT_TERMS = (
        "1. At no time the vehicle be used, operated or driven. (a) For the damage of persons for hire or reward "
        "whether Express or implied, (unless approval has been agreed). By a person who is less than 22 years of age "
        "or more then 65 years of age (unless such approval has been agreed) or By any person who has given to the "
        "lessor any false particulars. (c) Knowingly for any unlawful purpose. (d) To propel or tow any vehicle or "
        "trailer. (f) By any person except the hire unless the lessor provides Permission beforehand. (e) For racing, "
        "reliability trials speed testing or driving tuition. (g) To carry a greater number of passengers and or more "
        "baggage Than is recommended by the manufacturer. (h) After the expiry of the period of hire of as stated "
        "overleaf. (I) Outside the British isles except with prior notice agreed with the lessor. (J) The vehicle must "
        "not be driven in manner which would render void any insurance and/or other contract of insurance or in "
        "contravention of any road or traffic act or contravention of road use regulations, nor must it be driven in "
        "the event of mechanical, electrical or structural failure which might cause further damage. 2. The hirer will "
        "return the vehicle to the lessor's address shown together with all tyres, tools, accessories and equipment in "
        "the condition as when received (ordinary wear and tear excepted). 3. The hirer shall not use the vehicle if "
        "any damage or fault shall arise so as to make the vehicle unroadworthy or liable to cause damage to any "
        "person or property until such damage or fault has been repaired and corrected. In the event of any such "
        "fault arising which can be repaired at a total cost of less than \u00a310, the hirer shall either return the "
        "vehicle to the lessor or authorise the carrying out of such repair by a reputable and properly qualified "
        "motor repairer. Authorisation for expenditure in excess of \u00a325 must be obtained from the lessor prior "
        "to commencement of the repair. The hire shall not without the lessor's consent permit or authorised repairs "
        "to the vehicle at the total cost exceeding \u00a325 or suffer any lien to be placed upon the vehicle and "
        "shall pay for and all charges in connection with any such unauthorised repairs. The hirer shall inform the "
        "lessor as soon as reasonable possible of any fault to the vehicle requiring repair or of the carrying out of "
        "any repair to the vehicle as aforesaid. The hirer is also responsible for safety checks of the vehicle, In "
        "particular water, oil level and tyres, while the hirer is in custody out of any vehicle. Any damages "
        "resulting from failure to adhere to above will be charge back to the hirer. 4. in case of accident the hirer "
        "is responsible for the cost of repair of the car whether the hirer is responsible for the cause of accident "
        "or not.in case of vehicle write off, hirer shall pay the total value of the vehicle less salvage value to "
        "lesser and cannot claim the salvage vehicle. the hirer can recover the cost from the third party insurance "
        "in case of non fault the cost of vehicle damage and depreciation will be determine by the independent "
        "engineer report from a reputed company and hirer is responsible to pay according to that report the hirer is "
        "authorising the insurance company to issue the payment related to vehicle repair or write off value to the "
        "lessor. 5. The hirer shall be liable as owner of the vehicle in respect of, (a) Any of the following "
        "offences which may be committed in relation to that vehicle when it is stationary and when a penalty notice "
        "is issued being on a road during the hours of darkness without the light or reflections required by law, or "
        "being left or park, or being loaded or unloaded and the non-payment of charge made at a street parking place "
        "and/or pay & displays. (b) Any fixed penalty offence including congestion charge committed in respect of "
        "that vehicle under part iii and section 66 of the road traffic act 1988"
    )

    RIGHT_TERMS = (
        "and schedule 2 to the road traffic regulation 2000 as amended, replaced or extended by any subsequent "
        "legislation or orders any such offence committed under the equivalent applicable to Scotland Northern Ireland "
        "or other parts of the British Isles upon which the vehicle is being used (c) Any access charge which may be "
        "incurred in respect of that vehicle in pursuance of an order under section 45 and 46 of the road Traffic "
        "Act1984, as amended, replaced or extended by any subsequent legislation or orders and under the equivalent "
        "legislation applicable to Scotland, Northern Ireland or other parts of the British Isles upon which the "
        "vehicle is being used. (d) Any financial penalty or charge which may be demanded by a third party as a "
        "result of the vehicle having been parked or left upon land which is not a public road. "
        "6.The hirer shall immediately report to the lessor any accident which the vehicle is involved in and shall "
        "deliver to the lessor every process, pleading or notice on paper of any kind received by the hirer or the "
        "vehicle relating to any claim or proceeding connected with any such accident or event involving the vehicle. "
        "Neither the hirer nor any driver of the vehicle shall aid or albeit the assertion of any such claim or "
        "proceeding and co-operate with the lessor and its insurer in investigating and defending the same. "
        "7. The hirer shall defend and indemnify, the lessor from and against any and all losses, liabilities, "
        "damages, injuries, claims, demands cost and expenses arising out of connected with the possession or use of "
        "the vehicle during the rental term (except those covered by the insurance providing here under by the "
        "lessor) and caused by negligence and non-observance of the agreement on the part of the hirer, his driver, "
        "agents or employees including but not limited to any and claims liabilities third parties arising out of the "
        "disposal of the vehicle by government authority for illegal or improper use of said vehicle. "
        "8. Notwithstanding the period of hire shown overleaf. (a) The lessor may demand the return of the vehicle "
        "at any time so long as at all material times the lessor is aware or becomes aware of any activity on the "
        "part of the lessor in relation to the vehicle which could reasonably lead the lessor to believe that the "
        "hirer is acting or likely to act in a manner prejudicial to the preservation, maintenance or good upkeep of "
        "the vehicle. (b) If the vehicle is not returned within the minimum hire period and/or in accordance with "
        "paragraph (a) of this clause the hirer will pay the Lessor hire charges at the lessor's published tariffs "
        "(which can be inspected at the lessor's premises) for such period as the vehicle shall be wrongfully "
        "retained by the hirer, his servant and/or agents, including any administration charges incurred. "
        "9. The hirer shall pay to the lessor, hire charges and/or other such charges that become due under this "
        "agreement, by one single Instalment within one month beginning with the date of this agreement. "
        "10. Any addition to or alternative of the terms and conditions of agreement shall be null and void unless "
        "agreed upon in writing by by the lessor and hirer. "
        "11. The hirer agrees to compensate the lessor in full for any loss in case of fire or theft. "
        "12. Minimum hire period is 4 weeks. "
        "13. The hirer may terminate the hire of the vehicle by giving 2 weeks notice and returning the vehicle to "
        "the lessor. "
        "14. BULBS AND TYRES are hirer responsablity . "
        "15. I(Hirer) fully agree to check OIL and Water on daily basis. "
        "16. I(Hirer) give my consent to share my details with third party "
        "17. I (Hirer) give my consent to transfer all liabilities and penalty charges including Congestion Charge "
        "on my name.respect of that vehicle under part iii and section 66 of the road traffic act 1988"
    )

    def draw_block(text, x, start_y, col_w, font="Helvetica", fs=FS):
        ty = start_y
        cv.setFont(font, fs)
        for ln in simpleSplit(text, font, fs, col_w):
            if ty < 52: break
            cv.drawString(x, ty, ln); ty -= fs + 1.2
        return ty

    content_y = y - 3
    draw_block(LEFT_TERMS,  L+3,   content_y, CW)
    draw_block(RIGHT_TERMS, CM+4,  content_y, CW)

    # Footer signatures
    hl(48)
    cv.setFont("Helvetica-Bold", 9)
    cv.drawString(L+3, 40, "Hirers Signature X :")
    cv.line(L+90, 38, 220, 38)
    cv.drawString(225, 40, "Date:")
    cv.line(250, 38, 370, 38)
    cv.drawString(375, 40, "Owners Signature X :")
    cv.line(465, 38, R-3, 38)
    cv.setFont("Helvetica", 10); cv.drawCentredString(W/2, 32, "2")

    cv.save(); buf.seek(0); return buf.getvalue()

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
    text-align:center;padding:10px 0;font-size:14px;color:#888;
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
    # Store submitted contract data to survive reruns
    pending_contract=None,
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
                                    type=["jpg","png","jpeg"], key=f"uploader_{ctx}")
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
        opts = ["-- Manual Entry --"] + [f"{v['reg']} ({v['model']})" for v in FLEET_VEHICLES]
        cur = "-- Manual Entry --"
        if st.session_state.sel_reg:
            hit = [o for o in opts if o.startswith(st.session_state.sel_reg)]
            if hit: cur = hit[0]
        chosen = st.selectbox("🚗 Select Vehicle", opts, index=opts.index(cur), key=f"fleet_{ctx}")
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
#  GENERATE CONTRACT from pending data
#  (decoupled from form submission to survive reruns)
# ─────────────────────────────────────────────
if st.session_state.pending_contract:
    try:
        pdf = generate_contract(st.session_state.pending_contract)
        st.session_state.contract_pdf = pdf
        st.session_state.contract_no  = st.session_state.pending_contract["contract_no"]
    except Exception as e:
        import traceback
        st.error(f"Contract PDF error: {e}\n{traceback.format_exc()}")
    finally:
        st.session_state.pending_contract = None

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

    if st.session_state.perm_pdf:
        st.download_button("📥 Download Permission Letter PDF",
                           data=st.session_state.perm_pdf,
                           file_name="Permission_Letter.pdf",
                           mime="application/pdf", key="dl_perm_top")

    with st.form("perm_form"):
        c1, c2 = st.columns(2)
        with c1:
            p_date = st.date_input("Document Date", datetime.now(), format="DD/MM/YYYY")
            p_ins  = st.text_input("Insurance Policy No", "HAVFL-000211")
            p_reg  = st.text_input("Vehicle Registration", value=st.session_state.sel_reg)
            p_mod  = st.text_input("Make & Model",
                        value=f"{st.session_state.sel_make} {st.session_state.sel_model}".strip())
        with c2:
            p_name  = st.text_input("Driver Full Name",   value=st.session_state.ocr_name)
            p_lic   = st.text_input("Driving Licence No", value=st.session_state.ocr_licence)
            p_start = st.date_input("Hire Start Date", datetime.now(), format="DD/MM/YYYY")
            p_end   = st.date_input("Hire End Date",   datetime.now(), format="DD/MM/YYYY")
        p_addr = st.text_area("Driver Address", value=st.session_state.ocr_address)
        go_p = st.form_submit_button("🖨️ Generate Permission Letter PDF")

    if go_p:
        try:
            st.session_state.perm_pdf = generate_permission_letter({
                "date": p_date.strftime("%d/%m/%Y"), "insurance_policy": p_ins,
                "registration": format_uk_reg(p_reg), "make_model": p_mod.upper(),
                "driver_name": p_name.upper(), "address": p_addr.upper(),
                "license_no": p_lic.upper(),
                "start_date": p_start.strftime("%d/%m/%Y"), "end_date": p_end.strftime("%d/%m/%Y"),
            })
            st.success("✅ Ready!")
        except Exception as e:
            st.error(f"Error: {e}")

    if st.session_state.perm_pdf:
        st.download_button("📥 Download Permission Letter PDF",
                           data=st.session_state.perm_pdf,
                           file_name="Permission_Letter.pdf",
                           mime="application/pdf", key="dl_perm_bottom")

# ══════════════════════════════════
#  TAB 2 — CONTRACT
# ══════════════════════════════════
with tab2:
    render_automation("tab2")
    st.markdown("---")

    # Always show download if available
    if st.session_state.contract_pdf:
        st.success("✅ Contract ready!")
        st.download_button("📥 Download Contract PDF",
                           data=st.session_state.contract_pdf,
                           file_name=f"FA_IBI_Contract_{st.session_state.contract_no}.pdf",
                           mime="application/pdf", key="dl_contract_top")
        st.markdown("---")

    go_c = False
    with st.form("contract_form"):
        st.subheader("Hirer Details")
        cc1, cc2 = st.columns(2)
        with cc1:
            c_no   = st.text_input("Contract Number", "1608/DRIVER/REG/2026")
            c_name = st.text_input("Full Name",    value=st.session_state.ocr_name)
            c_addr = st.text_area("Address",       value=st.session_state.ocr_address)
            c_post = st.text_input("Postcode",     value=st.session_state.ocr_postcode)
            c_dob  = st.text_input("Date of Birth (DD/MM/YYYY)",
                                   value=normalize_date(st.session_state.ocr_dob),
                                   placeholder="DD/MM/YYYY")
        with cc2:
            c_date = st.date_input("Contract Date", datetime.now(), format="DD/MM/YYYY")
            c_lic  = st.text_input("Licence No",  value=st.session_state.ocr_licence)
            c_exp  = st.text_input("Date of Expiry (DD/MM/YYYY)",
                                   value=normalize_date(st.session_state.ocr_expiry),
                                   placeholder="DD/MM/YYYY")
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
        with pt1: c_st  = st.date_input("Hire Start",       datetime.now(), format="DD/MM/YYYY")
        with pt2: c_ret = st.date_input("Expected Return",   datetime.now(), format="DD/MM/YYYY")

        st.markdown("---"); st.subheader("Vehicle")
        pv1, pv2, pv3 = st.columns(3)
        with pv1: c_mk  = st.text_input("Make",  value=st.session_state.sel_make)
        with pv2: c_rv  = st.text_input("Reg",   value=st.session_state.sel_reg)
        with pv3: c_mv  = st.text_input("Model", value=st.session_state.sel_model)

        go_c = st.form_submit_button("🖨️ Generate 2-Page Contract PDF", type="primary")

    # Store data in session state on submit — decoupled from generation
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
        st.rerun()  # rerun triggers the generate block at the top of the file

st.markdown('<div class="vch-footer">Powered By '
            '<a href="https://virtualcarhire.pages.dev/" target="_blank">Virtual Car Hire</a>'
            '</div>', unsafe_allow_html=True)
