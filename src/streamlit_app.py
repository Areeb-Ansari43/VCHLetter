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

try:
    from azure.core.credentials import AzureKeyCredential
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
except ImportError:
    AzureKeyCredential = None
    DocumentIntelligenceClient = None
    AnalyzeDocumentRequest = None

import base64, json
from reportlab.lib.utils import simpleSplit

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIT_LOG_FILE = os.path.join(SRC_DIR, "audit_logs.json")

def get_audit_logs():
    if not os.path.exists(AUDIT_LOG_FILE):
        return []
    try:
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def add_audit_log(event_type: str, details: str = "", doc_name: str = ""):
    logs = get_audit_logs()
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "event_type": event_type,
        "doc_name": doc_name,
        "details": details,
    }
    logs.insert(0, entry)
    try:
        with open(AUDIT_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2)
    except Exception as e:
        pass

def _find_img(base_name):
    for ext in [".jpg", ".png", ".jpeg", ".JPG", ".PNG"]:
        p = os.path.join(SRC_DIR, base_name + ext)
        if os.path.exists(p): return p
    return None

# If you have a hosted URL for your logo, paste it here (e.g. from a GitHub
# raw link or image host) and it will be used as the browser tab icon
# regardless of what files happen to be deployed alongside this script.
FAVICON_URL = "https://virtualcarhire.pages.dev/assets/favicon-32x32.png?v=3"

fav_path = FAVICON_URL or _find_img("Screenshot_2026-06-09_230035") or "🚗"

# ─────────────────────────────────────────────
#  STREAMLIT CONFIGURATION & BRAND HIDING
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="FA-IBI Workspace",
    page_icon=fav_path,
    layout="centered"
)

# ─────────────────────────────────────────────
#  BROWSER TAB TITLE — Streamlit appends " · Streamlit" to whatever
#  page_title is set above; this forces the tab back to a clean title.
# ─────────────────────────────────────────────
import streamlit.components.v1 as components

# ─────────────────────────────────────────────
#  BROWSER TAB TITLE — Streamlit appends " · Streamlit" to whatever
#  page_title is set above. st.markdown() never actually runs <script>
#  tags (Streamlit strips script execution from injected HTML), which is
#  why a markdown-based fix silently does nothing. components.html()
#  renders in a real iframe that DOES execute scripts, so we reach up to
#  the parent (top-level) document to force the tab title.
# ─────────────────────────────────────────────
components.html("""
<script>
(function() {
    const desiredTitle = "FA-IBI Workspace";
    function applyTitle() {
        try {
            if (window.parent.document.title !== desiredTitle) {
                window.parent.document.title = desiredTitle;
            }
        } catch (e) {}
    }
    applyTitle();
    try {
        const titleEl = window.parent.document.querySelector('title');
        if (titleEl) new MutationObserver(applyTitle).observe(titleEl, { childList: true });
    } catch (e) {}
    setInterval(applyTitle, 300);
})();
</script>
""", height=0, width=0)

# ─────────────────────────────────────────────
#  LINK-PREVIEW METADATA (best effort)
#  NOTE: Slack/WhatsApp/Teams/etc. generate link previews by fetching the
#  page's raw HTML with no JavaScript execution. Streamlit apps render
#  their content client-side, so tags injected here (after the JS app
#  boots) are usually invisible to those crawlers — this is a platform
#  limitation, not something fixable from inside the Python script. The
#  reliable fix is a small edge/proxy rule in front of your custom domain
#  (e.g. a Cloudflare Worker) that serves a static HTML snippet with these
#  tags to known bot user-agents while passing real visitors through to
#  Streamlit. Happy to write that Worker script if xubi.org is on
#  Cloudflare — just say the word. Leaving this block in in case your
#  hosting setup does happen to expose it.
# ─────────────────────────────────────────────
st.markdown(f"""
<meta property="og:title" content="FA-IBI Workspace" />
<meta property="og:description" content="FA-IBI LTD private hire vehicle rental — driver licence scanning, permission letters, and hire contracts generated in one place." />
<meta property="og:image" content="{FAVICON_URL}" />
<meta property="og:url" content="https://vchletter.xubi.org" />
<meta property="og:type" content="website" />
<meta name="twitter:card" content="summary" />
<meta name="twitter:title" content="FA-IBI Workspace" />
<meta name="twitter:description" content="FA-IBI LTD private hire vehicle rental — driver licence scanning, permission letters, and hire contracts generated in one place." />
<meta name="twitter:image" content="{FAVICON_URL}" />
""", unsafe_allow_html=True)

st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
[data-testid="stToolbar"] {visibility: hidden !important;}
[data-testid="stStatusWidget"] {visibility: hidden !important;}
[data-testid="stDecoration"] {visibility: hidden !important;}
.stApp { padding-bottom: 46px; }

.fa-ibi-footer {
    position: fixed;
    left: 0;
    bottom: 0;
    width: 100%;
    height: 40px;
    background-color: #0e1117;
    border-top: 1px solid #262730;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 13px;
    color: #cfcfcf;
    z-index: 2147483647;
}
.fa-ibi-footer a {
    color: #ff8c00;
    font-weight: 600;
    text-decoration: none;
}
.fa-ibi-footer a:hover { text-decoration: underline; }
</style>

<div class="fa-ibi-footer">
    Powered By <a href="https://virtualcarhire.pages.dev/" target="_blank" rel="noopener">&nbsp;Virtual Car Hire</a>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  AUTO-DISMISSING NOTIFICATIONS
#  Renders a Streamlit-alert-styled banner that visually fades out and
#  collapses on its own after `seconds` (default 10s) using a pure CSS
#  animation, so callers don't need to manage timers/reruns.
# ─────────────────────────────────────────────
def notify(message: str, kind: str = "success", seconds: int = 10):
    palette = {
        "success": ("#1e4620", "#3dd56d", "#d4f7d4", "✅"),
        "info":    ("#1e3a5c", "#3d9bd5", "#d4e9f7", "ℹ️"),
        "warning": ("#5c4a1e", "#d5a83d", "#f7ecd4", "⚠️"),
        "error":   ("#5c1e1e", "#d53d3d", "#f7d4d4", "🚫"),
    }
    bg, border, fg, icon = palette.get(kind, palette["success"])
    uid = f"fa-ibi-toast-{kind}-{abs(hash(message)) % 100000}"
    st.markdown(f"""
    <style>
    @keyframes {uid}-fade {{
        0%   {{ opacity: 1; max-height: 200px; margin-bottom: 1rem; padding: 0.75rem 1rem; }}
        85%  {{ opacity: 1; max-height: 200px; margin-bottom: 1rem; padding: 0.75rem 1rem; }}
        100% {{ opacity: 0; max-height: 0;   margin-bottom: 0;    padding: 0 1rem; }}
    }}
    #{uid} {{
        background-color: {bg};
        border: 1px solid {border};
        color: {fg};
        border-radius: 8px;
        overflow: hidden;
        font-size: 14px;
        line-height: 1.4;
        animation: {uid}-fade {seconds}s ease forwards;
    }}
    </style>
    <div id="{uid}">{icon} {message}</div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  REAL COOKIE-BASED AUTH (no URL params, no full-page reload hacks)
# ─────────────────────────────────────────────
AUTH_COOKIE_NAME = "fa_ibi_auth"
AUTH_COOKIE_DAYS = 30

if stx is not None:
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


def clean_document_name(name: str, fallback: str) -> str:
    """Return a safe editable base name for a downloaded PDF."""
    value = re.sub(r'[\x00-\x1f<>:"/\\|?*]', "", str(name or ""))
    value = re.sub(r"\s+", " ", value).strip(" .")
    value = re.sub(r"\.pdf$", "", value, flags=re.IGNORECASE).strip(" .")
    return value or fallback

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
    # Remove OCR field markers such as "8." without stripping a house number.
    s = re.sub(r"(?<!\w)[1-9](?:[ABCDE58])?\.\s*", " ", s)
    s = re.sub(r"[^A-Z0-9 ,'\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip().strip(",").strip()
    return s

def extract_postcode(text: str) -> str:
    # Match UK postcode patterns: e.g. SW1A 1AA, W1A 0AX, M1 1AE, B33 8TH, CR2 6XH, TW4 6JQ
    m = re.search(r"\b([A-Z]{1,2}[0-9][A-Z0-9]?\s*[0-9][A-Z]{2})\b", text.upper())
    if m:
        res = m.group(1).strip()
        if " " not in res and len(res) >= 5:
            res = f"{res[:-3]} {res[-3:]}"
        return res
    return ""

def normalize_address(s: str) -> str:
    """Keep the scanned address on one clean line for every downstream document."""
    if not s:
        return ""
    s = str(s).upper().replace("\r", " ").replace("\n", " ").replace("\u200b", " ")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s*,\s*", ", ", s)
    return s.strip(" ,")


def get_full_address(addr: str, postcode: str) -> str:
    """Combine address and postcode into a single full line address."""
    addr_clean = normalize_address(addr)
    post_clean = (postcode or "").strip().upper()
    if post_clean and post_clean not in addr_clean:
        if addr_clean:
            return f"{addr_clean}, {post_clean}"
        return post_clean
    return addr_clean


def normalize_license_number(s: str) -> str:
    """Normalize a UK licence number to its canonical 16-character identifier."""
    compact = re.sub(r"[^A-Z0-9]", "", str(s or "").upper())
    match = re.search(r"[A-Z9]{5}\d{6}[A-Z9]{2}[A-Z0-9]{3,5}", compact)
    if match:
        return match.group(0)[:16]
    return compact


def _grab(blob, start_pats, end_pats):
    for sp in start_pats:
        for ep in end_pats:
            m = re.search(sp + r"\s*(.*?)\s*" + ep, blob, re.DOTALL)
            if m and m.group(1).strip():
                return m.group(1).strip()
    return ""

# ─────────────────────────────────────────────
#  OCR ENGINE
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
        pass
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
    img = ImageOps.exif_transpose(img)
    img = _deskew_and_orient(img)

    w, h = img.size
    target = 2400
    if max(w, h) < target:
        scale = target / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    gray = ImageOps.grayscale(img)
    gray = ImageEnhance.Sharpness(gray).enhance(2.0)
    gray = ImageEnhance.Contrast(gray).enhance(1.8)

    if cv2 is not None:
        arr = np.array(gray)
        arr = cv2.fastNlMeansDenoising(arr, h=10)
        bw_arr = cv2.adaptiveThreshold(
            arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 35, 11
        )
        bw = Image.fromarray(bw_arr)
    else:
        bw = gray.point(lambda p: 255 if p > 140 else 0)

    # Run OCR on preprocessed grayscale as well as adaptive thresholded image to catch high contrast text
    text_bw = _best_ocr_text(bw)
    text_gray = _best_ocr_text(gray)

    # Return the richer text output
    return text_bw if len(text_bw) >= len(text_gray) else text_gray

# ─────────────────────────────────────────────
#  AZURE AI DOCUMENT INTELLIGENCE
# ─────────────────────────────────────────────
def azure_ocr_available() -> bool:
    if DocumentIntelligenceClient is None:
        return False
    try:
        return bool(st.secrets.get("AZURE_DOCINTEL_ENDPOINT", "")) and bool(st.secrets.get("AZURE_DOCINTEL_KEY", ""))
    except Exception:
        return False

def _field_str(fields, name):
    f = fields.get(name)
    if f is None:
        return ""
    val = getattr(f, "value_string", None) or getattr(f, "content", None) or ""
    return str(val).strip()

def _field_date(fields, name):
    f = fields.get(name)
    if f is None:
        return ""
    d = getattr(f, "value_date", None)
    if d:
        return d.strftime("%d/%m/%Y")
    content = getattr(f, "content", None)
    return normalize_date(content) if content else ""

def extract_signature_crop(result, orig_img: Image.Image) -> bytes:
    """Extract signature crop at full resolution using Azure bounding polygon or licence position fallback."""
    orig_w, orig_h = orig_img.size
    crop_box = None

    if result and getattr(result, "documents", None):
        doc = result.documents[0]
        fields = getattr(doc, "fields", {}) or {}
        sig_field = fields.get("Signature")
        if sig_field and getattr(sig_field, "bounding_regions", None) and sig_field.bounding_regions:
            region = sig_field.bounding_regions[0]
            poly = getattr(region, "polygon", [])
            page_num = getattr(region, "page_number", 1)
            page_w, page_h = None, None
            if getattr(result, "pages", None):
                for page in result.pages:
                    if getattr(page, "page_number", None) == page_num:
                        page_w, page_h = page.width, page.height
                        break
            if poly and len(poly) >= 6 and page_w and page_h:
                xs = poly[0::2]
                ys = poly[1::2]
                min_x = max(0, min(xs))
                max_x = min(page_w, max(xs))
                min_y = max(0, min(ys))
                max_y = min(page_h, max(ys))

                rx1, rx2 = min_x / page_w, max_x / page_w
                ry1, ry2 = min_y / page_h, max_y / page_h

                pad_x = (rx2 - rx1) * 0.05
                pad_y = (ry2 - ry1) * 0.05
                rx1 = max(0.0, rx1 - pad_x)
                rx2 = min(1.0, rx2 + pad_x)
                ry1 = max(0.0, ry1 - pad_y)
                ry2 = min(1.0, ry2 + pad_y)

                crop_box = (
                    int(rx1 * orig_w),
                    int(ry1 * orig_h),
                    int(rx2 * orig_w),
                    int(ry2 * orig_h),
                )

    if not crop_box:
        # Bounding box for UK driving licence signature (Field 9) beneath address
        crop_box = (
            int(0.18 * orig_w),
            int(0.73 * orig_h),
            int(0.55 * orig_w),
            int(0.90 * orig_h),
        )

    cropped_img = orig_img.crop(crop_box)
    return clean_signature_crop(cropped_img)

def clean_signature_crop(cropped_pil: Image.Image) -> bytes:
    """Isolate dark signature ink from background, crop tightly around ink, and make background transparent."""
    if cropped_pil.mode != "RGB":
        cropped_pil = cropped_pil.convert("RGB")

    cv_img = np.array(cropped_pil)
    gray = cv2.cvtColor(cv_img, cv2.COLOR_RGB2GRAY)

    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned_mask = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(cleaned_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        valid_contours = [c for c in contours if cv2.contourArea(c) > 10]
        if not valid_contours:
            valid_contours = contours

        all_pts = np.vstack(valid_contours)
        x, y, w, h = cv2.boundingRect(all_pts)

        pad = 2
        h_img, w_img = gray.shape
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(w_img, x + w + pad)
        y2 = min(h_img, y + h + pad)

        cv_img = cv_img[y1:y2, x1:x2]
        cleaned_mask = cleaned_mask[y1:y2, x1:x2]

    rgba = cv2.cvtColor(cv_img, cv2.COLOR_RGB2RGBA)
    rgba[:, :, 3] = cleaned_mask

    res_pil = Image.fromarray(rgba)
    buf = io.BytesIO()
    res_pil.save(buf, format="PNG")
    return buf.getvalue()

def run_ocr_azure(uploaded_file) -> dict:
    uploaded_file.seek(0)
    orig_img = Image.open(uploaded_file).convert("RGB")
    orig_img = ImageOps.exif_transpose(orig_img)

    azure_img = orig_img.copy()
    azure_img.thumbnail((2000, 2000))
    buf = io.BytesIO()
    azure_img.save(buf, format="JPEG", quality=92)
    img_bytes = buf.getvalue()

    client = DocumentIntelligenceClient(
        endpoint=st.secrets["AZURE_DOCINTEL_ENDPOINT"],
        credential=AzureKeyCredential(st.secrets["AZURE_DOCINTEL_KEY"]),
    )
    poller = client.begin_analyze_document(
        "prebuilt-idDocument",
        AnalyzeDocumentRequest(bytes_source=img_bytes),
    )
    result = poller.result()

    if not result.documents:
        raise ValueError("Azure couldn't detect an ID document in this photo.")

    fields = result.documents[0].fields
    full_address = _field_str(fields, "Address")
    postcode = extract_postcode(full_address)
    address_no_postcode = re.sub(re.escape(postcode), "", full_address, flags=re.I).strip(", ").strip() if postcode else full_address

    sig_bytes = extract_signature_crop(result, orig_img)

    return {
        "surname": _field_str(fields, "LastName").upper(),
        "forename": _field_str(fields, "FirstName").upper(),
        "dob": _field_date(fields, "DateOfBirth"),
        "expiry": _field_date(fields, "DateOfExpiration"),
        "licence": normalize_license_number(_field_str(fields, "DocumentNumber")),
        "address": normalize_address(address_no_postcode),
        "postcode": postcode.upper(),
        "signature_bytes": sig_bytes,
    }

def extract_signature_crop_fallback(uploaded_file) -> bytes:
    uploaded_file.seek(0)
    orig_img = Image.open(uploaded_file).convert("RGB")
    orig_img = ImageOps.exif_transpose(orig_img)
    orig_w, orig_h = orig_img.size
    crop_box = (
        int(0.18 * orig_w),
        int(0.73 * orig_h),
        int(0.55 * orig_w),
        int(0.90 * orig_h),
    )
    cropped_img = orig_img.crop(crop_box)
    return clean_signature_crop(cropped_img)

def parse_licence(raw: str) -> dict:
    blob = " " + re.sub(r"\s+", " ", raw.upper()) + " "

    # Pre-clean known common OCR substitutions in field headers
    blob_proc = re.sub(r"\b1[.,;]\s*", " 1. ", blob)
    blob_proc = re.sub(r"\b2[.,;]\s*", " 2. ", blob_proc)
    blob_proc = re.sub(r"\b3[.,;]\s*", " 3. ", blob_proc)
    blob_proc = re.sub(r"\b4[Aa][.,;]\s*", " 4A. ", blob_proc)
    blob_proc = re.sub(r"\b4[Bb][.,;]\s*", " 4B. ", blob_proc)
    blob_proc = re.sub(r"\b5[.,;]\s*", " 5. ", blob_proc)
    blob_proc = re.sub(r"\b8[.,;]\s*", " 8. ", blob_proc)

    surname = clean_name(_grab(blob_proc, [r"1\."], [r"2\."])) or (re.search(r"1\.\s*([A-Z\-]+)", blob_proc).group(1).strip() if re.search(r"1\.\s*([A-Z\-]+)", blob_proc) else "")
    forename = clean_name(_grab(blob_proc, [r"2\."], [r"3\."])) or (re.search(r"2\.\s*([A-Z\-]+)", blob_proc).group(1).strip() if re.search(r"2\.\s*([A-Z\-]+)", blob_proc) else "")
    dob = first_date(_grab(blob_proc, [r"3\."], [r"4[Aa]\b"])) or (normalize_date(re.search(r"3\.\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})", blob_proc).group(1)) if re.search(r"3\.\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})", blob_proc) else "")
    expiry = first_date(_grab(blob_proc, [r"4[Bb]\.?"], [r"4[Cc]", r"5\."])) or (normalize_date(re.search(r"4[Bb]\.?\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})", blob_proc).group(1)) if re.search(r"4[Bb]\.?\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})", blob_proc) else "")

    licence = ""
    clean_strip = re.sub(r"\s", "", blob_proc)
    lic_match = re.search(r"5\.?([A-Z9]{5}\d{6}[A-Z9]{2}[A-Z0-9]{3,5})", clean_strip)
    if not lic_match:
        lic_match = re.search(r"([A-Z9]{5}\d{6}[A-Z9]{2}[A-Z0-9]{3,5})", clean_strip)
    if lic_match: licence = normalize_license_number(lic_match.group(1))

    raw_8 = _grab(blob_proc, [r"8\."], [r"9\."]) or (re.search(r"8\.\s*(.*?)(?=\s*9\.)", blob_proc, re.DOTALL).group(1).strip() if re.search(r"8\.\s*(.*?)(?=\s*9\.)", blob_proc, re.DOTALL) else blob_proc)
    raw_9_match = re.search(r"9\.\s*(.*?)(?=\s*10\.|$)", blob_proc, re.DOTALL)
    raw_9 = raw_9_match.group(1).strip() if raw_9_match else ""
    postcode = extract_postcode(raw_8) or extract_postcode(raw_9) or extract_postcode(blob_proc)
    addr_clean = strip_address_noise(raw_8.replace(licence, ""))
    if postcode: addr_clean = re.sub(re.escape(postcode), "", addr_clean, flags=re.I)
    addr_clean = re.sub(r"^[0-9A-Z]{1,2}\b\.?\s*", "", addr_clean.strip()).strip(", ").strip()
    addr_clean = normalize_address(addr_clean)

    return {"surname": surname, "forename": forename, "dob": dob, "expiry": expiry, "licence": licence, "address": addr_clean, "postcode": postcode}

def _wrap_draw(c, text, x, y, max_width, font="Helvetica", size=11, leading=14):
    c.setFont(font, size)
    for line in simpleSplit(text, font, size, max_width):
        c.drawString(x, y, line)
        y -= leading
    return y

def _wrap_draw_bold_token(c, text, token, x, y, max_width, size=11, leading=14):
    """Wrap text while rendering one exact token in bold."""
    lines = simpleSplit(text, "Helvetica", size, max_width)
    for line in lines:
        token_start = line.find(token) if token else -1
        if token_start < 0:
            c.setFont("Helvetica", size)
            c.drawString(x, y, line)
        else:
            before, after = line[:token_start], line[token_start + len(token):]
            before_width = stringWidth(before, "Helvetica", size)
            token_width = stringWidth(token, "Helvetica-Bold", size)
            c.setFont("Helvetica", size)
            c.drawString(x, y, before)
            c.setFont("Helvetica-Bold", size)
            c.drawString(x + before_width, y, token)
            c.setFont("Helvetica", size)
            c.drawString(x + before_width + token_width, y, after)
        y -= leading
    return y


def generate_permission_letter(data: dict) -> bytes:
    """Generate Permission Letter PDF containing only the Director signature (Muhammad Sohail Qureshi).

    Note: Hirer/licence signature is intentionally omitted from this document completely.
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter, pageCompression=1)
    pw, ph = letter
    bg = _find_img("image_f4efbe"); sig = _find_img("signature")
    if bg: c.drawImage(bg, 0, 0, width=pw, height=ph)
    c.setFont("Helvetica", 11)
    c.drawRightString(pw - 54, 595, data["date"])
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(pw / 2, 550, "PERMISSION LETTER")

    text_width = pw - 108
    y = 515
    c.setFont("Helvetica", 11)
    c.drawString(54, y, "To Whom It May Concern,")
    y -= 25

    policy_number = str(data.get("insurance_policy", "")).strip().upper()
    confirm_text = (
        f"We confirm that the below vehicle can be used for the carriage of "
        f"passengers for hire and reward by prior appointments (private hire) "
        f"as specified on insurance policy: {policy_number}"
    )
    y = _wrap_draw_bold_token(c, confirm_text, policy_number, 54, y, text_width)
    y -= 4

    auth_text = (
        "We authorise and give permission to the following individual to use "
        "the vehicle for all private hire bookings from UBER, BOLT, OLA, FREE "
        "NOW app, WHEELY and other private hire operators."
    )
    y = _wrap_draw(c, auth_text, 54, y, text_width)
    y -= 18

    c.setFont("Helvetica", 11)
    for label, val in [("Vehicle Registration", data["registration"]), ("Make and Model", data["make_model"]), ("Driver Name", data["driver_name"]), ("Address", normalize_address(data["address"])), ("Driving Licence No", data["license_no"])]:
        c.drawString(54, y, f"{label} :"); c.drawString(180, y, val)
        y -= 22
    y -= 18

    c.drawString(54, y, "Hire start date. :"); c.drawString(160, y, data["start_date"])
    y -= 15
    c.drawString(54, y, "Hire end date    :"); c.drawString(160, y, data["end_date"])
    y -= 25

    c.drawString(54, y, "Regards,")
    y -= 5

    if sig:
        sig_w, sig_h = 60, 38
        c.drawImage(sig, 54, y - sig_h, width=sig_w, height=sig_h, mask="auto")
        y -= (sig_h + 12)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(54, y, "Muhammad Sohail Qureshi")
        y -= 14
        c.setFont("Helvetica", 11)
        c.drawString(54, y, "Director(FA-IBI LTD)")

    c.save(); buf.seek(0); return buf.getvalue()

# ─────────────────────────────────────────────
#  CONTRACT PDF — coordinates re-measured directly against the actual
#  template background using the calibration-grid PDF.
#
#  Method: the calibration grid was exported to an image, the red 20pt
#  ruler lines were detected pixel-by-pixel and regressed against their
#  known point values (0,20,40,...), giving an exact pixel->point
#  mapping for this specific template render. Every label on the clean
#  template (Full Name, Address, License No, Ph/Email, Hire Payment,
#  Hire Period, Hire Vehicle Details, and the page-2 header/footer) was
#  then located in pixel space via OCR / pixel inspection and converted
#  through that mapping. The result was test-rendered and visually
#  checked against the template before being committed here.
#
#  Units: PDF points, origin (0,0) at BOTTOM-LEFT of the page,
#  page size is 612 x 792 (US Letter).
# ─────────────────────────────────────────────
CONTRACT_PAGE1_FIELDS = {
    # key:               (x,     y,     font_size)
    "contract_no":       (335,   696,   8.0),
    "date":              (80,    48,    8.8),    # bottom "Date:___" row, below signatures
    "driver_name":       (87,    660.5, 8.8),
    "dob":               (494,   660.5, 8.8),
    "address":           (77,    636.5, 8.8),
    "postcode":          (467,   636.5, 8.8),
    "license_no":        (92,    611.5, 8.8),
    "issuing_authority":  (327,   611.5, 8.8),
    "expiry_date":       (489,   611.5, 8.8),
    "phone":             (60,    582.4, 8.8),
    "email":             (283,   582.4, 8.8),
    "rent":              (110,   379,   8.8),   # "The Rental of £___" row
    "rate":              (135,   343.9, 8.8),   # "...at the rate of ___ Pence per mile" row
    "deposit":           (107,   311.5, 8.8),   # "Deposit Paid £___" row
    "start_date":        (108,   213.4, 8.8),   # "Date Hire Start:" row
    "expected_return":   (185,   198.4, 8.8),   # "Expected Date of Vehicle Return:" row
    "start_time":        (455,   213.4, 8.8),   # time the vehicle was handed over
    "return_time":       (455,   198.4, 8.8),   # time the vehicle was returned
    "car_make":          (68,    133.9, 8.8),   # "HIRE VEHICLE DETAILS" -> Make/Reg/Model row
    "registration":      (288,   133.9, 8.8),
    "car_model":         (456,   133.9, 8.8),
}
CONTRACT_PAGE2_FIELDS = {
    "contract_no":  (140, 723,  8.8),   # close beside the "CONTRACT NUMBER:" label
    "registration": (375, 723,  8.8),   # clear of the "CAR REG:" label
    "date":         (280, 48,   8.8),   # "Date:" slot, kept clear of the "Owners Signature X" label
}
CONTRACT_FIELD_MAXW = {
    "contract_no": 130,
    "date": 55,
    "driver_name": 300,
    "address": 300,
    "car_make": 180,
    "car_model":         130,
    "start_time":        75,
    "return_time":       75,
}

# ─────────────────────────────────────────────
#  OWNER SIGNATURES
#  Add a new entry here whenever a new employee's signature image is
#  dropped into the project folder (same folder as this script). The
#  dropdown label is what shows up in the form; the value is the base
#  filename (without extension) that _find_img() will look for.
# ─────────────────────────────────────────────
SIGNATURE_FILES = {
    "Sohail's Signature": "Sohails_Signature",  # Sohails_Signature.png — background removed, cropped tight
    "Rizwan's Signature": "Rizwan_Signature",   # Rizwan_Signature.png — background removed, cropped tight
    "FA-IBI Signature":   "FA-IBI_Signature",   # FA-IBI_Signature.png — background removed, cropped tight
}
SIGNATURE_OPTIONS = ["-- No Signature --"] + list(SIGNATURE_FILES.keys())

# Where the signature image gets stamped on each page (PDF points,
# origin bottom-left) — sized to sit neatly on the "Owners Signature X:"
# line without overlapping the label or the blank line beneath it.
# Signatures are scaled to FIT inside this box while keeping their own
# aspect ratio (see _stamp_signature), so tall/narrow and wide/short
# signatures both look correct without being squashed or stretched.
SIGNATURE_PLACEMENT = {
    1: {"x": 448, "y": 64, "width": 85, "height": 22},   # page 1, positioned directly above printed line
    2: {"x": 452, "y": 42, "width": 62, "height": 20},   # page 2, positioned directly above printed line
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

def _stamp_signature(cv, signature_label: str, page: int):
    filename = SIGNATURE_FILES.get(signature_label)
    if not filename:
        return
    sig_path = _find_img(filename)
    if not sig_path:
        return
    spot = SIGNATURE_PLACEMENT.get(page)
    if not spot:
        return
    box_w, box_h = spot["width"], spot["height"]
    try:
        with Image.open(sig_path) as im:
            iw, ih = im.size
        scale = min(box_w / iw, box_h / ih)
        draw_w, draw_h = iw * scale, ih * scale
    except Exception:
        draw_w, draw_h = box_w, box_h
    x = spot["x"] + (box_w - draw_w) / 2
    y = spot["y"] + (box_h - draw_h) / 2
    cv.drawImage(sig_path, x, y, width=draw_w, height=draw_h, mask="auto")

def _stamp_hirer_signature(cv, signature_bytes: bytes, spot: dict):
    if not signature_bytes:
        return
    box_w, box_h = spot["width"], spot["height"]
    try:
        from reportlab.lib.utils import ImageReader
        im = Image.open(io.BytesIO(signature_bytes))
        iw, ih = im.size
        scale = min(box_w / iw, box_h / ih)
        draw_w, draw_h = iw * scale, ih * scale
        x = spot["x"] + (box_w - draw_w) / 2
        y = spot["y"] + (box_h - draw_h) / 2
        cv.drawImage(ImageReader(im), x, y, width=draw_w, height=draw_h, mask="auto")
    except Exception:
        pass

def generate_contract(data: dict) -> bytes:
    buf = io.BytesIO()
    cv = canvas.Canvas(buf, pagesize=letter, pageCompression=1)
    W, H = 612, 792
    bg1, bg2 = _find_img("1"), _find_img("2")

    if bg1: cv.drawImage(bg1, 0, 0, width=W, height=H)
    cv.setFont("Helvetica-Bold", 8.8)
    for key, (x, y, size) in CONTRACT_PAGE1_FIELDS.items():
        cv.setFont("Helvetica-Bold" if key in ("contract_no", "rent", "rate", "deposit", "car_make", "registration", "car_model") else "Helvetica", size)
        value = normalize_address(data.get(key, "")) if key == "address" else data.get(key, "")
        _draw_fit(cv, value, x, y, base_size=size, max_width=CONTRACT_FIELD_MAXW.get(key),
                  font="Helvetica-Bold" if key in ("contract_no", "rent", "rate", "deposit", "car_make", "registration", "car_model") else "Helvetica")
    _stamp_signature(cv, data.get("owner_signature", ""), page=1)
    if data.get("hirer_signature"):
        _stamp_hirer_signature(cv, data.get("hirer_signature"), spot={"x": 160, "y": 66, "width": 110, "height": 25})
    cv.showPage()

    if bg2: cv.drawImage(bg2, 0, 0, width=W, height=H)
    for key, (x, y, size) in CONTRACT_PAGE2_FIELDS.items():
        _draw_fit(cv, data.get(key, ""), x, y, base_size=size, max_width=CONTRACT_FIELD_MAXW.get(key),
                  font="Helvetica-Bold")
    _stamp_signature(cv, data.get("owner_signature", ""), page=2)
    if data.get("hirer_signature"):
        _stamp_hirer_signature(cv, data.get("hirer_signature"), spot={"x": 160, "y": 42, "width": 110, "height": 25})

    cv.save(); buf.seek(0); return buf.getvalue()

def generate_calibration_grid() -> bytes:
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
            add_audit_log("Verification PIN Entered", details="Successful Verification PIN Entry")
            if cookie_manager is not None:
                cookie_manager.set(
                    AUTH_COOKIE_NAME, "true",
                    expires_at=datetime.now() + timedelta(days=AUTH_COOKIE_DAYS),
                    key="set_auth_cookie",
                )
            st.rerun()
        else:
            add_audit_log("Verification PIN Entered", details="Failed Verification PIN Entry")
            notify("Invalid Security Verification Pin Code", "error")
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
for k, v in dict(ocr_name="", ocr_licence="", ocr_address="", ocr_postcode="", ocr_dob="", ocr_expiry="", ocr_signature_bytes=None, last_scan_id="", sel_reg="", sel_make="", sel_model="", scan_msg="", fleet_msg="", perm_pdf=None, perm_filename="Permission Letter", contract_pdf=None, contract_filename="Contract", contract_no="", pending_contract=None).items():
    if k not in st.session_state: st.session_state[k] = v

col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.title("FA-IBI Workspace")
with col_head2:
    st.markdown("<div style='text-align: right; margin-top: 10px;'>", unsafe_allow_html=True)
    with st.popover("📋 Audit Logs", use_container_width=True):
        st.subheader("📋 System Audit Logs")
        st.caption("History of created documents & PIN verification attempts")
        logs = get_audit_logs()
        if not logs:
            st.info("No audit log records found.")
        else:
            search_query = st.text_input("🔍 Search logs...", key="audit_log_search")
            filtered_logs = logs
            if search_query.strip():
                q = search_query.strip().lower()
                filtered_logs = [
                    l for l in logs
                    if q in l.get("timestamp", "").lower()
                    or q in l.get("event_type", "").lower()
                    or q in l.get("doc_name", "").lower()
                    or q in l.get("details", "").lower()
                ]

            import pandas as pd
            df = pd.DataFrame(filtered_logs)
            if not df.empty:
                df = df.rename(columns={
                    "timestamp": "Date & Time",
                    "event_type": "Event Type",
                    "doc_name": "Document Name",
                    "details": "Details"
                })
                cols = [c for c in ["Date & Time", "Event Type", "Document Name", "Details"] if c in df.columns]
                st.dataframe(df[cols], use_container_width=True, hide_index=True)
            else:
                st.write("No matching log records found.")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("### 🎛️ Shared Data Automation Panel")
if st.session_state.scan_msg:
    notify(st.session_state.scan_msg, "warning" if st.session_state.scan_msg.startswith("⚠️") else "success")
if st.session_state.fleet_msg:
    notify(st.session_state.fleet_msg, "info")
col_scan, col_fleet = st.columns(2)

with col_scan:
    uploaded = st.file_uploader("📷 Driver's Licence Scanner", type=["jpg","png","jpeg"], key="global_engine_scanner")
    use_azure = azure_ocr_available()
    if uploaded and not use_azure:
        st.caption("ℹ️ Using the built-in Tesseract scanner. Add `AZURE_DOCINTEL_ENDPOINT` and `AZURE_DOCINTEL_KEY` to secrets for much more accurate scanning via Azure AI Document Intelligence.")
    if uploaded and (use_azure or pytesseract):
        fid = f"{uploaded.name}_{uploaded.size}"
        if st.session_state.last_scan_id != fid:
            with st.spinner("Processing Elements..."):
                try:
                    if use_azure:
                        p = run_ocr_azure(uploaded)
                    else:
                        raw = run_ocr(uploaded); p = parse_licence(raw)
                        p["signature_bytes"] = extract_signature_crop_fallback(uploaded)
                    client_name = f"{p['forename']} {p['surname']}".strip()
                    st.session_state.ocr_name, st.session_state.ocr_licence, st.session_state.ocr_address, st.session_state.ocr_postcode, st.session_state.ocr_dob, st.session_state.ocr_expiry = client_name, p["licence"], p["address"], p["postcode"], p["dob"], p["expiry"]
                    st.session_state.ocr_signature_bytes = p.get("signature_bytes")
                    if client_name:
                        st.session_state.perm_filename = clean_document_name(f"{client_name} Permission Letter", "Permission Letter")
                        st.session_state.contract_filename = clean_document_name(f"{client_name} Contract", "Contract")
                    st.session_state.scan_msg = "✅ Licence scanned successfully! Please double-check the fields below before generating documents."
                except Exception as e: st.session_state.scan_msg = f"⚠️ Scan parsing failed: {e}"
                st.session_state.last_scan_id = fid
            st.rerun()
    elif uploaded and not use_azure and not pytesseract:
        st.error("Neither Azure Document Intelligence (secrets not configured) nor pytesseract is available, so scanning can't run.")

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
        st.session_state.contract_filename = st.session_state.contract_filename or "Contract"
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
        perm_addr_val = get_full_address(st.session_state.ocr_address, st.session_state.ocr_postcode)
        p_addr = st.text_area("Driver Address", value=perm_addr_val)
        default_p_doc_name = f"{st.session_state.ocr_name} Permission Letter".strip() if st.session_state.ocr_name else "Permission Letter"
        p_doc_name = st.text_input("Document Name", default_p_doc_name, key="perm_document_name")
        go_p = st.form_submit_button("🖨️ Generate Permission Letter PDF")
    if go_p:
        perm_clean_name = clean_document_name(p_doc_name, "Permission Letter")
        st.session_state.perm_pdf = generate_permission_letter({"date": p_date.strftime("%d/%m/%Y"), "insurance_policy": p_ins, "registration": format_uk_reg(p_reg), "make_model": p_mod.upper(), "driver_name": p_name.upper(), "address": p_addr.upper(), "license_no": p_lic.upper(), "start_date": p_start.strftime("%d/%m/%Y"), "end_date": p_end.strftime("%d/%m/%Y")})
        st.session_state.perm_filename = perm_clean_name
        add_audit_log("Permission Letter Generated", details=f"Driver: {p_name.upper()}, Reg: {format_uk_reg(p_reg)}", doc_name=f"{perm_clean_name}.pdf")
        st.rerun()
    if st.session_state.perm_pdf: st.download_button("📥 Download Permission Letter PDF", data=st.session_state.perm_pdf, file_name=f"{st.session_state.perm_filename}.pdf", mime="application/pdf", key="dl_perm_btn")

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
        notify("🎉 Contract PDF Created Successfully!", "success")
        st.download_button("📥 Download Generated Contract PDF", data=st.session_state.contract_pdf, file_name=f"{st.session_state.contract_filename}.pdf", mime="application/pdf", key="dl_contract_btn")
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
        tm1, tm2 = st.columns(2)
        with tm1: c_start_time = st.time_input("Time Car Given", datetime.now().time().replace(second=0, microsecond=0), key="c_form_start_time")
        with tm2: c_return_time = st.time_input("Time Car Returned", datetime.now().time().replace(second=0, microsecond=0), key="c_form_return_time")
        st.markdown("---"); pv1, pv2, pv3 = st.columns(3)
        with pv1: c_mk = st.text_input("Make", value=st.session_state.sel_make)
        with pv2: c_rv = st.text_input("Reg", value=st.session_state.sel_reg)
        with pv3: c_mv = st.text_input("Model", value=st.session_state.sel_model)
        st.markdown("---")
        sig_col1, sig_col2 = st.columns(2)
        hirer_sig_options = ["Scanned Licence Signature", "-- No Signature --"]
        with sig_col1:
            c_hirer_sig = st.selectbox("✍️ Hirer Signature", hirer_sig_options)
        with sig_col2:
            c_sig = st.selectbox("✍️ Owner Signature", SIGNATURE_OPTIONS)
        default_c_doc_name = f"{st.session_state.ocr_name} Contract".strip() if st.session_state.ocr_name else "Contract"
        c_doc_name = st.text_input("Document Name", default_c_doc_name, key="contract_document_name")
        go_c = st.form_submit_button("🖨️ Generate 2-Page Contract PDF", type="primary")
    if go_c:
        contract_clean_name = clean_document_name(c_doc_name, "Contract")
        hirer_sig_bytes = st.session_state.ocr_signature_bytes if c_hirer_sig == "Scanned Licence Signature" else None
        st.session_state.pending_contract = {"contract_no": c_no.strip().upper() or "N/A", "date": c_date.strftime("%d/%m/%Y"), "driver_name": c_name.strip().upper(), "address": normalize_address(c_addr), "postcode": c_post.strip().upper(), "dob": c_dob.strip(), "license_no": c_lic.strip().upper(), "expiry_date": c_exp.strip(), "issuing_authority": c_auth.strip().upper(), "phone": c_ph.strip(), "email": c_em.strip().upper(), "rent": c_rent.strip(), "rate": c_rate.strip(), "deposit": c_dep.strip(), "start_date": c_st.strftime("%d/%m/%Y"), "expected_return": c_ret.strftime("%d/%m/%Y"), "start_time": c_start_time.strftime("%H:%M"), "return_time": c_return_time.strftime("%H:%M"), "registration": format_uk_reg(c_rv), "car_make": c_mk.strip().upper(), "car_model": c_mv.strip().upper(), "owner_signature": c_sig, "hirer_signature": hirer_sig_bytes}
        st.session_state.contract_filename = contract_clean_name
        add_audit_log("Contract Generated", details=f"Contract No: {c_no.strip().upper() or 'N/A'}, Driver: {c_name.strip().upper()}, Reg: {format_uk_reg(c_rv)}", doc_name=f"{contract_clean_name}.pdf")
        st.rerun()
