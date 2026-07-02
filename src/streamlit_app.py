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
    s = re.sub(r"\b[3-8][ABC58]?\.?\s*", " ", s) # Removes common OCR field marks like 8. or 4b.
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
    # Fixed fallback context stripping filters to grab precise 16-18 character variants
    m = re.search(r"\b([A-Z9]{5}\d{6}[A-Z9]{2}[A-Z0-9]{2,5})\b", c)
    return m.group(1) if m else ""

# ─────────────────────────────────────────────
#  OCR 
# ─────────────────────────────────────────────
def run_ocr(uploaded_file) -> str:
    img = Image.open(uploaded_file).convert("RGB")
    w, h = img.size
    if max(w, h) < 1800:
        scale = 1800 / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    img = ImageOps.grayscale(img)
    img = ImageEnhance.Contrast(img).enhance(2.5) # Slight bump to maximize clear text
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
    return pytesseract.image_to_string(img, config=r"--oem 3 --psm 4") # Config psm 4 reads better line structures

STREET_TYPES = ["ROAD","STREET","AVENUE","LANE","DRIVE","CLOSE","WAY","GARDENS",
                "CRESCENT","PLACE","COURT","GROVE","TERRACE","WALK","SQUARE","HILL",
                "VALE","VIEW","RISE","MEWS","PARADE","AVENUE","BOULEVARD","CIRCUS"]

def parse_licence(raw: str) -> dict:
    blob = " " + re.sub(r"\s+", " ", raw.upper()) + " "

    # Surname
    surname = clean_name(_grab(blob, [r"1\.", r"[Il]\."], [r"2\."]))
    if not surname:
        m = re.search(r"\b(?:SURNAME|LAST\s+NAME)[:\s]+([A-Z][A-Z\s'\-]{1,40}?)(?=\s+(?:2\.|FIRST|GIVEN|FORENAME|3\.))", blob)
        if m: surname = clean_name(m.group(1))

    # Forename
    raw_2 = _grab(blob, [r"2\."], [r"3\."])
    raw_2 = re.sub(r"\b\d[A-Ca-c]?\.?\s*", " ", raw_2)
    forename = clean_name(raw_2)

    # DOB
    raw_3 = _grab(blob, [r"3\."], [r"4[Aa]\.?", r"4\b"])
    dob = first_date(raw_3)
    if not dob:
        m = re.search(r"(?:D\.?O\.?B|DATE\s+OF\s+BIRTH|BIRTH)[:\s]+(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})", blob)
        if m: dob = normalize_date(m.group(1))

    # Expiry
    raw_4b = _grab(blob, [r"4[Bb][\.\s]?", r"4[Bb]\b"], [r"5\.", r"5\b", r"7\.", r"7\b", r"8\.", r"8\b"])
    expiry = first_date(raw_4b)

    # Licence Number Match Fix
    licence = ""
    # Look globally for standard 16-character sequence format strings
    lic_match = re.search(r"\b([A-Z9]{5}\d{6}[A-Z9]{2}[A-Z0-9]{3,5})\b", blob.replace(" ", ""))
    if lic_match:
        licence = lic_match.group(1)[:16]
    if not licence:
        raw_5 = _grab(blob, [r"5\."], [r"[678]\.", r"7\b", r"8\b"])
        licence = validate_uk_licence(raw_5)

    # Address Parsing Corrective Filters
    raw_8 = _grab(blob, [r"8\."], [r"9\."])
    lines = [l.strip() for l in raw.split("\n") if l.strip()]
    pc_re = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b", re.I)

    if not raw_8:
        for idx, line in enumerate(lines):
            if pc_re.search(line.upper()):
                window = lines[max(0, idx - 3): idx + 1]
                addr_lines = []
                for wl in window:
                    u = wl.upper().strip()
                    if any(x in u for x in ["1.", "2.", "3.", "4B.", "5."]): continue
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
#  PDF — CONTRACT (Cleaned Fields Output)
# ─────────────────────────────────────────────
def generate_contract(data: dict) -> bytes:
    buf = io.BytesIO()
    cv = canvas.Canvas(buf, pagesize=letter, pageCompression=1)
    W, H = 612, 792
    L, R = 28, 584
    BW = R - L   

    def hl(y): cv.line(L, y, R, y)
    def vl(x, y1, y2): cv.line(x, y1, x, y2)
    def grey_bar(y, h, txt, fs=9):
        cv.setFillColorRGB(0.78, 0.78, 0.78)
        cv.rect(L, y - h, BW, h, fill=1, stroke=1)
        cv.setFillColorRGB(0, 0, 0)
        cv.setFont("Helvetica-Bold", fs)
        cv.drawCentredString(W/2, y - h + (h - fs) / 2 + 1, txt)
        return y - h

    # PAGE 1
    y = H - 16
    cv.rect(L, 30, BW, H - 46, stroke=1, fill=0)

    cv.setFont("Helvetica-Bold", 20)
    cv.drawCentredString(W/2, y - 2, "FA-IBI LTD")
    y -= 20; hl(y)

    y -= 9
    cv.setFont("Helvetica", 7.5)
    cv.drawString(L+3, y, "50 SALISBURY ROAD HOUNSLOW TW4 6JQ")
    cv.drawString(255, y, "PH: 07861838162")
    cv.setFillColorRGB(0, 0, 0.8)
    cv.drawString(392, y, "Email:info@fa-ibi.co.uk")
    cv.setFillColorRGB(0, 0, 0)
    y -= 9
    cv.drawString(392, y, "Company Registration No: 8844002")
    y -= 3; hl(y)

    y -= 1
    cv.setFillColorRGB(0.88, 0.88, 0.88)
    cv.rect(L, y-14, BW, 14, fill=1, stroke=0); hl(y); hl(y-14)
    cv.setFillColorRGB(0, 0, 0)
    cv.setFont("Helvetica-Bold", 8)
    cv.drawString(L+3, y-10, "THIS CONTRACT CONTAINS 2 PAGES")
    cv.drawString(225, y-10, "CONTRACT NUMBER:")
    cv.drawString(308, y-10, data.get("contract_no", ""))
    cv.drawString(R-50, y-10, "PAGE: 1/2")
    y -= 14

    y = grey_bar(y, 16, "HIRER DETAILS", 10); hl(y)

    def labelled(y_top, h, items):
        for lbl, val, xl, xv, xe in items:
            cv.setFont("Helvetica-Bold", 8)
            cv.drawString(xl, y_top - h + 4, lbl)
            cv.setFont("Helvetica", 8.5)
            cv.drawString(xv, y_top - h + 4, str(val))
            cv.line(xv - 2, y_top - h + 2, xe, y_top - h + 2)
        hl(y_top - h)
        return y_top - h

    y -= 1
    y = labelled(y, 22, [
        ("Full Name:", data.get("driver_name", ""), L+3, L+52, 350),
        ("Date Of Birth:", data.get("dob", ""),     355, 430, R-3),
    ])
    y -= 1
    y = labelled(y, 22, [
        ("Address:", data.get("address", ""), L+3, L+42, 350),
        ("Postcode:", data.get("postcode", ""), 355, 415, R-3),
    ])
    y -= 1
    C2, C3 = L + BW//3, L + 2*BW//3
    vl(C2, y, y-22); vl(C3, y, y-22)
    y = labelled(y, 22, [
        ("License No:", data.get("license_no", ""),     L+3,   L+50,  C2-3),
        ("Issuing Authority:", data.get("issuing_authority", ""), C2+3, C2+82, C3-3),
        ("Date Of Expiry:", data.get("expiry_date", ""), C3+3, C3+70, R-3),
    ])
    y -= 1
    vl(200, y, y-22)
    y = labelled(y, 22, [
        ("Ph:", data.get("phone", ""), L+3, L+20, 198),
        ("Email:", data.get("email", ""), 203, 228, R-3),
    ])

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
             "which I have the opportunity to see and read.")
    y -= 2; cv.setFont("Helvetica", 7)
    for ln in simpleSplit(legal, "Helvetica", 7, BW - 6):
        cv.drawString(L+3, y-8, ln); y -= 8
    y -= 3; hl(y)

    MID = L + int(BW * 0.55)
    ph_top = y
    cv.setFillColorRGB(0.78, 0.78, 0.78)
    cv.rect(L, ph_top-13, MID-L, 13, fill=1, stroke=1)
    cv.rect(MID, ph_top-13, R-MID, 13, fill=1, stroke=1)
    cv.setFillColorRGB(0, 0, 0)
    cv.setFont("Helvetica-Bold", 8)
    cv.drawCentredString((L+MID)//2, ph_top-9, "HIRE PAYMENT")
    cv.drawCentredString((MID+R)//2, ph_top-9, "METHOD OF PAYMENT")
    ph_top -= 13

    PH = 115  
    vl(MID, ph_top, ph_top - PH)
    hl(ph_top - PH)

    lx, ly = L+3, ph_top
    cv.setFont("Helvetica", 7.5)
    cv.drawString(lx, ly-10, "The Rental of \u00a3")
    cv.setFont("Helvetica-Bold", 8); cv.drawString(lx+56, ly-10, data.get("rent", ""))
    cv.setFont("Helvetica", 7.5); cv.drawString(lx+85, ly-10, "Per week at the prevailing rate")
    cv.drawString(lx, ly-19, "multiplied by the number of weeks of hire / rental")
    cv.drawString(lx, ly-29, "on termination of the hire charge at the rate of")
    cv.setFont("Helvetica-Bold", 8); cv.drawString(lx+80, ly-38, data.get("rate", ""))
    cv.setFont("Helvetica", 7.5); cv.drawString(lx+105, ly-38, "Pence per mile.")
    cv.drawString(lx, ly-47, "Deposit Paid \u00a3")
    cv.setFont("Helvetica-Bold", 8); cv.drawString(lx+55, ly-47, data.get("deposit", ""))
    
    cv.setFont("Helvetica-Bold", 8)
    cv.drawString(lx, ly-110, "SIGNED X:")
    cv.line(lx+42, ly-111, MID-5, ly-111)

    rx, ry = MID+4, ph_top
    cv.setFont("Helvetica", 7.5)
    cv.drawString(rx, ry-10, "Method of Payment: CASH / BANK TRANSFER")
    cv.drawString(rx, ry-39, "Please make cheque payable to: FA-IBI LTD")
    cv.drawString(rx, ry-48, "ACC: 843605086  SORT CODE: 20-42-73")

    y = ph_top - PH

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

    hp_row("Date Hire Start:", data.get("start_date", ""))
    hp_row("Expected Date of Vehicle Return:", data.get("expected_return", ""))
    hp_row("Actual Date of Vehicle Return:")
    y -= 1; cv.setFont("Helvetica", 8)
    cv.drawString(L+3, y-10, "Extension Of Hiring Period Time And Date:")
    cv.line(220, y-11, R-3, y-11)
    y -= 16; hl(y)

    y = grey_bar(y, 13, "HIRE VEHICLE DETAILS", 8); hl(y)
    C2V = L + BW//3; C3V = L + 2*BW//3
    vl(C2V, y, y-20); vl(C3V, y, y-20)

    y -= 1
    cv.setFont("Helvetica-Bold", 8); cv.drawString(L+3, y-13, "Make:")
    cv.setFont("Helvetica", 8.5); cv.drawString(L+28, y-13, data.get("car_make", ""))
    cv.line(L+26, y-14, C2V-4, y-14)
    cv.setFont("Helvetica-Bold", 8); cv.drawString(C2V+3, y-13, "REG No:")
    cv.setFont("Helvetica", 8.5); cv.drawString(C2V+34, y-13, data.get("registration", ""))
    cv.line(C2V+32, y-14, C3V-4, y-14)
    cv.setFont("Helvetica-Bold", 8); cv.drawString(C3V+3, y-13, "Model:")
    cv.setFont("Helvetica", 8.5); cv.drawString(C3V+30, y-13, data.get("car_model", ""))
    cv.line(C3V+28, y-14, R-3, y-14)
    y -= 20; hl(y)

    y -= 3
    cv.setFont("Helvetica-Bold", 9)
    cv.drawString(L+3, y-14, "Hirers Signature X :")
    cv.line(L+90, y-15, 320, y-15)
    cv.drawString(325, y-14, "Owners Signature X :")
    cv.line(420, y-15, R-3, y-15)
    y -= 22; hl(y)

    cv.setFont("Helvetica", 10); cv.drawCentredString(W/2, 36, "1")

    # PAGE 2 
    cv.showPage()
    y = H - 20
    cv.rect(L, 30, BW, H - 50, stroke=1, fill=0)

    cv.setFont("Helvetica-Bold", 14)
    cv.drawCentredString(W/2, y-2, "TERMS AND CONDITIONS OF FA-IBI LTD")
    y -= 18; hl(y)

    vl(W//2, y, y-14)
    cv.setFillColorRGB(0.88, 0.88, 0.88)
    cv.rect(L, y-14, BW, 14, fill=1, stroke=0)
    hl(y); hl(y-14)
    cv.setFillColorRGB(0, 0, 0)
    cv.setFont("Helvetica-Bold", 8.5)
    cv.drawString(L+3, y-10, "CONTRACT NUMBER:")
    cv.setFont("Helvetica", 8.5)
    cv.drawString(L+100, y-10, data.get("contract_no", ""))
    cv.setFont("Helvetica-Bold", 8.5)
    cv.drawString(W//2+3, y-10, "CAR REG:")
    cv.setFont("Helvetica", 8.5)
    cv.drawString(W//2+50, y-10, data.get("registration", ""))
    y -= 14

    cv.setFont("Helvetica", 10); cv.drawCentredString(W/2, 32, "2")
    cv.save(); buf.seek(0); return buf.getvalue()

# ─────────────────────────────────────────────
#  STREAMLIT UI
# ─────────────────────────────────────────────
st.set_page_config(page_title="FA-IBI Workspace", layout="centered")
st.markdown("""
<style>
#MainMenu,footer,header,[data-testid="stToolbar"]{display:none!important;}
.main .block-container{padding-top:1rem!important;max-width:100%!important;}
</style>
""", unsafe_allow_html=True)

if "authenticated" not in st.session_state: st.session_state.authenticated = False
if st.query_params.get("session") == "active": st.session_state.authenticated = True
if not st.session_state.authenticated:
    code = st.text_input("System Access", type="password", placeholder="Enter key…")
    if code == st.secrets.get("ACCESS_KEY", ""):
        st.session_state.authenticated = True
        st.query_params["session"] = "active"; st.rerun()
    else: st.stop()

# Unified Global State Variables Configuration
for k, v in dict(
    ocr_name="", ocr_licence="", ocr_address="", ocr_postcode="",
    ocr_dob="", ocr_expiry="", last_scan_id="",
    sel_reg="", sel_make="", sel_model="",
    scan_msg="", fleet_msg="",
    perm_pdf=None, contract_pdf=None, contract_no="",
    pending_contract=None,
).items():
    if k not in st.session_state: st.session_state[k] = v

st.title("FA-IBI Master Document Workspace")

def render_automation(ctx):
    st.markdown("#### 🎛️ Data Automation")
    if st.session_state.scan_msg:  st.success(st.session_state.scan_msg)
    if st.session_state.fleet_msg: st.info(st.session_state.fleet_msg)
    col_scan, col_fleet = st.columns(2)

    with col_scan:
        uploaded = st.file_uploader("📷 Driver's Licence Scanner", type=["jpg","png","jpeg"], key=f"uploader_{ctx}")
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

if st.session_state.pending_contract:
    try:
        pdf = generate_contract(st.session_state.pending_contract)
        st.session_state.contract_pdf = pdf
        st.session_state.contract_no  = st.session_state.pending_contract["contract_no"]
    except Exception as e:
        st.error(f"Contract Generation Error: {e}")
    finally:
        st.session_state.pending_contract = None

tab1, tab2 = st.tabs(["📝 Permission Letter", "📜 Contract Generator"])

with tab1:
    render_automation("tab1")
    st.markdown("---")
    with st.form("perm_form"):
        c1, c2 = st.columns(2)
        with c1:
            p_date = st.date_input("Document Date", datetime.now(), format="DD/MM/YYYY")
            p_ins  = st.text_input("Insurance Policy No", "HAVFL-000211")
            p_reg  = st.text_input("Vehicle Registration", value=st.session_state.sel_reg)
            p_mod  = st.text_input("Make & Model", value=f"{st.session_state.sel_make} {st.session_state.sel_model}".strip())
        with c2:
            p_name  = st.text_input("Driver Full Name",   value=st.session_state.ocr_name)
            p_lic   = st.text_input("Driving Licence No", value=st.session_state.ocr_licence)
            p_start = st.date_input("Hire Start Date", datetime.now(), format="DD/MM/YYYY")
            p_end   = st.date_input("Hire End Date",   datetime.now(), format="DD/MM/YYYY")
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
        st.download_button("📥 Download Permission Letter PDF", data=st.session_state.perm_pdf, file_name="Permission_Letter.pdf", mime="application/pdf")

with tab2:
    render_automation("tab2")
    st.markdown("---")

    if st.session_state.contract_pdf:
        st.download_button("📥 Download Contract PDF", data=st.session_state.contract_pdf, file_name=f"FA_IBI_Contract_{st.session_state.contract_no}.pdf", mime="application/pdf")

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
            c_date = st.date_input("Contract Date", datetime.now(), format="DD/MM/YYYY")
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
        with pt1: c_st  = st.date_input("Hire Start",       datetime.now(), format="DD/MM/YYYY")
        with pt2: c_ret = st.date_input("Expected Return",   datetime.now(), format="DD/MM/YYYY")

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
