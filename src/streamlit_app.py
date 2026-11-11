import streamlit as st
import os, re, io, logging
import numpy as np
from PIL import Image, ImageOps, ImageEnhance
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
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
except ImportError:
    AzureKeyCredential = None
    DocumentIntelligenceClient = None

try:
    import pypdfium2
except ImportError:
    pypdfium2 = None

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pillow_heif = None

try:
    from supabase import create_client
except ImportError:
    create_client = None

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload
except ImportError:
    service_account = None
    build = None
    MediaIoBaseUpload = None

import base64, json, urllib.parse, hashlib, threading, zipfile, functools
from reportlab.lib.utils import simpleSplit

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIT_LOG_FILE = os.path.join(SRC_DIR, "audit_logs.json")

def get_secret(key: str, default: str = "") -> str:
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default

def get_uk_now() -> datetime:
    """Return current datetime in UK local time (Europe/London), handling GMT/BST automatically."""
    try:
        return datetime.now(ZoneInfo("Europe/London"))
    except Exception:
        return datetime.now()

def get_audit_logs():
    """Local audit log entries (newest first)."""
    if not os.path.exists(AUDIT_LOG_FILE):
        return []
    try:
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []

_AUDIT_LOCK = threading.Lock()

def _supabase_credentials() -> tuple[str, str]:
    url = get_secret("SUPABASE_URL", "")
    key = get_secret("SUPABASE_SERVICE_ROLE_KEY") or get_secret("SUPABASE_KEY") or get_secret("SUPABASE_ANON_KEY") or ""
    return url, key

@st.cache_resource(show_spinner=False)
def _cached_supabase_client(url: str, key: str):
    return create_client(url, key)

def get_supabase_client():
    """Return a shared Supabase client, or None when it isn't configured."""
    if create_client is None:
        return None
    url, key = _supabase_credentials()
    if not url or not key:
        return None
    try:
        return _cached_supabase_client(url, key)
    except Exception:
        return None

def _push_audit_to_supabase(entry: dict):
    """Mirror an audit entry into the optional Supabase `audit_logs` table.

    Streamlit Cloud wipes local files whenever the app restarts, so this keeps
    history permanently when the table exists. Fails silently otherwise.
    """
    client = get_supabase_client()
    if client is None:
        return
    def _work():
        try:
            client.table("audit_logs").insert(entry).execute()
        except Exception:
            pass
    threading.Thread(target=_work, daemon=True).start()

def add_audit_log(event_type: str, details: str = "", doc_name: str = "", file_path: str = ""):
    entry = {
        "timestamp": get_uk_now().strftime("%Y-%m-%d %H:%M:%S"),
        "event_type": event_type,
        "doc_name": doc_name,
        "details": details,
        "file_path": file_path,
    }
    with _AUDIT_LOCK:
        logs = get_audit_logs()
        logs.insert(0, entry)
        try:
            with open(AUDIT_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(logs[:5000], f, indent=2)
        except Exception:
            pass
    _push_audit_to_supabase(entry)
    try:
        get_cached_audit_logs.clear()
    except Exception:
        pass

def save_to_google_drive(file_bytes: bytes, filename: str, vehicle_reg: str) -> tuple[bool, str]:
    """Upload generated PDF to Google Drive under folder matching car's registration.

    Returns (success, message). Must not break main page flow if upload fails.
    """
    if build is None or service_account is None or MediaIoBaseUpload is None:
        return False, "Google Drive client libraries are not installed."

    try:
        # Load Google service account credentials from st.secrets
        creds_data = get_secret("gcp_service_account") or get_secret("GOOGLE_DRIVE_CREDENTIALS") or get_secret("GDRIVE_SERVICE_ACCOUNT")
        if not creds_data:
            return False, "Google Drive API credentials not found in secrets (`gcp_service_account`)."

        if isinstance(creds_data, str):
            creds_info = json.loads(creds_data)
        elif hasattr(creds_data, "to_dict"):
            creds_info = creds_data.to_dict()
        else:
            creds_info = dict(creds_data)

        scopes = ["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=scopes)

        # Optional domain-wide delegation for virtualcarhire@gmail.com if configured
        target_email = get_secret("GDRIVE_IMPERSONATE_EMAIL", "virtualcarhire@gmail.com")
        if creds_info.get("type") == "service_account" and target_email:
            try:
                creds = creds.with_subject(target_email)
            except Exception:
                pass

        service = build("drive", "v3", credentials=creds)

        folder_name = vehicle_reg.strip().upper() if vehicle_reg and vehicle_reg.strip() else "Uncategorized"

        # Search for existing folder with vehicle registration name
        query = f"mimeType = 'application/vnd.google-apps.folder' and name = '{folder_name}' and trashed = false"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        folders = results.get("files", [])

        if folders:
            folder_id = folders[0]["id"]
        else:
            # Create folder for vehicle registration
            folder_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder"
            }
            folder = service.files().create(body=folder_metadata, fields="id").execute()
            folder_id = folder.get("id")

        # Upload PDF file into the folder
        file_name_pdf = f"{filename}.pdf" if not filename.endswith(".pdf") else filename
        file_metadata = {
            "name": file_name_pdf,
            "parents": [folder_id]
        }

        media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype="application/pdf", resumable=True)
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink"
        ).execute()

        return True, f"Successfully saved '{file_name_pdf}' to Google Drive folder '{folder_name}'."
    except Exception as e:
        return False, f"Google Drive upload failed: {str(e)}"

def sync_to_supabase(file_bytes: bytes, filename: str, doc_type: str, driver_ref: str = "", vehicle_reg: str = "") -> str:
    """Upload a generated PDF to Supabase Storage and record it in `driver_documents`.

    The upload runs in a background thread so generating a document stays
    instant. Returns the storage filename (or "" when Supabase is not configured).
    Fails silently so it never interrupts the user.
    """
    client = get_supabase_client()
    if client is None:
        return ""
    bucket_name = "driver_documents"
    safe_name = re.sub(r"[^A-Za-z0-9 ._()\-]", "", str(filename or "document")).strip() or "document"
    storage_filename = f"{get_uk_now().strftime('%Y%m%d_%H%M%S')}_{safe_name}"
    if not storage_filename.lower().endswith(".pdf"):
        storage_filename += ".pdf"
    payload = {
        "driver_ref": driver_ref,
        "vehicle_reg": vehicle_reg,
        "doc_type": doc_type,
        "file_name": storage_filename,
        "file_path": f"{bucket_name}/{storage_filename}",
        "created_at": get_uk_now().isoformat(),
    }

    def _work():
        try:
            client.storage.from_(bucket_name).upload(
                path=storage_filename,
                file=file_bytes,
                file_options={"content-type": "application/pdf", "upsert": "true"},
            )
        except Exception:
            pass
        try:
            client.table("driver_documents").insert(payload).execute()
        except Exception:
            pass

    try:
        threading.Thread(target=_work, daemon=True).start()
    except Exception:
        return ""
    return storage_filename

def download_from_supabase_storage(doc_name: str, file_path: str = "") -> bytes | None:
    """Download document PDF bytes from Supabase Storage bucket driver_documents."""
    if create_client is None:
        return None
    try:
        client = get_supabase_client()
        if client is None:
            return None
        bucket_name = "driver_documents"

        paths_to_try = []
        if file_path:
            paths_to_try.append(file_path.replace(f"{bucket_name}/", "", 1))
        if doc_name:
            paths_to_try.append(doc_name.strip())

        for p in dict.fromkeys(paths_to_try):
            try:
                res = client.storage.from_(bucket_name).download(p)
                if res:
                    return res
            except Exception:
                pass

        if doc_name:
            base_doc = re.sub(r"\.pdf$", "", doc_name.strip(), flags=re.IGNORECASE)
            try:
                records = client.table("driver_documents").select("*").ilike("file_name", f"%{base_doc}%").order("created_at", desc=True).limit(5).execute()
                for rec in (records.data or []) if records else []:
                    fn = rec.get("file_name")
                    if fn:
                        try:
                            res = client.storage.from_(bucket_name).download(fn)
                            if res:
                                return res
                        except Exception:
                            pass
            except Exception:
                pass

            try:
                files = client.storage.from_(bucket_name).list(
                    "", {"limit": 100, "search": base_doc[:60], "sortBy": {"column": "created_at", "order": "desc"}}
                )
                for f in files or []:
                    fn = f.get("name", "")
                    if base_doc.lower() in fn.lower():
                        try:
                            res = client.storage.from_(bucket_name).download(fn)
                            if res:
                                return res
                        except Exception:
                            pass
            except Exception:
                pass

        return None
    except Exception:
        return None

def create_signed_pdf_links(paths: tuple, expires_in: int = 3600) -> dict:
    """Batch-create temporary download links for stored PDFs. {path: url}."""
    client = get_supabase_client()
    if client is None or not paths:
        return {}
    bucket = "driver_documents"
    clean = [p.replace(f"{bucket}/", "", 1) for p in paths if p]
    out = {}
    try:
        res = client.storage.from_(bucket).create_signed_urls(clean, expires_in)
        for item in res or []:
            path = item.get("path") or ""
            url = item.get("signedURL") or item.get("signedUrl") or item.get("signed_url") or ""
            if path and url and not item.get("error"):
                out[f"{bucket}/{path}"] = url
    except Exception:
        pass
    return out

@functools.lru_cache(maxsize=64)
def _find_img(base_name):
    candidate_dirs = [
        SRC_DIR,
        os.path.join(SRC_DIR, "src"),
        os.path.dirname(SRC_DIR),
        os.getcwd(),
        os.path.join(os.getcwd(), "src"),
        os.path.dirname(os.path.abspath(__file__)),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"),
    ]
    seen = set()
    for d in candidate_dirs:
        if not d or d in seen:
            continue
        seen.add(d)
        for ext in [".jpg", ".png", ".jpeg", ".JPG", ".PNG"]:
            p = os.path.join(d, base_name + ext)
            if os.path.exists(p):
                return p
    return None

FAVICON_URL = "https://virtualcarhire.pages.dev/assets/favicon-32x32.png?v=3"
SOCIAL_PREVIEW_IMG_URL = "https://virtualcarhire.pages.dev/assets/ab_workspace_social.png"
PUBLIC_APP_URL = "https://vchletter.xubi.org"

fav_path = FAVICON_URL or _find_img("Screenshot_2026-06-09_230035") or "🚗"

def _inject_index_meta_tags():
    try:
        import streamlit
        static_dir = os.path.join(os.path.dirname(streamlit.__file__), "static")
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                content = f.read()
            og_meta = (
                '<meta property="og:title" content="FA-IBI Workspace" />\n'
                '<meta property="og:description" content="FA-IBI Workspace — Create, manage and generate your documents in one place." />\n'
                f'<meta property="og:image" content="{SOCIAL_PREVIEW_IMG_URL}" />\n'
                f'<meta property="og:url" content="{PUBLIC_APP_URL}" />\n'
                '<meta property="og:type" content="website" />\n'
                '<meta name="twitter:card" content="summary_large_image" />\n'
                '<meta name="twitter:title" content="FA-IBI Workspace" />\n'
                '<meta name="twitter:description" content="FA-IBI Workspace — Create, manage and generate your documents in one place." />\n'
                f'<meta name="twitter:image" content="{SOCIAL_PREVIEW_IMG_URL}" />\n'
            )
            if 'property="og:title"' in content:
                return  # already injected; avoid rewriting index.html on every rerun
            content = content.replace("<head>", f"<head>\n{og_meta}", 1)
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(content)
    except Exception:
        pass

_inject_index_meta_tags()

# ─────────────────────────────────────────────
#  STREAMLIT CONFIGURATION & BRAND HIDING
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="FA-IBI Workspace",
    page_icon=fav_path,
    layout="wide"
)

# Keep the browser tab title fixed (runs in the app document; no iframe).
st.html("""
<script>
(function () {
    const desiredTitle = "FA-IBI Workspace";
    function fix() {
        try { if (document.title !== desiredTitle) document.title = desiredTitle; } catch (e) {}
        try { if (window.parent && window.parent.document.title !== desiredTitle) window.parent.document.title = desiredTitle; } catch (e) {}
    }
    fix();
    if (!window.__faIbiTitleTimer) { window.__faIbiTitleTimer = setInterval(fix, 1500); }
})();
</script>
""", unsafe_allow_javascript=True)

st.html(f"""
<div class="fa-hidden-meta" style="display:none"></div>
<meta property="og:title" content="FA-IBI Workspace" />
<meta property="og:description" content="FA-IBI Workspace — Create, manage and generate your documents in one place." />
<meta property="og:image" content="{SOCIAL_PREVIEW_IMG_URL}" />
<meta property="og:url" content="{PUBLIC_APP_URL}" />
<meta property="og:type" content="website" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="FA-IBI Workspace" />
<meta name="twitter:description" content="FA-IBI Workspace — Create, manage and generate your documents in one place." />
<meta name="twitter:image" content="{SOCIAL_PREVIEW_IMG_URL}" />
""")

st.html("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
[data-testid="stHeader"] {display: none !important;}
[data-testid="stToolbar"] {visibility: hidden !important;}
[data-testid="stStatusWidget"] {visibility: hidden !important;}
[data-testid="stDecoration"] {visibility: hidden !important;}
[data-testid="stSidebar"] {display: none !important;}
.stApp { padding-bottom: 46px; }

/* ── Tight, centred page layout (no wide empty gutters) ── */
.block-container, [data-testid="stMainBlockContainer"] {
    padding: 0.75rem 1.75rem 4.25rem 1.75rem !important;
    max-width: 1480px !important;
}
[data-testid="stVerticalBlock"] { gap: 0.6rem; }
[data-testid="stHorizontalBlock"] { gap: 0.9rem; }
h1, h2, h3, h4, h5 { margin: 0 !important; padding: 0.15rem 0 !important; }
hr { margin: 0.4rem 0 !important; }

/* Zero-height helper frames (cookie manager etc.) must not leave gaps */
[data-testid="stElementContainer"]:has(iframe[height="0"]),
.element-container:has(iframe[height="0"]),
[data-testid="stElementContainer"]:has(> [data-testid="stHtml"]:empty) {
    position: absolute !important; width: 0 !important; height: 0 !important;
    overflow: hidden !important; margin: 0 !important; padding: 0 !important;
}
[data-testid="stElementContainer"]:has(> [data-testid="stHtml"] > script),
[data-testid="stElementContainer"]:has(.fa-ibi-footer),
[data-testid="stElementContainer"]:has(> [data-testid="stHtml"] > meta),
[data-testid="stElementContainer"]:has(.fa-hidden-meta) {
    position: absolute !important; height: 0 !important; margin: 0 !important; overflow: visible !important;
}

/* ── Brand header ── */
.fa-brand { display: flex; align-items: center; gap: 10px; }
.fa-brand-logo {
    width: 38px; height: 38px; border-radius: 10px; flex: 0 0 auto;
    background: linear-gradient(135deg, #ff8c00, #ff4b4b);
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; color: #fff; font-size: 15px; letter-spacing: .5px;
}
.fa-brand-title { font-size: 1.35rem; font-weight: 750; color: #f5f5f5; line-height: 1.1; }
.fa-brand-sub { font-size: 0.78rem; color: #9ca3af; }

.fa-section-title {
    font-size: 0.95rem; font-weight: 700; color: #e5e7eb;
    display: flex; align-items: center; gap: 6px; margin-bottom: 2px;
}
.fa-muted { color: #9ca3af; font-size: 0.8rem; }

@keyframes faIbiFadeIn {
    0% { opacity: 0; transform: translateY(3px); }
    100% { opacity: 1; transform: translateY(0); }
}

.main-workspace-content, .audit-page-content, .licence-preview-card, .doc-preview-card, .fa-vehicle-card {
    animation: faIbiFadeIn 0.22s ease-out forwards;
}

.licence-preview-card {
    background-color: #1a1c23;
    border: 1px solid #2e323e;
    border-radius: 8px;
    padding: 12px;
    max-width: 420px;
    margin-top: 4px;
    margin-bottom: 4px;
}
.licence-preview-card img {
    max-width: 100% !important;
    max-height: 260px !important;
    object-fit: contain !important;
    border-radius: 4px;
}
[data-testid="stImage"] img { border-radius: 6px; }
.doc-preview-card [data-testid="stImage"] img, [data-testid="stImage"] img.doc-page {
    box-shadow: 0 6px 22px rgba(0,0,0,.45);
}

/* ── Selected vehicle card ── */
.fa-vehicle-card {
    background: linear-gradient(180deg, #1c1f27, #171920);
    border: 1px solid #2e323e; border-radius: 10px; padding: 12px 14px;
}
.fa-vehicle-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; }
.fa-plate {
    background: #f7d117; color: #111; font-weight: 800; letter-spacing: 1.5px;
    border-radius: 5px; padding: 3px 10px; font-size: 15px; font-family: "Arial Black", Arial, sans-serif;
    border: 1px solid #c9a80e;
}
.fa-vehicle-name { font-weight: 700; color: #f3f4f6; font-size: 14px; }
.fa-badge {
    font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 999px;
    background: #1e3a2b; color: #43d978; border: 1px solid #2d5a3f; white-space: nowrap;
}
.fa-spec-grid {
    display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; margin-top: 10px;
}
.fa-spec { background: #12141a; border: 1px solid #262a35; border-radius: 7px; padding: 6px 8px; }
.fa-spec-label { font-size: 10px; color: #8b93a3; text-transform: uppercase; letter-spacing: .5px; }
.fa-spec-value { font-size: 13px; color: #f3f4f6; font-weight: 650; }

/* ── Audit log stat tiles ── */
.fa-stat-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
.fa-stat { background: #1a1c23; border: 1px solid #2e323e; border-radius: 10px; padding: 10px 12px; }
.fa-stat-label { font-size: 11px; color: #9ca3af; text-transform: uppercase; letter-spacing: .5px; }
.fa-stat-value { font-size: 22px; color: #f9fafb; font-weight: 750; line-height: 1.2; }

/* ── Mobile ── */
@media (max-width: 640px) {
    .block-container, [data-testid="stMainBlockContainer"] {
        padding: 0.6rem 0.7rem 4.25rem 0.7rem !important;
    }
    .fa-brand-title { font-size: 1.1rem; }
    .fa-brand-sub { display: none; }
    .fa-spec-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .fa-stat-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .licence-preview-card { max-width: 100%; }
    [data-testid="stHorizontalBlock"] { gap: 0.5rem; }
    .fa-ibi-footer { font-size: 12px !important; }
    /* Bigger touch targets */
    .stButton button, .stDownloadButton button, .stLinkButton a { min-height: 44px; }
    input, textarea { font-size: 16px !important; } /* stops iOS zooming into fields */
}

@media (prefers-reduced-motion: reduce) {
    .main-workspace-content, .audit-page-content, .licence-preview-card, .doc-preview-card, .fa-vehicle-card {
        animation: none !important;
        transition: none !important;
    }
}

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
    z-index: 999990;
}
.fa-ibi-footer a {
    color: #ff8c00;
    font-weight: 600;
    text-decoration: none;
}
.fa-ibi-footer a:hover { text-decoration: underline; }
</style>
""")

st.html("""
<div class="fa-ibi-footer">
    Powered By <a href="https://virtualcarhire.pages.dev/" target="_blank" rel="noopener">&nbsp;Virtual Car Hire</a>
</div>
""")

# ─────────────────────────────────────────────
#  AUTO-DISMISSING NOTIFICATIONS
#  Uses Streamlit toasts: they float over the page (no layout jumps),
#  work on mobile and dismiss themselves.
# ─────────────────────────────────────────────
_TOAST_ICONS = {
    "success": ":material/check_circle:",
    "info": ":material/info:",
    "warning": ":material/warning:",
    "error": ":material/error:",
}

def notify(message: str, kind: str = "success", seconds: int = 10):
    message = re.sub(r"^[✅⚠️🚫ℹ️\s]+", "", str(message or "")).strip()
    if not message:
        return
    try:
        st.toast(message, icon=_TOAST_ICONS.get(kind, _TOAST_ICONS["success"]))
    except Exception:
        pass

def queue_notice(message: str, kind: str = "success"):
    """Show a toast on the next run (use from callbacks / before st.rerun)."""
    st.session_state.setdefault("_pending_notices", []).append((message, kind))

def flush_notices():
    for message, kind in st.session_state.pop("_pending_notices", []) or []:
        notify(message, kind)

# ─────────────────────────────────────────────
#  REAL COOKIE-BASED AUTH (no URL params, no full-page reload hacks)
# ─────────────────────────────────────────────
AUTH_COOKIE_NAME = "fa_ibi_auth"
AUTH_COOKIE_DAYS = 30

if stx is not None:
    try:
        cookie_manager = stx.CookieManager()
    except Exception:
        cookie_manager = None
else:
    cookie_manager = None

if cookie_manager is None and stx is None:
    st.warning(
        "⚠️ `extra-streamlit-components` isn't installed, so login can't persist "
        "across refreshes. Add `extra-streamlit-components` to requirements.txt "
        "and redeploy to fix this.",
        icon="⚠️",
    )

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated and cookie_manager is not None:
    try:
        cookies = cookie_manager.get_all()
        if isinstance(cookies, dict) and cookies.get(AUTH_COOKIE_NAME) == "true":
            st.session_state.authenticated = True
            st.rerun()
    except Exception:
        pass


# Source: "VCH_Car_Fleet_01092026.numbers" (Sheet 1). Rent is the weekly hire
# price in GBP, deposit in GBP, miles = monthly mileage allowance.
FLEET_VEHICLES = [
    {"reg": "KN73 XLB", "make": "MERCEDES-BENZ", "model_name": "EQE", "model": "MERCEDES-BENZ EQE", "category": "Mercedes-Benz", "fuel": "Electric", "year": 2023, "rent": 440, "deposit": 1000, "miles": 4500, "term": "8 Weeks"},
    {"reg": "KN73 XLA", "make": "MERCEDES-BENZ", "model_name": "EQE", "model": "MERCEDES-BENZ EQE", "category": "Mercedes-Benz", "fuel": "Electric", "year": 2023, "rent": 440, "deposit": 1000, "miles": 4000, "term": "8 Weeks"},
    {"reg": "KU73 MVW", "make": "MERCEDES-BENZ", "model_name": "EQE", "model": "MERCEDES-BENZ EQE", "category": "Mercedes-Benz", "fuel": "Electric", "year": 2023, "rent": 440, "deposit": 1000, "miles": 4000, "term": "8 Weeks"},
    {"reg": "WH74 EJF", "make": "MERCEDES-BENZ", "model_name": "EQE", "model": "MERCEDES-BENZ EQE", "category": "Mercedes-Benz", "fuel": "Electric", "year": 2024, "rent": 440, "deposit": 1000, "miles": 4000, "term": "8 Weeks"},
    {"reg": "WG74 KFJ", "make": "MERCEDES-BENZ", "model_name": "EQE", "model": "MERCEDES-BENZ EQE", "category": "Mercedes-Benz", "fuel": "Electric", "year": 2024, "rent": 440, "deposit": 1000, "miles": 4000, "term": "8 Weeks"},
    {"reg": "KR74 WDL", "make": "MERCEDES-BENZ", "model_name": "EQE", "model": "MERCEDES-BENZ EQE", "category": "Mercedes-Benz", "fuel": "Electric", "year": 2024, "rent": 440, "deposit": 1000, "miles": 4000, "term": "8 Weeks"},
    {"reg": "EN73 UBZ", "make": "MERCEDES-BENZ", "model_name": "EQE", "model": "MERCEDES-BENZ EQE", "category": "Mercedes-Benz", "fuel": "Electric", "year": 2023, "rent": 440, "deposit": 1000, "miles": 4000, "term": "8 Weeks"},
    {"reg": "WN20 NKU", "make": "MERCEDES-BENZ", "model_name": "E300", "model": "MERCEDES-BENZ E300", "category": "Mercedes-Benz", "fuel": "Plug-in-Hybrid", "year": 2020, "rent": 280, "deposit": 500, "miles": 5000, "term": "8 Weeks"},
    {"reg": "BD20 XPU", "make": "MERCEDES-BENZ", "model_name": "E300", "model": "MERCEDES-BENZ E300", "category": "Mercedes-Benz", "fuel": "Plug-in-Hybrid", "year": 2020, "rent": 280, "deposit": 500, "miles": 5000, "term": "8 Weeks"},
    {"reg": "GY69 NWL", "make": "MERCEDES-BENZ", "model_name": "E300", "model": "MERCEDES-BENZ E300", "category": "Mercedes-Benz", "fuel": "Plug-in-Hybrid", "year": 2019, "rent": 280, "deposit": 500, "miles": 5000, "term": "8 Weeks"},
    {"reg": "KT68 VYM", "make": "MERCEDES-BENZ", "model_name": "E220D", "model": "MERCEDES-BENZ E220D", "category": "Mercedes-Benz", "fuel": "Diesel", "year": 2018, "rent": 270, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "FX19 FXC", "make": "MERCEDES-BENZ", "model_name": "E220D", "model": "MERCEDES-BENZ E220D", "category": "Mercedes-Benz", "fuel": "Diesel", "year": 2019, "rent": 270, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "CA19 UTF", "make": "MERCEDES-BENZ", "model_name": "E220D", "model": "MERCEDES-BENZ E220D", "category": "Mercedes-Benz", "fuel": "Diesel", "year": 2019, "rent": 270, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "OWN19 XNX", "make": "MERCEDES-BENZ", "model_name": "E220D", "model": "MERCEDES-BENZ E220D", "category": "Mercedes-Benz", "fuel": "Diesel", "year": 2019, "rent": 270, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "BV19 WNA", "make": "MERCEDES-BENZ", "model_name": "E220D", "model": "MERCEDES-BENZ E220D", "category": "Mercedes-Benz", "fuel": "Diesel", "year": 2018, "rent": 270, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "BX19 ZMY", "make": "MERCEDES-BENZ", "model_name": "E220D", "model": "MERCEDES-BENZ E220D", "category": "Mercedes-Benz", "fuel": "Diesel", "year": 2019, "rent": 270, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "BU19 ACJ", "make": "MERCEDES-BENZ", "model_name": "E220D", "model": "MERCEDES-BENZ E220D", "category": "Mercedes-Benz", "fuel": "Diesel", "year": 2019, "rent": 270, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "WD19 SNN", "make": "MERCEDES-BENZ", "model_name": "E220D", "model": "MERCEDES-BENZ E220D", "category": "Mercedes-Benz", "fuel": "Diesel", "year": 2019, "rent": 270, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "KP69 WOR", "make": "MERCEDES-BENZ", "model_name": "E220D", "model": "MERCEDES-BENZ E220D", "category": "Mercedes-Benz", "fuel": "Diesel", "year": 2019, "rent": 270, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "LR69 UCG", "make": "MERCEDES-BENZ", "model_name": "E220D", "model": "MERCEDES-BENZ E220D", "category": "Mercedes-Benz", "fuel": "Diesel", "year": 2019, "rent": 270, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "HX19 VZG", "make": "MERCEDES-BENZ", "model_name": "E220D", "model": "MERCEDES-BENZ E220D", "category": "Mercedes-Benz", "fuel": "Diesel", "year": 2018, "rent": 270, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "HX19 VXB", "make": "MERCEDES-BENZ", "model_name": "E220D", "model": "MERCEDES-BENZ E220D", "category": "Mercedes-Benz", "fuel": "Diesel", "year": 2019, "rent": 270, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "OU68 SXP", "make": "MERCEDES-BENZ", "model_name": "E220D", "model": "MERCEDES-BENZ E220D", "category": "Mercedes-Benz", "fuel": "Diesel", "year": 2018, "rent": 270, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "BN68 MYZ", "make": "MERCEDES-BENZ", "model_name": "E220D", "model": "MERCEDES-BENZ E220D", "category": "Mercedes-Benz", "fuel": "Diesel", "year": 2018, "rent": 270, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "RO68 NXP", "make": "MERCEDES-BENZ", "model_name": "E220D", "model": "MERCEDES-BENZ E220D", "category": "Mercedes-Benz", "fuel": "Diesel", "year": 2018, "rent": 270, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "MV68 OHB", "make": "MERCEDES-BENZ", "model_name": "E220D", "model": "MERCEDES-BENZ E220D", "category": "Mercedes-Benz", "fuel": "Diesel", "year": 2018, "rent": 270, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "MV68 OGF", "make": "MERCEDES-BENZ", "model_name": "E220D", "model": "MERCEDES-BENZ E220D", "category": "Mercedes-Benz", "fuel": "Diesel", "year": 2018, "rent": 270, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "BN68 NHP", "make": "MERCEDES-BENZ", "model_name": "E220D", "model": "MERCEDES-BENZ E220D", "category": "Mercedes-Benz", "fuel": "Diesel", "year": 2018, "rent": 270, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "AK69 CKJ", "make": "MERCEDES-BENZ", "model_name": "E220D", "model": "MERCEDES-BENZ E220D", "category": "Mercedes-Benz", "fuel": "Diesel", "year": 2019, "rent": 270, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "BL19 JDZ", "make": "MERCEDES-BENZ", "model_name": "E220D", "model": "MERCEDES-BENZ E220D", "category": "Mercedes-Benz", "fuel": "Diesel", "year": 2019, "rent": 270, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "PO18 UTT", "make": "MERCEDES-BENZ", "model_name": "E220D", "model": "MERCEDES-BENZ E220D", "category": "Mercedes-Benz", "fuel": "Diesel", "year": 2018, "rent": 270, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "BN17 CVA", "make": "MERCEDES-BENZ", "model_name": "VITO", "model": "MERCEDES-BENZ VITO", "category": "Mercedes-Benz", "fuel": "Diesel", "year": 2017, "rent": 370, "deposit": 500, "miles": 5000, "term": "8 Weeks"},
    {"reg": "KO18 HKE", "make": "MERCEDES-BENZ", "model_name": "VITO", "model": "MERCEDES-BENZ VITO", "category": "Mercedes-Benz", "fuel": "Diesel", "year": 2018, "rent": 370, "deposit": 500, "miles": 5000, "term": "8 Weeks"},
    {"reg": "SF19 WPW", "make": "MERCEDES-BENZ", "model_name": "VITO", "model": "MERCEDES-BENZ VITO", "category": "Mercedes-Benz", "fuel": "Diesel", "year": 2018, "rent": 400, "deposit": 500, "miles": 5000, "term": "8 Weeks"},
    {"reg": "KT18 ATF", "make": "MERCEDES-BENZ", "model_name": "VITO", "model": "MERCEDES-BENZ VITO", "category": "Mercedes-Benz", "fuel": "Diesel", "year": 2018, "rent": 370, "deposit": 500, "miles": 5000, "term": "8 Weeks"},
    {"reg": "KW18 TMV", "make": "MERCEDES-BENZ", "model_name": "VITO", "model": "MERCEDES-BENZ VITO", "category": "Mercedes-Benz", "fuel": "Diesel", "year": 2018, "rent": 370, "deposit": 500, "miles": 5000, "term": "8 Weeks"},
    {"reg": "WR16 UED", "make": "MERCEDES-BENZ", "model_name": "VITO", "model": "MERCEDES-BENZ VITO", "category": "Mercedes-Benz", "fuel": "Diesel", "year": 2016, "rent": 350, "deposit": 500, "miles": 5000, "term": "8 Weeks"},
    {"reg": "WR19 UFG", "make": "MERCEDES-BENZ", "model_name": "VITO", "model": "MERCEDES-BENZ VITO", "category": "Mercedes-Benz", "fuel": "Diesel", "year": 2019, "rent": 400, "deposit": 500, "miles": 5000, "term": "8 Weeks"},
    {"reg": "KF19 UCJ", "make": "TOYOTA", "model_name": "COROLLA", "model": "TOYOTA COROLLA", "category": "Toyota", "fuel": "Petrol", "year": 2019, "rent": 210, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "KF19 UCM", "make": "TOYOTA", "model_name": "COROLLA", "model": "TOYOTA COROLLA", "category": "Toyota", "fuel": "Petrol", "year": 2019, "rent": 210, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "KF19 UCN", "make": "TOYOTA", "model_name": "COROLLA", "model": "TOYOTA COROLLA", "category": "Toyota", "fuel": "Petrol", "year": 2019, "rent": 210, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "LT69 GSU", "make": "TOYOTA", "model_name": "COROLLA", "model": "TOYOTA COROLLA", "category": "Toyota", "fuel": "Petrol", "year": 2019, "rent": 210, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "LT69 GSY", "make": "TOYOTA", "model_name": "COROLLA", "model": "TOYOTA COROLLA", "category": "Toyota", "fuel": "Petrol", "year": 2019, "rent": 210, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "LT69 GSZ", "make": "TOYOTA", "model_name": "COROLLA", "model": "TOYOTA COROLLA", "category": "Toyota", "fuel": "Petrol", "year": 2019, "rent": 210, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "LT69 GTU", "make": "TOYOTA", "model_name": "COROLLA", "model": "TOYOTA COROLLA", "category": "Toyota", "fuel": "Petrol", "year": 2019, "rent": 210, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "LL68 CRZ", "make": "TOYOTA", "model_name": "AURIS", "model": "TOYOTA AURIS", "category": "Toyota", "fuel": "Hybrid", "year": 2018, "rent": 210, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "LL68 CRV", "make": "TOYOTA", "model_name": "AURIS", "model": "TOYOTA AURIS", "category": "Toyota", "fuel": "Hybrid", "year": 2018, "rent": 210, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "LM68 KRD", "make": "TOYOTA", "model_name": "AURIS", "model": "TOYOTA AURIS", "category": "Toyota", "fuel": "Hybrid", "year": 2018, "rent": 210, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "LM68 KRG", "make": "TOYOTA", "model_name": "AURIS", "model": "TOYOTA AURIS", "category": "Toyota", "fuel": "Hybrid", "year": 2018, "rent": 210, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "LM68 KRJ", "make": "TOYOTA", "model_name": "AURIS", "model": "TOYOTA AURIS", "category": "Toyota", "fuel": "Hybrid", "year": 2018, "rent": 210, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "LM68 KRO", "make": "TOYOTA", "model_name": "AURIS", "model": "TOYOTA AURIS", "category": "Toyota", "fuel": "Hybrid", "year": 2019, "rent": 210, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "LM68 KRU", "make": "TOYOTA", "model_name": "AURIS", "model": "TOYOTA AURIS", "category": "Toyota", "fuel": "Hybrid", "year": 2018, "rent": 210, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "LR16 VTY", "make": "TOYOTA", "model_name": "PRIUS", "model": "TOYOTA PRIUS", "category": "Toyota", "fuel": "Hybrid", "year": 2016, "rent": 200, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "AF70 MWK", "make": "TESLA", "model_name": "MODEL 3", "model": "TESLA MODEL 3", "category": "Tesla", "fuel": "Electric", "year": 2020, "rent": 260, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "BJ20 LGX", "make": "TESLA", "model_name": "MODEL 3", "model": "TESLA MODEL 3", "category": "Tesla", "fuel": "Electric", "year": 2020, "rent": 260, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "MJ69 YPN", "make": "TESLA", "model_name": "MODEL 3", "model": "TESLA MODEL 3", "category": "Tesla", "fuel": "Electric", "year": 2019, "rent": 260, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "BK70 WYM", "make": "TESLA", "model_name": "MODEL 3", "model": "TESLA MODEL 3", "category": "Tesla", "fuel": "Electric", "year": 2020, "rent": 260, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "BT69 TEJ", "make": "TESLA", "model_name": "MODEL 3", "model": "TESLA MODEL 3", "category": "Tesla", "fuel": "Electric", "year": 2019, "rent": 260, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "LA69 AXF", "make": "TESLA", "model_name": "MODEL 3", "model": "TESLA MODEL 3", "category": "Tesla", "fuel": "Electric", "year": 2019, "rent": 260, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "LA69 AYB", "make": "TESLA", "model_name": "MODEL 3", "model": "TESLA MODEL 3", "category": "Tesla", "fuel": "Electric", "year": 2019, "rent": 260, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "LB69 OFY", "make": "TESLA", "model_name": "MODEL 3", "model": "TESLA MODEL 3", "category": "Tesla", "fuel": "Electric", "year": 2019, "rent": 260, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "LD20 COJ", "make": "TESLA", "model_name": "MODEL 3", "model": "TESLA MODEL 3", "category": "Tesla", "fuel": "Electric", "year": 2020, "rent": 260, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "LD20 FCE", "make": "TESLA", "model_name": "MODEL 3", "model": "TESLA MODEL 3", "category": "Tesla", "fuel": "Electric", "year": 2020, "rent": 260, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "WN20 EJA", "make": "TESLA", "model_name": "MODEL 3", "model": "TESLA MODEL 3", "category": "Tesla", "fuel": "Electric", "year": 2020, "rent": 260, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "BN20 WJL", "make": "JAGUAR", "model_name": "I-PACE", "model": "JAGUAR I-PACE", "category": "Jaguar", "fuel": "Electric", "year": 2020, "rent": 270, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "BN20 XMX", "make": "JAGUAR", "model_name": "I-PACE", "model": "JAGUAR I-PACE", "category": "Jaguar", "fuel": "Electric", "year": 2020, "rent": 270, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "GX70 UBD", "make": "JAGUAR", "model_name": "I-PACE", "model": "JAGUAR I-PACE", "category": "Jaguar", "fuel": "Electric", "year": 2020, "rent": 270, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "HK73 SXU", "make": "HYUNDAI", "model_name": "SANTA FE", "model": "HYUNDAI SANTA FE", "category": "Hyundai", "fuel": "Plug-in-Hybrid", "year": 2023, "rent": 330, "deposit": 500, "miles": 5000, "term": "8 Weeks"},
    {"reg": "LB76 BUJ", "make": "HYUNDAI", "model_name": "SANTA FE", "model": "HYUNDAI SANTA FE", "category": "Hyundai", "fuel": "Plug-in-Hybrid", "year": 2026, "rent": 370, "deposit": 500, "miles": 5000, "term": "8 Weeks"},
    {"reg": "LB76 BWF", "make": "HYUNDAI", "model_name": "SANTA FE", "model": "HYUNDAI SANTA FE", "category": "Hyundai", "fuel": "Plug-in-Hybrid", "year": 2026, "rent": 370, "deposit": 500, "miles": 5000, "term": "8 Weeks"},
    {"reg": "EF70 ZPZ", "make": "HYUNDAI", "model_name": "IONIQ", "model": "HYUNDAI IONIQ", "category": "Hyundai", "fuel": "Plug-in-Hybrid", "year": 2020, "rent": 210, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "EF70 ZPY", "make": "HYUNDAI", "model_name": "IONIQ", "model": "HYUNDAI IONIQ", "category": "Hyundai", "fuel": "Plug-in-Hybrid", "year": 2020, "rent": 210, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "EF70 ZVM", "make": "HYUNDAI", "model_name": "IONIQ", "model": "HYUNDAI IONIQ", "category": "Hyundai", "fuel": "Plug-in-Hybrid", "year": 2020, "rent": 210, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "EF70 ZYA", "make": "HYUNDAI", "model_name": "IONIQ", "model": "HYUNDAI IONIQ", "category": "Hyundai", "fuel": "Plug-in-Hybrid", "year": 2020, "rent": 210, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "EF70 ZYD", "make": "HYUNDAI", "model_name": "IONIQ", "model": "HYUNDAI IONIQ", "category": "Hyundai", "fuel": "Plug-in-Hybrid", "year": 2020, "rent": 210, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "GU72 DVP", "make": "HYUNDAI", "model_name": "IONIQ", "model": "HYUNDAI IONIQ", "category": "Hyundai", "fuel": "Plug-in-Hybrid", "year": 2022, "rent": 210, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "FL70 EUV", "make": "HYUNDAI", "model_name": "IONIQ", "model": "HYUNDAI IONIQ", "category": "Hyundai", "fuel": "Plug-in-Hybrid", "year": 2020, "rent": 210, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "EK70 BKJ", "make": "HYUNDAI", "model_name": "IONIQ", "model": "HYUNDAI IONIQ", "category": "Hyundai", "fuel": "Plug-in-Hybrid", "year": 2020, "rent": 210, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "YC72 HZM", "make": "MG", "model_name": "5 EV", "model": "MG 5 EV", "category": "MG", "fuel": "Electric", "year": 2022, "rent": 200, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "YF22 UVZ", "make": "MG", "model_name": "5 EV", "model": "MG 5 EV", "category": "MG", "fuel": "Electric", "year": 2022, "rent": 200, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "YF22 UWK", "make": "MG", "model_name": "5 EV", "model": "MG 5 EV", "category": "MG", "fuel": "Electric", "year": 2022, "rent": 200, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "YF22 UWM", "make": "MG", "model_name": "5 EV", "model": "MG 5 EV", "category": "MG", "fuel": "Electric", "year": 2022, "rent": 200, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "YF22 UWT", "make": "MG", "model_name": "5 EV", "model": "MG 5 EV", "category": "MG", "fuel": "Electric", "year": 2022, "rent": 200, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "YF22 UXC", "make": "MG", "model_name": "5 EV", "model": "MG 5 EV", "category": "MG", "fuel": "Electric", "year": 2022, "rent": 200, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "YF22 UXY", "make": "MG", "model_name": "5 EV", "model": "MG 5 EV", "category": "MG", "fuel": "Electric", "year": 2022, "rent": 200, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "YG71 LCZ", "make": "MG", "model_name": "5 EV", "model": "MG 5 EV", "category": "MG", "fuel": "Electric", "year": 2021, "rent": 200, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "YH76Z LWF", "make": "MG", "model_name": "S9", "model": "MG S9", "category": "MG", "fuel": "Plug-in-Hybrid", "year": 2026, "rent": 300, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "MD25 AYY", "make": "FORD", "model_name": "TOURNEO CUSTOM", "model": "FORD TOURNEO CUSTOM", "category": "Ford", "fuel": "Electric", "year": 2025, "rent": 430, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "MD25 DDZ", "make": "FORD", "model_name": "TOURNEO CUSTOM", "model": "FORD TOURNEO CUSTOM", "category": "Ford", "fuel": "Electric", "year": 2025, "rent": 430, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "RX25 CME", "make": "FORD", "model_name": "TOURNEO CUSTOM", "model": "FORD TOURNEO CUSTOM", "category": "Ford", "fuel": "Electric", "year": 2025, "rent": 430, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "BK76 WJG", "make": "FORD", "model_name": "TOURNEO CUSTOM", "model": "FORD TOURNEO CUSTOM", "category": "Ford", "fuel": "Electric", "year": 2025, "rent": 430, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "BK76 VWB", "make": "FORD", "model_name": "TOURNEO CUSTOM", "model": "FORD TOURNEO CUSTOM", "category": "Ford", "fuel": "Electric", "year": 2025, "rent": 430, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
    {"reg": "BK76 WGD", "make": "FORD", "model_name": "TOURNEO CUSTOM", "model": "FORD TOURNEO CUSTOM", "category": "Ford", "fuel": "Electric", "year": 2025, "rent": 430, "deposit": 500, "miles": 5000, "term": "6 Weeks"},
]

FLEET_CATEGORIES = list(dict.fromkeys(v["category"] for v in FLEET_VEHICLES))
FLEET_BY_REG = {v["reg"]: v for v in FLEET_VEHICLES}

# ─────────────────────────────────────────────
#  PARSING AND GENERATION ENGINES
# ─────────────────────────────────────────────
def format_uk_reg(text):
    clean = re.sub(r"[^A-Za-z0-9]", "", str(text or "")).upper()
    if len(clean) < 4:
        return clean
    if re.fullmatch(r"[A-Z]{2}\d{2}[A-Z]{3}", clean):      # current style: AB12 CDE
        return f"{clean[:4]} {clean[4:]}"
    if re.search(r"\d[A-Z]{3}$", clean):                  # prefix style: A123 BCD
        return f"{clean[:-3]} {clean[-3:]}"
    if re.match(r"^[A-Z]{3}\d", clean):                   # suffix style: ABC 123D
        return f"{clean[:3]} {clean[3:]}"
    return f"{clean[:4]} {clean[4:]}".strip()

def split_make_model(s):
    parts = s.strip().split(" ", 1)
    return (parts[0].upper(), parts[1].upper()) if len(parts) == 2 else (parts[0].upper(), "")

_NAME_TITLES = {"MR", "MRS", "MS", "MISS", "DR", "MX", "SIR", "PROF"}

def clean_name(s):
    s = re.sub(r"[^A-Z '\-]", " ", str(s or "").upper())
    words = [w for w in s.split() if len(w) > 1 and not re.match(r"^\d+$", w)]
    while words and words[0].strip(".") in _NAME_TITLES:
        words = words[1:]
    return " ".join(words).strip()

def normalize_date(s: str) -> str:
    if not s: return ""
    return re.sub(r"[.\-]", "/", s.strip())


def clean_document_name(name: str, fallback: str) -> str:
    """Return a safe editable base name for a downloaded PDF."""
    value = re.sub(r'[\x00-\x1f<>:"/\\|?*]', "", str(name or ""))
    value = re.sub(r"\s+", " ", value).strip(" .")
    value = re.sub(r"\.pdf$", "", value, flags=re.IGNORECASE).strip(" .")
    if not value:
        return fallback

    words = value.split(" ")
    if len(words) >= 4 and len(words) % 2 == 0 and words[:len(words)//2] == words[len(words)//2:]:
        value = " ".join(words[:len(words)//2])
        words = value.split(" ")

    if len(words) >= 5:
        rest = words[1:]
        if len(rest) % 2 == 0 and rest[:len(rest)//2] == rest[len(rest)//2:]:
            value = " ".join([words[0]] + rest[:len(rest)//2])

    return value

def format_driver_name_for_display(name: str, reg: str = "") -> str:
    if not name or not str(name).strip():
        return ""
    clean_n = str(name).strip()
    clean_reg = re.sub(r"[^A-Za-z0-9]", "", str(reg or "")).upper()
    if clean_reg and clean_reg != "REG":
        clean_n = re.sub(re.escape(clean_reg), "", clean_n, flags=re.IGNORECASE).strip()

    clean = clean_name(clean_n)
    if not clean or clean.upper() == "DRIVER":
        return ""
    parts = clean.split("-")
    return "-".join(" ".join(w.capitalize() for w in p.split()) for p in parts)

def build_default_contract_no(name: str, reg: str) -> str:
    """Build dynamic contract number matching format: 1608/[DRIVER-NAME]/[REG]2026."""
    clean_n = str(name or "").strip()
    clean_reg = re.sub(r"[^A-Za-z0-9]", "", str(reg or "")).upper()
    if clean_reg and clean_reg != "REG":
        clean_n = re.sub(re.escape(clean_reg), "", clean_n, flags=re.IGNORECASE).strip()

    clean_n = clean_name(clean_n)
    if clean_n and clean_n.upper() != "DRIVER":
        name_part = re.sub(r"\s+", "-", clean_n).upper()
    else:
        name_part = "DRIVER"

    if clean_reg and clean_reg != "REG":
        reg_part = f"{clean_reg}2026"
    else:
        reg_part = "REG/2026"

    return f"1608/{name_part}/{reg_part}"

def build_default_doc_name(prefix: str, name: str, reg: str, fallback: str) -> str:
    """Build auto-named document filename matching: Prefix - [Customer Name] - [Registration]."""
    fmt_name = format_driver_name_for_display(name, reg)
    clean_reg = re.sub(r"[^A-Za-z0-9]", "", str(reg or "")).upper()
    has_reg = bool(clean_reg and clean_reg != "REG")

    if fmt_name and has_reg:
        doc_str = f"{prefix} - {fmt_name} - {clean_reg}"
    elif fmt_name:
        doc_str = f"{prefix} - {fmt_name}"
    elif has_reg:
        doc_str = f"{prefix} - {clean_reg}"
    else:
        return fallback

    return clean_document_name(doc_str, fallback)

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
        probe = img.copy()
        probe.thumbnail((1400, 1400))
        osd = pytesseract.image_to_osd(probe, timeout=8)
        m = re.search(r"Rotate:\s*(\d+)", osd)
        conf = re.search(r"Orientation confidence:\s*([\d.]+)", osd)
        if m and (not conf or float(conf.group(1)) >= 1.5):
            angle = int(m.group(1))
            if angle in (90, 180, 270):
                img = img.rotate(-angle, expand=True)
    except Exception:
        pass
    return img

def _lines_from_data(data: dict) -> str:
    """Rebuild line-structured text from pytesseract image_to_data output."""
    lines, order = {}, []
    n = len(data.get("text", []))
    for i in range(n):
        word = str(data["text"][i]).strip()
        if not word:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        if key not in lines:
            lines[key] = []
            order.append(key)
        lines[key].append(word)
    return "\n".join(" ".join(lines[k]) for k in order)

def _best_ocr_text(bw_img: Image.Image) -> str:
    """Run a few Tesseract page-segmentation modes and keep the most confident."""
    configs = [r"--oem 3 --psm 6", r"--oem 3 --psm 4", r"--oem 3 --psm 11"]
    best_text, best_score = "", -1.0
    for cfg in configs:
        try:
            data = pytesseract.image_to_data(bw_img, config=cfg, output_type=pytesseract.Output.DICT, timeout=12)
            confs = [float(c) for c in data.get("conf", []) if str(c) not in ("-1", "")]
            avg_conf = sum(confs) / len(confs) if confs else 0.0
            text = _lines_from_data(data)
            # Reward confident text that also contains licence field markers.
            markers = len(re.findall(r"(?:^|\s)(?:1|2|3|4[ABC]|5|8)[.,]", text))
            score = avg_conf + markers * 4
            if text.strip() and score > best_score:
                best_score, best_text = score, text
        except Exception:
            continue
    if not best_text:
        try:
            best_text = pytesseract.image_to_string(bw_img, config=r"--oem 3 --psm 6", timeout=12)
        except Exception:
            best_text = ""
    return best_text

def _largest_embedded_image(data: bytes) -> bytes | None:
    """Pull the biggest picture out of a zip-based document (docx, pptx, odt, pages...)."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            best, best_size = None, 0
            for info in zf.infolist():
                name = info.filename.lower()
                if name.endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".gif")) and info.file_size > best_size:
                    best, best_size = info, info.file_size
            if best is not None:
                return zf.read(best)
            for info in zf.infolist():
                if info.filename.lower().endswith(".pdf"):
                    return zf.read(info)
    except Exception:
        return None
    return None

def _open_image_bytes(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    try:
        img.seek(0)  # first frame of GIF / multi-page TIFF
    except Exception:
        pass
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA", "P"):
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[-1])
        return bg
    return img.convert("RGB")

def _render_pdf_page1(data: bytes) -> Image.Image:
    if pypdfium2 is None:
        raise ValueError("Uploaded PDF could not be processed because pypdfium2 is not available.")
    try:
        pdf = pypdfium2.PdfDocument(data)
        if len(pdf) == 0:
            raise ValueError("Uploaded PDF contains no pages.")
        # Process ONLY page 1 (index 0), ignore page 2+
        page1 = pdf[0]
        w, h = page1.get_size()
        scale = max(2.0, min(4.0, 2400 / max(w, h, 1)))
        return page1.render(scale=scale).to_pil().convert("RGB")
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Invalid or malformed PDF document: {e}")

def load_uploaded_image(uploaded_file) -> Image.Image:
    """Load any uploaded licence file as an RGB image.

    Accepts every common photo format (JPG, PNG, HEIC/HEIF, WEBP, AVIF, BMP,
    TIFF, GIF...), PDFs (page 1 only) and documents that embed a photo
    (Word, PowerPoint, Pages, ODT, zip...).
    """
    if isinstance(uploaded_file, Image.Image):
        return uploaded_file.copy()

    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
    data = uploaded_file.read() if hasattr(uploaded_file, "read") else uploaded_file
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)

    if not data:
        raise ValueError("Uploaded file is empty.")

    name = str(getattr(uploaded_file, "name", "") or "").lower()
    head = data[:1024]
    is_pdf = data.startswith(b"%PDF") or b"%PDF-" in head or name.endswith(".pdf")
    if is_pdf:
        if not data.startswith(b"%PDF") and b"%PDF-" in head:
            data = data[data.index(b"%PDF-"):]
        return _render_pdf_page1(data)

    try:
        return _open_image_bytes(data)
    except Exception as pil_err:
        if data[:2] == b"PK":
            inner = _largest_embedded_image(data)
            if inner:
                if inner.startswith(b"%PDF"):
                    return _render_pdf_page1(inner)
                try:
                    return _open_image_bytes(inner)
                except Exception:
                    pass
        if cv2 is not None:
            try:
                arr = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
                if arr is not None:
                    return Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))
            except Exception:
                pass
        raise ValueError(f"Unsupported or corrupted image file format: {pil_err}")

def _order_quad(pts: np.ndarray) -> np.ndarray:
    pts = pts.reshape(4, 2).astype("float32")
    s = pts.sum(axis=1); d = np.diff(pts, axis=1).ravel()
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]], dtype="float32")

def auto_crop_card(img: Image.Image) -> Image.Image:
    """Find the licence card in a photo and flatten it (perspective correction).

    Only applied when a card-shaped rectangle (ID-1 aspect ~1.586) is clearly
    found; otherwise the original image is returned untouched.
    """
    if cv2 is None:
        return img
    try:
        w0, h0 = img.size
        scale = 900.0 / max(w0, h0)
        small = img.resize((max(1, int(w0 * scale)), max(1, int(h0 * scale)))) if scale < 1 else img
        sc = scale if scale < 1 else 1.0
        arr = np.array(small.convert("L"))
        arr = cv2.GaussianBlur(arr, (5, 5), 0)
        edges = cv2.Canny(arr, 40, 130)
        edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=2)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        area_total = arr.shape[0] * arr.shape[1]
        for c in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
            area = cv2.contourArea(c)
            if area < 0.25 * area_total or area > 0.97 * area_total:
                continue
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(approx) != 4:
                continue
            quad = _order_quad(approx) / sc
            tl, tr, br, bl = quad
            wid = max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl))
            hei = max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl))
            if hei <= 0:
                continue
            ratio = wid / hei
            portrait = False
            if 0.55 < ratio < 0.75:
                portrait = True
                ratio = 1 / ratio
            if not (1.35 < ratio < 1.85):
                continue
            out_w = int(max(wid, hei) if not portrait else max(wid, hei))
            out_w = max(1000, min(2400, out_w))
            out_h = int(out_w / 1.586)
            if portrait:
                dst = np.array([[0, 0], [out_h - 1, 0], [out_h - 1, out_w - 1], [0, out_w - 1]], dtype="float32")
                size = (out_h, out_w)
            else:
                dst = np.array([[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1], [0, out_h - 1]], dtype="float32")
                size = (out_w, out_h)
            M = cv2.getPerspectiveTransform(quad.astype("float32"), dst)
            warped = cv2.warpPerspective(np.array(img), M, size, flags=cv2.INTER_CUBIC)
            out = Image.fromarray(warped)
            if portrait:
                out = out.rotate(90, expand=True)
            return out
    except Exception:
        return img
    return img

def run_ocr(uploaded_file) -> str:
    img = load_uploaded_image(uploaded_file)
    img = auto_crop_card(img)
    img = _deskew_and_orient(img)

    w, h = img.size
    target = 2400
    if max(w, h) < target:
        scale = target / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    elif max(w, h) > 3200:
        img.thumbnail((3200, 3200), Image.LANCZOS)

    gray = ImageOps.grayscale(img)
    gray = ImageOps.autocontrast(gray, cutoff=1)
    gray = ImageEnhance.Sharpness(gray).enhance(1.8)

    if cv2 is not None:
        arr = np.array(gray)
        arr = cv2.fastNlMeansDenoising(arr, h=9)
        bw_arr = cv2.adaptiveThreshold(
            arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 35, 11
        )
        bw = Image.fromarray(bw_arr)
        gray = Image.fromarray(arr)
    else:
        bw = gray.point(lambda p: 255 if p > 140 else 0)

    # OCR the thresholded and the grayscale versions; keep the one that
    # yields the most licence fields.
    text_bw = _best_ocr_text(bw)
    text_gray = _best_ocr_text(gray)

    def _score(t):
        p = parse_licence(t)
        return sum(1 for k in ("surname", "forename", "dob", "expiry", "licence", "postcode") if p.get(k)), len(t)

    return text_bw if _score(text_bw) >= _score(text_gray) else text_gray

# ─────────────────────────────────────────────
#  AZURE AI DOCUMENT INTELLIGENCE
# ─────────────────────────────────────────────
def azure_ocr_available() -> bool:
    if DocumentIntelligenceClient is None:
        return False
    try:
        return bool(get_secret("AZURE_DOCINTEL_ENDPOINT")) and bool(get_secret("AZURE_DOCINTEL_KEY"))
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

def _azure_payload(img: Image.Image) -> bytes:
    """JPEG bytes sized for best Azure accuracy while staying small and fast."""
    azure_img = img.copy()
    azure_img.thumbnail((2200, 2200), Image.LANCZOS)
    for quality in (90, 82, 72):
        buf = io.BytesIO()
        azure_img.save(buf, format="JPEG", quality=quality, optimize=True)
        data = buf.getvalue()
        if len(data) < 3_500_000:
            return data
    return data

def run_ocr_azure(uploaded_file) -> dict:
    orig_img = load_uploaded_image(uploaded_file)
    card_img = auto_crop_card(orig_img)

    try:
        client = DocumentIntelligenceClient(
            endpoint=get_secret("AZURE_DOCINTEL_ENDPOINT"),
            credential=AzureKeyCredential(get_secret("AZURE_DOCINTEL_KEY")),
        )
        poller = client.begin_analyze_document(
            "prebuilt-idDocument",
            body=_azure_payload(card_img),
            content_type="image/jpeg",
        )
        result = poller.result(timeout=45)
    except Exception as e:
        raise ValueError(f"Azure Document Intelligence error: {e}")

    if not result.documents:
        raise ValueError("Azure couldn't detect an ID document in this photo.")

    fields = result.documents[0].fields or {}
    full_address = _field_str(fields, "Address")
    postcode = extract_postcode(full_address)
    address_no_postcode = re.sub(re.escape(postcode), "", full_address, flags=re.I).strip(", ").strip() if postcode else full_address

    out = {
        "surname": clean_name(_field_str(fields, "LastName")),
        "forename": clean_name(_field_str(fields, "FirstName")),
        "dob": _field_date(fields, "DateOfBirth"),
        "expiry": _field_date(fields, "DateOfExpiration"),
        "licence": normalize_license_number(_field_str(fields, "DocumentNumber")),
        "address": normalize_address(address_no_postcode),
        "postcode": postcode.upper(),
    }

    # Azure also returns the full page text: parse it with the UK licence
    # field rules to fill anything the ID model missed.
    content = getattr(result, "content", "")
    if isinstance(content, str) and content.strip():
        backup = parse_licence(content)
        for k in ("surname", "forename", "dob", "expiry", "licence", "address", "postcode"):
            if not out.get(k) and backup.get(k):
                out[k] = backup[k]
        if out.get("licence") and not re.fullmatch(r"[A-Z9]{5}\d{6}[A-Z9]{2}[A-Z0-9]{3}", out["licence"]) and backup.get("licence"):
            out["licence"] = backup["licence"]

    try:
        out["signature_bytes"] = extract_signature_crop(result, card_img)
    except Exception:
        out["signature_bytes"] = None
    return out

def extract_signature_crop_fallback(uploaded_file) -> bytes:
    orig_img = auto_crop_card(load_uploaded_image(uploaded_file))
    orig_w, orig_h = orig_img.size
    crop_box = (
        int(0.18 * orig_w),
        int(0.73 * orig_h),
        int(0.55 * orig_w),
        int(0.90 * orig_h),
    )
    cropped_img = orig_img.crop(crop_box)
    return clean_signature_crop(cropped_img)

def scan_licence(uploaded_file) -> tuple[dict, str]:
    """Scan a licence with the best engine available. Returns (fields, engine)."""
    errors = []
    if azure_ocr_available():
        try:
            return run_ocr_azure(uploaded_file), "Azure AI"
        except Exception as e:
            errors.append(str(e))
    if pytesseract is not None:
        try:
            raw = run_ocr(uploaded_file)
            p = parse_licence(raw)
            try:
                p["signature_bytes"] = extract_signature_crop_fallback(uploaded_file)
            except Exception:
                p["signature_bytes"] = None
            return p, "Tesseract"
        except Exception as e:
            errors.append(str(e))
    if not errors:
        errors.append("No scanning engine is configured (Azure secrets missing and Tesseract not installed).")
    raise ValueError(errors[0])

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
    text = str(text or "")
    if not text:
        return y
    c.setFont(font, size)
    for line in simpleSplit(text, font, size, max_width):
        c.drawString(x, y, line)
        y -= leading
    return y

def _wrap_draw_bold_token(c, text, token, x, y, max_width, size=11, leading=14):
    """Wrap text while rendering one exact token in bold."""
    text = str(text or "")
    token = str(token or "")
    if not text:
        return y
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


def generate_permission_letter(data: dict, include_background: bool = True) -> bytes:
    """Generate Permission Letter PDF containing only the Director signature (Muhammad Sohail Qureshi).

    Note: Hirer/licence signature is intentionally omitted from this document completely.
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter, pageCompression=1)
    pw, ph = letter
    bg = _find_img("image_f4efbe"); sig = _find_img("signature")
    if not bg:
        logging.warning("Permission letter template image 'image_f4efbe' was not found by _find_img.")
    elif include_background:
        c.drawImage(bg, 0, 0, width=pw, height=ph)

    c.setFont("Helvetica", 11)
    date_str = str(data.get("date", "") or "")
    c.drawRightString(pw - 54, 595, date_str)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(pw / 2, 550, "PERMISSION LETTER")

    text_width = pw - 108
    y = 515
    c.setFont("Helvetica", 11)
    c.drawString(54, y, "To Whom It May Concern,")
    y -= 25

    policy_number = str(data.get("insurance_policy", "") or "").strip().upper()
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
    fields_list = [
        ("Vehicle Registration", str(data.get("registration", "") or "")),
        ("Make and Model", str(data.get("make_model", "") or "")),
        ("Driver Name", str(data.get("driver_name", "") or "")),
        ("Address", normalize_address(str(data.get("address", "") or ""))),
        ("Driving Licence No", str(data.get("license_no", "") or "")),
    ]
    for label, val in fields_list:
        c.drawString(54, y, f"{label} :"); c.drawString(180, y, val)
        y -= 22
    y -= 18

    c.drawString(54, y, "Hire start date. :"); c.drawString(160, y, str(data.get("start_date", "") or ""))
    y -= 15
    c.drawString(54, y, "Hire end date    :"); c.drawString(160, y, str(data.get("end_date", "") or ""))
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
    if text is None:
        text = ""
    else:
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

def generate_contract(data: dict, include_background: bool = True) -> bytes:
    buf = io.BytesIO()
    cv = canvas.Canvas(buf, pagesize=letter, pageCompression=1)
    W, H = 612, 792
    bg1, bg2 = _find_img("1"), _find_img("2")
    if not bg1:
        logging.warning("Contract Page 1 template '1' was not found by _find_img.")
    elif include_background:
        cv.drawImage(bg1, 0, 0, width=W, height=H)

    cv.setFont("Helvetica-Bold", 8.8)
    for key, (x, y, size) in CONTRACT_PAGE1_FIELDS.items():
        font_style = "Helvetica-Bold" if key in ("contract_no", "rent", "rate", "deposit", "car_make", "registration", "car_model") else "Helvetica"
        raw_val = data.get(key, "")
        if raw_val is None:
            raw_val = ""
        value = normalize_address(raw_val) if key == "address" else str(raw_val)
        _draw_fit(cv, value, x, y, base_size=size, max_width=CONTRACT_FIELD_MAXW.get(key), font=font_style)

    _stamp_signature(cv, str(data.get("owner_signature", "") or ""), page=1)
    if data.get("hirer_signature"):
        _stamp_hirer_signature(cv, data.get("hirer_signature"), spot={"x": 160, "y": 66, "width": 110, "height": 25})
    cv.showPage()

    if not bg2:
        logging.warning("Contract Page 2 template '2' was not found by _find_img.")
    elif include_background:
        cv.drawImage(bg2, 0, 0, width=W, height=H)

    for key, (x, y, size) in CONTRACT_PAGE2_FIELDS.items():
        raw_val = data.get(key, "")
        if raw_val is None:
            raw_val = ""
        _draw_fit(cv, str(raw_val), x, y, base_size=size, max_width=CONTRACT_FIELD_MAXW.get(key), font="Helvetica-Bold")

    _stamp_signature(cv, str(data.get("owner_signature", "") or ""), page=2)
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

def format_date_val(val, fallback_default=None) -> str:
    if val is None:
        if fallback_default is not None:
            return fallback_default.strftime("%d/%m/%Y") if isinstance(fallback_default, (date, datetime)) else str(fallback_default)
        return ""
    if isinstance(val, (date, datetime)):
        return val.strftime("%d/%m/%Y")
    return str(val)

def format_time_val(val) -> str:
    if val is None:
        return get_uk_now().strftime("%H:%M")
    if isinstance(val, (time, datetime)):
        return val.strftime("%H:%M")
    return str(val)

def render_pdf_to_images(pdf_bytes: bytes) -> list[Image.Image]:
    """Convert PDF bytes into PIL Images (one per page) for live full-page A4 document preview."""
    if pypdfium2 is None or not pdf_bytes:
        if pypdfium2 is None:
            logging.error("pypdfium2 module is not available.")
        if not pdf_bytes:
            logging.warning("render_pdf_to_images received empty pdf_bytes.")
        return []
    try:
        pdf = pypdfium2.PdfDocument(pdf_bytes)
        imgs = []
        for page in pdf:
            imgs.append(page.render(scale=2).to_pil().convert("RGB"))
        return imgs
    except Exception as e:
        logging.exception("Failed to render PDF bytes to images with pypdfium2: %s", e)
        return []

PREVIEW_SCALE = 1.6  # ~980px wide pages: sharp on retina phones, quick to send

@functools.lru_cache(maxsize=8)
def _template_preview(base_name: str, size: tuple) -> Image.Image | None:
    path = _find_img(base_name)
    if not path:
        return None
    with Image.open(path) as im:
        if im.mode in ("RGBA", "LA", "P"):
            rgba = im.convert("RGBA")
            bg = Image.new("RGB", rgba.size, (255, 255, 255))
            bg.paste(rgba, mask=rgba.split()[-1])
            im2 = bg
        else:
            im2 = im.convert("RGB")
        return im2.resize(size, Image.LANCZOS)

def render_fast_preview(kind: str, data: dict) -> list[bytes]:
    """Fast live preview: draw only the typed fields to a transparent layer and
    lay it over a pre-scaled copy of the template (≈5x faster than rasterising
    the full PDF). Returns JPEG bytes per page."""
    templates = {"permission": ["image_f4efbe"], "contract": ["1", "2"]}[kind]
    gen = generate_permission_letter if kind == "permission" else generate_contract
    pages_out = []
    try:
        pdf_bytes = gen(data, include_background=False)
        pdf = pypdfium2.PdfDocument(pdf_bytes) if pypdfium2 is not None else None
    except Exception:
        logging.exception("Fast preview generation failed")
        pdf = None
    if pdf is None:
        imgs = render_pdf_to_images(gen(data))
    else:
        imgs = []
        for idx, page in enumerate(pdf):
            overlay = page.render(scale=PREVIEW_SCALE, fill_color=(255, 255, 255, 0), may_draw_forms=False).to_pil().convert("RGBA")
            base = _template_preview(templates[idx], overlay.size) if idx < len(templates) else None
            if base is None:
                base = Image.new("RGB", overlay.size, (255, 255, 255))
            page_img = base.copy()
            page_img.paste(overlay, mask=overlay.split()[-1])
            imgs.append(page_img)
    for img in imgs:
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=86, optimize=False)
        pages_out.append(buf.getvalue())
    return pages_out

@st.cache_data(max_entries=48, show_spinner=False)
def cached_preview(kind: str, data_json: str, hirer_sig: bytes | None = None) -> list[bytes]:
    data = json.loads(data_json)
    if hirer_sig:
        data["hirer_signature"] = hirer_sig
    return render_fast_preview(kind, data)

# ─────────────────────────────────────────────
#  AUDIT LOG DATA (local file + Supabase, merged)
# ─────────────────────────────────────────────
_STORAGE_PREFIX_RE = re.compile(r"^\d{8}_\d{6}_")

def _to_uk_timestamp(value: str) -> str:
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.astimezone(ZoneInfo("Europe/London"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(value)[:19].replace("T", " ")

def _fetch_remote_audit_rows() -> list[dict]:
    client = get_supabase_client()
    if client is None:
        return []
    try:
        res = client.table("audit_logs").select("*").order("timestamp", desc=True).limit(3000).execute()
        rows = res.data or []
        return [
            {
                "timestamp": _to_uk_timestamp(r.get("timestamp", "")) if "T" in str(r.get("timestamp", "")) else str(r.get("timestamp", "")),
                "event_type": r.get("event_type", "") or "",
                "doc_name": r.get("doc_name", "") or "",
                "details": r.get("details", "") or "",
                "file_path": r.get("file_path", "") or "",
            }
            for r in rows
        ]
    except Exception:
        return []

def _fetch_document_rows() -> list[dict]:
    """Every document ever generated is also recorded in `driver_documents`,
    which survives app restarts — use it to rebuild the history."""
    client = get_supabase_client()
    if client is None:
        return []
    try:
        res = client.table("driver_documents").select("*").order("created_at", desc=True).limit(3000).execute()
        out = []
        for r in res.data or []:
            fn = r.get("file_name", "") or ""
            doc_type = r.get("doc_type", "") or "Document"
            driver, reg = r.get("driver_ref", "") or "", r.get("vehicle_reg", "") or ""
            out.append({
                "timestamp": _to_uk_timestamp(r.get("created_at", "")),
                "event_type": f"{doc_type} Generated",
                "doc_name": _STORAGE_PREFIX_RE.sub("", fn),
                "details": ", ".join(x for x in (f"Driver: {driver}" if driver else "", f"Reg: {reg}" if reg else "") if x),
                "file_path": r.get("file_path", "") or (f"driver_documents/{fn}" if fn else ""),
            })
        return out
    except Exception:
        return []

@st.cache_data(ttl=30, show_spinner=False)
def get_cached_audit_logs():
    local = get_audit_logs()
    remote = _fetch_remote_audit_rows()
    docs = _fetch_document_rows()

    merged, seen_keys, seen_paths = [], set(), set()
    for entry in local + remote + docs:
        fp = entry.get("file_path", "") or ""
        key = (str(entry.get("timestamp", ""))[:16], entry.get("event_type", ""), entry.get("doc_name", ""))
        if key in seen_keys or (fp and fp in seen_paths):
            continue
        seen_keys.add(key)
        if fp:
            seen_paths.add(fp)
        merged.append(entry)
    merged.sort(key=lambda e: str(e.get("timestamp", "")), reverse=True)
    return merged

@st.cache_data(ttl=3000, show_spinner=False)
def cached_signed_links(paths: tuple) -> dict:
    return create_signed_pdf_links(paths, expires_in=3600)

# ─────────────────────────────────────────────
#  GATEKEEPER SECURITY PORTAL
# ─────────────────────────────────────────────
if not st.session_state.authenticated:
    _, login_col, _ = st.columns([1, 1.3, 1])
    with login_col:
        with st.container(border=True):
            st.html("""
            <div class="fa-brand" style="margin-bottom:6px">
              <div class="fa-brand-logo">FA</div>
              <div><div class="fa-brand-title">FA-IBI Workspace</div>
              <div class="fa-brand-sub">System Security Verification</div></div>
            </div>""")
            with st.form("login_form", border=False):
                code = st.text_input("Access PIN", type="password", placeholder="Enter key…")
                submitted = st.form_submit_button("Verify Key", icon=":material/lock_open:", type="primary", width="stretch")
            if submitted:
                if code == get_secret("ACCESS_KEY", ""):
                    st.session_state.authenticated = True
                    add_audit_log("Verification PIN Entered", details="Successful Verification PIN Entry")
                    if cookie_manager is not None:
                        try:
                            cookie_manager.set(
                                AUTH_COOKIE_NAME, "true",
                                expires_at=datetime.now() + timedelta(days=AUTH_COOKIE_DAYS),
                                key="set_auth_cookie",
                            )
                        except Exception:
                            pass
                    st.rerun()
                else:
                    add_audit_log("Verification PIN Entered", details="Failed Verification PIN Entry")
                    notify("Invalid Security Verification Pin Code", "error")
    st.stop()

# ─────────────────────────────────────────────
#  SESSION STATE: one source of truth for every form field
# ─────────────────────────────────────────────
DEFAULT_HIRE_END_DATE = date(2026, 11, 27)
MANUAL_VEHICLE = "__manual__"
MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB

def default_hire_end(start: date | None = None) -> date:
    start = start or get_uk_now().date()
    return DEFAULT_HIRE_END_DATE if DEFAULT_HIRE_END_DATE >= start else start + timedelta(weeks=8)

def form_defaults() -> dict:
    today = get_uk_now().date()
    now_t = get_uk_now().time().replace(second=0, microsecond=0)
    return {
        # Permission letter
        "p_form_date": today, "p_form_ins": "HAVFL-000211", "p_form_reg": "", "p_form_mod": "",
        "p_form_name": "", "p_form_lic": "", "p_form_start": today, "p_form_end": default_hire_end(today),
        "p_form_addr": "", "perm_document_name": "Permission Letter",
        # Contract
        "c_form_no": build_default_contract_no("", ""), "c_form_name": "", "c_form_addr": "", "c_form_post": "",
        "c_form_dob": "", "c_form_date": today, "c_form_lic": "", "c_form_exp": "", "c_form_auth": "DVLA",
        "c_form_ph": "", "c_form_em": "", "c_form_rent": "250/-", "c_form_rate": "20/-", "c_form_dep": "500/-",
        "c_form_start": today, "c_form_return": default_hire_end(today),
        "c_form_start_time": now_t, "c_form_return_time": now_t,
        "c_form_mk": "", "c_form_rv": "", "c_form_mv": "",
        "c_form_hirer_sig": "Scanned Licence Signature", "c_form_owner_sig": "-- No Signature --",
        "contract_document_name": "Contract",
        # Vehicle picker
        "global_engine_fleet": MANUAL_VEHICLE, "fleet_category_filter": "All",
    }

FORM_KEYS = list(form_defaults().keys())

STATE_DEFAULTS = dict(
    ocr_name="", ocr_licence="", ocr_address="", ocr_postcode="", ocr_dob="", ocr_expiry="",
    ocr_signature_bytes=None, last_scan_id="", scan_engine="", sel_reg="", sel_make="", sel_model="",
    perm_pdf=None, perm_filename="Permission Letter", contract_pdf=None, contract_filename="Contract",
    contract_no="", _auto_perm_name="Permission Letter", _auto_contract_name="Contract",
    _auto_contract_no=build_default_contract_no("", ""),
)

def init_state():
    for k, v in STATE_DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v
    for k, v in form_defaults().items():
        if k not in st.session_state:
            st.session_state[k] = v
        else:
            # Re-assigning keeps widget values alive while the other page is open.
            st.session_state[k] = st.session_state[k]

def _ss(key, default=""):
    v = st.session_state.get(key, default)
    return default if v is None else v

def refresh_auto_names(force: bool = False):
    """Keep document names + contract number in step with driver name & reg,
    unless the user typed their own value."""
    name = _ss("p_form_name") or _ss("c_form_name") or _ss("ocr_name")
    reg = _ss("p_form_reg") or _ss("c_form_rv") or _ss("sel_reg")
    new_vals = {
        "perm_document_name": ("_auto_perm_name", build_default_doc_name("Permission", name, reg, "Permission Letter"), ("Permission Letter",)),
        "contract_document_name": ("_auto_contract_name", build_default_doc_name("Contract", name, reg, "Contract"), ("Contract",)),
        "c_form_no": ("_auto_contract_no", build_default_contract_no(name, reg), ("1608/DRIVER/REG/2026",)),
    }
    for key, (tracker, new_val, fallbacks) in new_vals.items():
        current = str(st.session_state.get(key, "") or "").strip()
        if force or not current or current == st.session_state.get(tracker) or current in fallbacks:
            st.session_state[key] = new_val
        st.session_state[tracker] = new_val
    st.session_state.perm_filename = st.session_state.get("perm_document_name") or st.session_state.perm_filename
    st.session_state.contract_filename = st.session_state.get("contract_document_name") or st.session_state.contract_filename
    st.session_state.contract_no = st.session_state.get("c_form_no", "")

def apply_vehicle(car: dict | None, notice: bool = True):
    """Fill every vehicle field on both documents from a fleet vehicle."""
    if not car:
        st.session_state.sel_reg = st.session_state.sel_make = st.session_state.sel_model = ""
        for k in ("p_form_reg", "p_form_mod", "c_form_rv", "c_form_mk", "c_form_mv"):
            st.session_state[k] = ""
        refresh_auto_names()
        return
    st.session_state.sel_reg = car["reg"]
    st.session_state.sel_make = car["make"]
    st.session_state.sel_model = car["model_name"]
    st.session_state["p_form_reg"] = car["reg"]
    st.session_state["p_form_mod"] = car["model"]
    st.session_state["c_form_rv"] = car["reg"]
    st.session_state["c_form_mk"] = car["make"]
    st.session_state["c_form_mv"] = car["model_name"]
    st.session_state["c_form_rent"] = f"{car['rent']}/-"
    st.session_state["c_form_dep"] = f"{car['deposit']}/-"
    st.session_state["global_engine_fleet"] = car["reg"]
    refresh_auto_names()
    if notice:
        queue_notice(f"{car['reg']} · {car['model']} added — £{car['rent']}/week, £{car['deposit']} deposit", "info")

def find_fleet_vehicle(reg_text: str) -> dict | None:
    compact = re.sub(r"[^A-Z0-9]", "", str(reg_text or "").upper())
    if len(compact) < 5:
        return None
    for v in FLEET_VEHICLES:
        if re.sub(r"[^A-Z0-9]", "", v["reg"]) == compact:
            return v
    return None

# ── Field-sync callbacks (Permission ⇄ Contract) ──
def _sync_name(src):
    val = st.session_state.get(src, "")
    st.session_state["p_form_name"] = val
    st.session_state["c_form_name"] = val
    refresh_auto_names()

def _sync_licence(src):
    val = str(st.session_state.get(src, "") or "").upper()
    st.session_state["p_form_lic"] = val
    st.session_state["c_form_lic"] = val

def _sync_reg(src):
    val = str(st.session_state.get(src, "") or "").upper()
    st.session_state["p_form_reg"] = val
    st.session_state["c_form_rv"] = val
    car = find_fleet_vehicle(val)
    if car and car["reg"] != st.session_state.get("sel_reg"):
        apply_vehicle(car)
        st.session_state["_needs_full_rerun"] = True
    elif not car and st.session_state.get("sel_reg") and re.sub(r"[^A-Z0-9]", "", val) != re.sub(r"[^A-Z0-9]", "", st.session_state.sel_reg):
        st.session_state.sel_reg = ""
        st.session_state["global_engine_fleet"] = MANUAL_VEHICLE
        st.session_state["_needs_full_rerun"] = True
    refresh_auto_names()

def _sync_make_model_from_perm():
    make, model = split_make_model(st.session_state.get("p_form_mod", "") or "")
    st.session_state["c_form_mk"] = make
    st.session_state["c_form_mv"] = model

def _sync_make_model_from_contract():
    st.session_state["p_form_mod"] = f"{_ss('c_form_mk')} {_ss('c_form_mv')}".strip().upper()

def _sync_address_from_perm():
    full = normalize_address(st.session_state.get("p_form_addr", ""))
    post = extract_postcode(full)
    addr = re.sub(re.escape(post), "", full, flags=re.I).strip(" ,") if post else full
    st.session_state["c_form_addr"] = normalize_address(addr)
    st.session_state["c_form_post"] = post

def _sync_address_from_contract():
    st.session_state["p_form_addr"] = get_full_address(_ss("c_form_addr"), _ss("c_form_post"))

def _sync_pair(a, b):
    st.session_state[b] = st.session_state.get(a)

def reset_workspace():
    for k, v in form_defaults().items():
        if k == "fleet_category_filter":
            continue
        st.session_state[k] = v
    for k, v in STATE_DEFAULTS.items():
        st.session_state[k] = v
    st.session_state["_scanner_nonce"] = st.session_state.get("_scanner_nonce", 0) + 1
    queue_notice("Workspace cleared — ready for the next customer.", "info")

def apply_ocr_results_to_session_state(p: dict):
    raw_name = f"{p.get('forename', '')} {p.get('surname', '')}".strip()
    client_name = format_driver_name_for_display(raw_name)
    licence_no = (p.get("licence") or "").strip()
    address = (p.get("address") or "").strip()
    postcode = (p.get("postcode") or "").strip()
    dob = (p.get("dob") or "").strip()
    expiry = (p.get("expiry") or "").strip()
    sig_bytes = p.get("signature_bytes")

    if client_name:
        st.session_state.ocr_name = client_name
        st.session_state["p_form_name"] = client_name
        st.session_state["c_form_name"] = client_name

    if licence_no:
        st.session_state.ocr_licence = licence_no
        st.session_state["p_form_lic"] = licence_no
        st.session_state["c_form_lic"] = licence_no

    if address:
        st.session_state.ocr_address = address
        st.session_state["c_form_addr"] = address

    if postcode:
        st.session_state.ocr_postcode = postcode
        st.session_state["c_form_post"] = postcode

    curr_addr = st.session_state.get("c_form_addr", st.session_state.get("ocr_address", ""))
    curr_post = st.session_state.get("c_form_post", st.session_state.get("ocr_postcode", ""))
    if curr_addr or curr_post:
        st.session_state["p_form_addr"] = get_full_address(curr_addr, curr_post)

    if dob:
        st.session_state.ocr_dob = dob
        st.session_state["c_form_dob"] = normalize_date(dob)

    if expiry:
        st.session_state.ocr_expiry = expiry
        st.session_state["c_form_exp"] = normalize_date(expiry)

    if sig_bytes:
        st.session_state.ocr_signature_bytes = sig_bytes

    curr_driver_name = st.session_state.get("p_form_name") or client_name
    curr_reg = st.session_state.get("p_form_reg") or st.session_state.get("sel_reg", "")

    perm_doc = build_default_doc_name("Permission", curr_driver_name, curr_reg, "Permission Letter")
    contract_doc = build_default_doc_name("Contract", curr_driver_name, curr_reg, "Contract")
    contract_no = build_default_contract_no(curr_driver_name, curr_reg)

    st.session_state.perm_filename = perm_doc
    st.session_state["perm_document_name"] = perm_doc
    st.session_state["_auto_perm_name"] = perm_doc

    st.session_state.contract_filename = contract_doc
    st.session_state["contract_document_name"] = contract_doc
    st.session_state["_auto_contract_name"] = contract_doc

    st.session_state.contract_no = contract_no
    st.session_state["c_form_no"] = contract_no
    st.session_state["_auto_contract_no"] = contract_no

# ─────────────────────────────────────────────
#  HEADER & NAVIGATION
# ─────────────────────────────────────────────
init_state()
query_page = st.query_params.get("page", "workspace")
if "current_page" not in st.session_state:
    st.session_state.current_page = "audit" if query_page == "audit" else "workspace"

NAV_LABELS = {"workspace": "Workspace", "audit": "Audit Logs"}

def _on_nav_change():
    choice = st.session_state.get("nav_choice")
    if choice:
        page = "audit" if choice == "Audit Logs" else "workspace"
        st.session_state.current_page = page
        st.query_params["page"] = page
    else:
        st.session_state.nav_choice = NAV_LABELS[st.session_state.current_page]

st.session_state.nav_choice = NAV_LABELS[st.session_state.current_page]

with st.container(horizontal=True, vertical_alignment="center", gap="small"):
    sub = "Document history & security log" if st.session_state.current_page == "audit" else "Permission letters & hire contracts"
    st.html(f"""
    <div class="fa-brand">
      <div class="fa-brand-logo">FA</div>
      <div><div class="fa-brand-title">FA-IBI Workspace</div><div class="fa-brand-sub">{sub}</div></div>
    </div>""", width="content")
    st.space("stretch")
    st.segmented_control(
        "Page", ["Workspace", "Audit Logs"], key="nav_choice", label_visibility="collapsed",
        on_change=_on_nav_change, required=True,
        format_func=lambda o: ("🗂️ " if o == "Workspace" else "🧾 ") + o,
    )
    if st.button("Log out", key="top_logout_btn", icon=":material/logout:"):
        st.session_state.authenticated = False
        if cookie_manager is not None:
            try:
                cookie_manager.delete(AUTH_COOKIE_NAME, key="delete_auth_cookie")
            except Exception:
                pass
        st.rerun()

flush_notices()

# ─────────────────────────────────────────────
#  AUDIT LOGS PAGE
# ─────────────────────────────────────────────
EVENT_ICONS = {
    "Contract Generated": "📄",
    "Permission Letter Generated": "✉️",
    "Licence Scanned": "🪪",
    "Saved to Google Drive": "☁️",
    "Verification PIN Entered": "🔐",
}

def _fmt_uk(ts: str) -> str:
    try:
        return datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
    except Exception:
        return ts

def render_audit_page():
    logs = get_cached_audit_logs()

    n_contract = sum(1 for l in logs if l.get("event_type") == "Contract Generated")
    n_perm = sum(1 for l in logs if l.get("event_type") == "Permission Letter Generated")
    n_scans = sum(1 for l in logs if l.get("event_type") == "Licence Scanned")
    n_failed = sum(1 for l in logs if "Failed" in str(l.get("details", "")))
    st.html(f"""
    <div class="fa-stat-grid audit-page-content">
      <div class="fa-stat"><div class="fa-stat-label">Contracts</div><div class="fa-stat-value">{n_contract}</div></div>
      <div class="fa-stat"><div class="fa-stat-label">Permission letters</div><div class="fa-stat-value">{n_perm}</div></div>
      <div class="fa-stat"><div class="fa-stat-label">Licences scanned</div><div class="fa-stat-value">{n_scans}</div></div>
      <div class="fa-stat"><div class="fa-stat-label">Failed PIN attempts</div><div class="fa-stat-value">{n_failed}</div></div>
    </div>""")

    if not logs:
        st.info("No audit log records found yet. Generated documents will appear here.", icon=":material/info:")
        return

    f1, f2 = st.columns([2, 3], vertical_alignment="bottom")
    with f1:
        search_query = st.text_input(
            "Search", placeholder="Driver name, registration, document…", key="audit_page_search",
            live=True, icon=":material/search:", label_visibility="collapsed",
        )
    with f2:
        types = sorted({l.get("event_type", "") for l in logs if l.get("event_type")})
        chosen_types = st.pills("Event type", types, selection_mode="multi", key="audit_types",
                                label_visibility="collapsed",
                                format_func=lambda t: f"{EVENT_ICONS.get(t, '•')} {t.replace(' Generated', '').replace('Verification PIN Entered', 'PIN')}")

    filtered = logs
    if chosen_types:
        filtered = [l for l in filtered if l.get("event_type") in chosen_types]
    if search_query and search_query.strip():
        q = search_query.strip().lower()
        q_compact = re.sub(r"\s+", "", q)
        filtered = [
            l for l in filtered
            if q in " ".join(str(l.get(k, "")) for k in ("timestamp", "event_type", "doc_name", "details")).lower()
            or (q_compact and q_compact in re.sub(r"\s+", "", " ".join(str(l.get(k, "")) for k in ("doc_name", "details")).lower()))
        ]

    st.caption(f"Showing {len(filtered)} of {len(logs)} records · times are UK local time")
    if not filtered:
        st.write("No matching log records found.")
        return

    link_paths = tuple(dict.fromkeys(l["file_path"] for l in filtered[:400] if l.get("file_path")))
    links = cached_signed_links(link_paths) if link_paths else {}

    rows = [{
        "When": _fmt_uk(str(l.get("timestamp", ""))),
        "Event": f"{EVENT_ICONS.get(l.get('event_type', ''), '•')} {l.get('event_type', '')}",
        "Details": l.get("details", "") or "—",
        "Document": l.get("doc_name", "") or "—",
        "PDF": links.get(l.get("file_path", ""), None),
    } for l in filtered]
    if not links:
        for r in rows:
            r.pop("PDF", None)

    st.dataframe(
        rows,
        hide_index=True,
        width="stretch",
        height=min(640, 38 + 35 * len(rows)),
        column_config={
            "When": st.column_config.TextColumn("When", width="small"),
            "Event": st.column_config.TextColumn("Event", width="medium"),
            "Details": st.column_config.TextColumn("What was processed", width="large"),
            "Document": st.column_config.TextColumn("Document", width="medium"),
            "PDF": st.column_config.LinkColumn("PDF", display_text="Open PDF", width="small"),
        },
    )

    docs = [l for l in filtered if l.get("doc_name")]
    if docs:
        with st.expander("Download a document", icon=":material/download:", expanded=not links):
            idx = st.selectbox(
                "Document", range(len(docs)), key="audit_doc_pick",
                format_func=lambda i: f"{_fmt_uk(str(docs[i].get('timestamp', '')))} — {docs[i].get('doc_name', '')}",
            )
            entry = docs[idx]
            doc_name, file_path = entry.get("doc_name", ""), entry.get("file_path", "")
            cache_key = f"audit_pdf_cache_{hashlib.md5((str(entry.get('timestamp')) + doc_name + file_path).encode()).hexdigest()}"
            if st.session_state.get(cache_key):
                st.download_button(
                    "Download PDF", data=st.session_state[cache_key],
                    file_name=doc_name if doc_name.lower().endswith(".pdf") else f"{doc_name}.pdf",
                    mime="application/pdf", key=f"dl_{cache_key}", icon=":material/download:",
                    type="primary", width="stretch", on_click="ignore",
                )
            elif st.button("Fetch PDF", key=f"fetch_{cache_key}", icon=":material/cloud_download:", width="stretch"):
                with st.spinner("Fetching PDF…"):
                    pdf_bytes = download_from_supabase_storage(doc_name, file_path)
                if pdf_bytes:
                    st.session_state[cache_key] = pdf_bytes
                    st.rerun()
                else:
                    notify("Could not retrieve this PDF from Supabase Storage.", "warning")

    if st.button("Refresh", key="audit_refresh", icon=":material/refresh:", type="tertiary"):
        get_cached_audit_logs.clear()
        cached_signed_links.clear()
        st.rerun()

if st.session_state.current_page == "audit":
    render_audit_page()
    st.stop()

# ─────────────────────────────────────────────
#  SECURED MASTER WORKSPACE
# ─────────────────────────────────────────────
@st.cache_data(max_entries=8, show_spinner=False)
def licence_thumbnail(file_bytes: bytes, name: str) -> bytes:
    buf_in = io.BytesIO(file_bytes)
    buf_in.name = name
    img = load_uploaded_image(buf_in)
    img.thumbnail((900, 900))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=85)
    return out.getvalue()

top_scan, top_fleet = st.columns([1, 1], gap="medium")

with top_scan:
    with st.container(border=True):
        st.html('<div class="fa-section-title">🪪 Driver\'s Licence Scanner</div>')
        uploaded = st.file_uploader(
            "Upload a photo, scan or PDF of the licence (front side)",
            type=None,
            max_upload_size=25,
            key=f"global_engine_scanner_{st.session_state.get('_scanner_nonce', 0)}",
            help="Any photo format (JPG, PNG, HEIC, WEBP…), PDF or document. On a phone you can take a photo directly.",
        )
        if uploaded is not None:
            file_bytes = uploaded.getvalue()
            if uploaded.size > MAX_UPLOAD_SIZE_BYTES:
                st.error("This file is too large. Please upload a file under 25 MB.")
            else:
                fid = hashlib.md5(file_bytes).hexdigest()
                if st.session_state.last_scan_id != fid:
                    with st.spinner("Reading licence…"):
                        try:
                            p, engine = scan_licence(uploaded)
                            apply_ocr_results_to_session_state(p)
                            st.session_state.scan_engine = engine
                            found = [lbl for k, lbl in (("surname", "name"), ("licence", "licence no"), ("dob", "date of birth"),
                                                         ("expiry", "expiry"), ("address", "address"), ("postcode", "postcode")) if p.get(k)]
                            add_audit_log("Licence Scanned", details=f"Driver: {st.session_state.ocr_name or 'unknown'}, Engine: {engine}, Fields: {len(found)}/6")
                            if len(found) >= 4:
                                notify(f"Licence scanned ({engine}) — please double-check the fields.", "success")
                            else:
                                notify(f"Only part of the licence could be read ({', '.join(found) or 'nothing'}). Try a sharper, flatter photo or fill in the rest.", "warning")
                        except Exception as e:
                            notify(f"Licence scan failed: {e}. Please enter the details manually.", "error")
                    st.session_state.last_scan_id = fid

                pv1, pv2 = st.columns([3, 2], vertical_alignment="center")
                with pv1:
                    try:
                        st.image(licence_thumbnail(file_bytes, uploaded.name), caption=uploaded.name, width=360)
                    except Exception as img_err:
                        st.warning(f"Unable to render licence preview: {img_err}")
                with pv2:
                    if st.session_state.ocr_signature_bytes:
                        st.caption("Signature captured")
                        st.image(st.session_state.ocr_signature_bytes, width=160)
                    if st.session_state.scan_engine:
                        st.caption(f"Read with {st.session_state.scan_engine}")
                    if st.button("Scan again", key="rescan_btn", icon=":material/refresh:", type="tertiary"):
                        st.session_state.last_scan_id = ""
                        st.rerun()
        else:
            st.html("""
            <div class="licence-preview-card" style="border: 1px dashed #3f4454; padding: 14px; text-align: center; color: #9ca3af; max-width: 100%;">
                <div style="font-size: 20px; margin-bottom: 2px;">💳</div>
                <div style="font-weight: 600; font-size: 13px; color: #d1d5db;">Licence Preview</div>
                <div style="font-size: 11px; margin-top: 2px;">Upload the licence and every field fills in automatically.</div>
            </div>""")
        if not azure_ocr_available() and pytesseract is None:
            st.caption("⚠️ No scanner engine configured — add the Azure Document Intelligence secrets.")

def _on_vehicle_pick():
    reg = st.session_state.get("global_engine_fleet")
    if reg == MANUAL_VEHICLE or reg is None:
        st.session_state["global_engine_fleet"] = MANUAL_VEHICLE
        apply_vehicle(None)
    else:
        apply_vehicle(FLEET_BY_REG.get(reg))

with top_fleet:
    with st.container(border=True):
        st.html(f'<div class="fa-section-title">🚘 Select Vehicle <span class="fa-muted">· {len(FLEET_VEHICLES)} in fleet</span></div>')
        cat = st.pills(
            "Category", ["All"] + FLEET_CATEGORIES, key="fleet_category_filter",
            label_visibility="collapsed", required=True,
        ) or "All"
        pool = FLEET_VEHICLES if cat == "All" else [v for v in FLEET_VEHICLES if v["category"] == cat]
        options = [MANUAL_VEHICLE] + [v["reg"] for v in pool]
        current = st.session_state.get("global_engine_fleet") or MANUAL_VEHICLE
        if current not in options:
            if current in FLEET_BY_REG:
                options.insert(1, current)
            else:
                st.session_state["global_engine_fleet"] = MANUAL_VEHICLE

        def _fmt_vehicle(reg):
            if reg == MANUAL_VEHICLE:
                return "✏️ Manual entry / custom vehicle"
            v = FLEET_BY_REG[reg]
            return f"{v['reg']}  ·  {v['model']}  ·  {v['fuel']}  ·  £{v['rent']}/wk"

        st.selectbox(
            f"Vehicle ({len(pool)} {'vehicles' if cat == 'All' else cat})",
            options, key="global_engine_fleet", format_func=_fmt_vehicle,
            on_change=_on_vehicle_pick, placeholder="Type a registration or model to search…",
        )

        car = FLEET_BY_REG.get(st.session_state.sel_reg)
        if car:
            st.html(f"""
            <div class="fa-vehicle-card">
              <div class="fa-vehicle-head">
                <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
                  <span class="fa-plate">{car['reg']}</span>
                  <span class="fa-vehicle-name">{car['model']}</span>
                </div>
                <span class="fa-badge">{car['category']} · {car['fuel']}</span>
              </div>
              <div class="fa-spec-grid">
                <div class="fa-spec"><div class="fa-spec-label">Rent</div><div class="fa-spec-value">£{car['rent']}/week</div></div>
                <div class="fa-spec"><div class="fa-spec-label">Deposit</div><div class="fa-spec-value">£{car['deposit']:,}</div></div>
                <div class="fa-spec"><div class="fa-spec-label">Min term</div><div class="fa-spec-value">{car['term']}</div></div>
                <div class="fa-spec"><div class="fa-spec-label">Monthly miles</div><div class="fa-spec-value">{car['miles']:,}</div></div>
                <div class="fa-spec"><div class="fa-spec-label">Fuel</div><div class="fa-spec-value">{car['fuel']}</div></div>
                <div class="fa-spec"><div class="fa-spec-label">Year</div><div class="fa-spec-value">{car['year']}</div></div>
              </div>
            </div>""")
        else:
            st.caption("Pick a fleet car to fill the registration, make, model, rent and deposit on both documents — or type them in manually below.")

# ─────────────────────────────────────────────
#  DOCUMENT DATA BUILDERS
# ─────────────────────────────────────────────
def permission_data_from_state() -> dict:
    return {
        "date": format_date_val(st.session_state.get("p_form_date"), get_uk_now().date()),
        "insurance_policy": _ss("p_form_ins").strip(),
        "registration": format_uk_reg(_ss("p_form_reg")),
        "make_model": _ss("p_form_mod").strip().upper(),
        "driver_name": _ss("p_form_name").strip().upper(),
        "address": normalize_address(_ss("p_form_addr")),
        "license_no": _ss("p_form_lic").strip().upper(),
        "start_date": format_date_val(st.session_state.get("p_form_start"), get_uk_now().date()),
        "end_date": format_date_val(st.session_state.get("p_form_end"), DEFAULT_HIRE_END_DATE),
    }

def contract_data_from_state(include_signature: bool = True) -> dict:
    name, reg = _ss("c_form_name"), _ss("c_form_rv")
    data = {
        "contract_no": _ss("c_form_no").strip().upper() or build_default_contract_no(name, reg),
        "date": format_date_val(st.session_state.get("c_form_date"), get_uk_now().date()),
        "driver_name": name.strip().upper(),
        "address": normalize_address(_ss("c_form_addr")),
        "postcode": _ss("c_form_post").strip().upper(),
        "dob": _ss("c_form_dob").strip(),
        "license_no": _ss("c_form_lic").strip().upper(),
        "expiry_date": _ss("c_form_exp").strip(),
        "issuing_authority": _ss("c_form_auth").strip().upper(),
        "phone": _ss("c_form_ph").strip(),
        "email": _ss("c_form_em").strip().upper(),
        "rent": _ss("c_form_rent").strip(),
        "rate": _ss("c_form_rate").strip(),
        "deposit": _ss("c_form_dep").strip(),
        "start_date": format_date_val(st.session_state.get("c_form_start"), get_uk_now().date()),
        "expected_return": format_date_val(st.session_state.get("c_form_return"), DEFAULT_HIRE_END_DATE),
        "start_time": format_time_val(st.session_state.get("c_form_start_time")),
        "return_time": format_time_val(st.session_state.get("c_form_return_time")),
        "registration": format_uk_reg(reg),
        "car_make": _ss("c_form_mk").strip().upper(),
        "car_model": _ss("c_form_mv").strip().upper(),
        "owner_signature": _ss("c_form_owner_sig", "-- No Signature --"),
    }
    if include_signature:
        data["hirer_signature"] = st.session_state.ocr_signature_bytes if _ss("c_form_hirer_sig") == "Scanned Licence Signature" else None
    return data

def _missing(fields: list[tuple[str, str]]) -> list[str]:
    return [label for key, label in fields if not str(st.session_state.get(key, "") or "").strip()]

def show_preview(kind: str, data: dict, sig: bytes | None = None):
    try:
        pages = cached_preview(kind, json.dumps(data, sort_keys=True, default=str), sig)
    except Exception as err:
        logging.exception("%s preview rendering error: %s", kind, err)
        st.error(f"Live document preview error: {err}")
        return
    if not pages:
        st.error("Live document preview rendering failed. Please check server logs.")
        return
    for idx, page in enumerate(pages, 1):
        if len(pages) > 1:
            st.caption(f"Page {idx} of {len(pages)}")
        st.image(page, width="stretch")

@st.cache_data(show_spinner=False)
def cached_calibration_grid() -> bytes:
    return generate_calibration_grid()

LIVE = "300ms"  # preview refreshes 0.3s after you stop typing

# ─────────────────────────────────────────────
#  DOCUMENTS (fragment: typing only re-runs this part → fast)
# ─────────────────────────────────────────────
@st.fragment
def documents_area():
    if st.session_state.pop("_needs_full_rerun", False):
        st.rerun()

    head_l, head_r = st.columns([3, 1], vertical_alignment="center")
    with head_l:
        st.caption("Everything you type appears instantly in the live preview. Name, licence, address, vehicle and dates are shared between both documents.")
    with head_r:
        st.button("New customer", key="reset_ws_btn", icon=":material/restart_alt:", on_click=reset_workspace,
                  width="stretch", help="Clear every field and start again")

    tab1, tab2 = st.tabs(["✉️ Permission Letter", "📄 Contract Generator"])

    # ───────────── Permission letter ─────────────
    with tab1:
        col_form, col_preview = st.columns([1, 1], gap="medium")
        with col_form:
            with st.container(border=True):
                st.html('<div class="fa-section-title">Driver</div>')
                st.text_input("Driver Full Name", key="p_form_name", live=LIVE, on_change=_sync_name, args=("p_form_name",), placeholder="e.g. John Smith")
                c1, c2 = st.columns(2)
                with c1:
                    st.text_input("Driving Licence No", key="p_form_lic", live=LIVE, on_change=_sync_licence, args=("p_form_lic",))
                with c2:
                    st.text_input("Insurance Policy No", key="p_form_ins", live=LIVE)
                st.text_input("Driver Address", key="p_form_addr", live=LIVE, on_change=_sync_address_from_perm, placeholder="House, street, town, postcode")

            with st.container(border=True):
                st.html('<div class="fa-section-title">Vehicle & hire</div>')
                c1, c2 = st.columns(2)
                with c1:
                    st.text_input("Vehicle Registration", key="p_form_reg", live=LIVE, on_change=_sync_reg, args=("p_form_reg",), placeholder="e.g. YF22 UWM")
                with c2:
                    st.text_input("Make & Model", key="p_form_mod", live=LIVE, on_change=_sync_make_model_from_perm)
                d1, d2, d3 = st.columns(3)
                with d1:
                    st.date_input("Document Date", key="p_form_date", format="DD/MM/YYYY", on_change=_sync_pair, args=("p_form_date", "c_form_date"))
                with d2:
                    st.date_input("Hire Start", key="p_form_start", format="DD/MM/YYYY", on_change=_sync_pair, args=("p_form_start", "c_form_start"))
                with d3:
                    st.date_input("Hire End", key="p_form_end", format="DD/MM/YYYY", on_change=_sync_pair, args=("p_form_end", "c_form_return"))

            with st.container(border=True):
                p_doc_name = st.text_input("Document Name", key="perm_document_name")
                missing = _missing([("p_form_name", "driver name"), ("p_form_lic", "licence no"), ("p_form_addr", "address"),
                                    ("p_form_reg", "registration"), ("p_form_mod", "make & model")])
                if missing:
                    st.caption(f"Still empty: {', '.join(missing)}")
                go_p = st.button("Generate Permission Letter PDF", key="go_p_btn", type="primary", width="stretch", icon=":material/print:")

                if go_p:
                    pdata = permission_data_from_state()
                    expected = build_default_doc_name("Permission", pdata["driver_name"], pdata["registration"], "Permission Letter")
                    perm_clean_name = clean_document_name(p_doc_name, expected)
                    if perm_clean_name in ("Permission Letter", "Permission", "Permission Driver") and pdata["driver_name"] and clean_name(pdata["driver_name"]).upper() != "DRIVER":
                        perm_clean_name = expected
                    with st.spinner("Creating PDF…"):
                        pdf_bytes = generate_permission_letter(pdata)
                    st.session_state.perm_pdf = pdf_bytes
                    st.session_state.perm_filename = perm_clean_name
                    sp_filename = sync_to_supabase(pdf_bytes, perm_clean_name, "Permission Letter", driver_ref=pdata["driver_name"], vehicle_reg=pdata["registration"])
                    add_audit_log("Permission Letter Generated", details=f"Driver: {pdata['driver_name']}, Reg: {pdata['registration']}",
                                  doc_name=f"{perm_clean_name}.pdf", file_path=f"driver_documents/{sp_filename}" if sp_filename else "")
                    notify("Permission letter created — download it below.", "success")

                if st.session_state.perm_pdf:
                    b1, b2 = st.columns(2)
                    with b1:
                        st.download_button("Download PDF", data=st.session_state.perm_pdf, file_name=f"{st.session_state.perm_filename}.pdf",
                                           mime="application/pdf", key="dl_perm_btn", width="stretch", icon=":material/download:", on_click="ignore")
                    with b2:
                        if st.button("Save to Google Drive", key="gdrive_perm_btn", width="stretch", icon=":material/cloud_upload:"):
                            with st.spinner("Uploading to Google Drive…"):
                                ok, msg = save_to_google_drive(st.session_state.perm_pdf, st.session_state.perm_filename, st.session_state.sel_reg or _ss("p_form_reg"))
                            if ok:
                                add_audit_log("Saved to Google Drive", details=msg, doc_name=f"{st.session_state.perm_filename}.pdf")
                            notify(msg, "success" if ok else "error")

        with col_preview:
            with st.container(border=True):
                st.html('<div class="fa-section-title">👁️ Live Document Preview</div>')
                show_preview("permission", permission_data_from_state())

    # ───────────── Contract ─────────────
    with tab2:
        col_form, col_preview = st.columns([1, 1], gap="medium")
        with col_form:
            with st.container(border=True):
                st.html('<div class="fa-section-title">Hirer Details</div>')
                cc1, cc2 = st.columns(2)
                with cc1:
                    st.text_input("Full Name", key="c_form_name", live=LIVE, on_change=_sync_name, args=("c_form_name",))
                with cc2:
                    st.text_input("Contract Number", key="c_form_no", live=LIVE)
                st.text_input("Address", key="c_form_addr", live=LIVE, on_change=_sync_address_from_contract)
                cc1, cc2, cc3 = st.columns(3)
                with cc1:
                    st.text_input("Postcode", key="c_form_post", live=LIVE, on_change=_sync_address_from_contract)
                with cc2:
                    st.text_input("Date of Birth", key="c_form_dob", live=LIVE, placeholder="DD/MM/YYYY")
                with cc3:
                    st.date_input("Contract Date", key="c_form_date", format="DD/MM/YYYY", on_change=_sync_pair, args=("c_form_date", "p_form_date"))
                cc1, cc2, cc3 = st.columns(3)
                with cc1:
                    st.text_input("Licence No", key="c_form_lic", live=LIVE, on_change=_sync_licence, args=("c_form_lic",))
                with cc2:
                    st.text_input("Licence Expiry", key="c_form_exp", live=LIVE, placeholder="DD/MM/YYYY")
                with cc3:
                    st.text_input("Issuing Authority", key="c_form_auth", live=LIVE)
                cc1, cc2 = st.columns(2)
                with cc1:
                    st.text_input("Phone", key="c_form_ph", live=LIVE, placeholder="07…")
                with cc2:
                    st.text_input("Email", key="c_form_em", live=LIVE, placeholder="name@example.com")

            with st.container(border=True):
                st.html('<div class="fa-section-title">Hire Vehicle & Payment</div>')
                pv1, pv2, pv3 = st.columns(3)
                with pv1:
                    st.text_input("Reg", key="c_form_rv", live=LIVE, on_change=_sync_reg, args=("c_form_rv",))
                with pv2:
                    st.text_input("Make", key="c_form_mk", live=LIVE, on_change=_sync_make_model_from_contract)
                with pv3:
                    st.text_input("Model", key="c_form_mv", live=LIVE, on_change=_sync_make_model_from_contract)
                pp1, pp2, pp3 = st.columns(3)
                with pp1:
                    st.text_input("Rent (£/week)", key="c_form_rent", live=LIVE)
                with pp2:
                    st.text_input("Excess (pence/mile)", key="c_form_rate", live=LIVE)
                with pp3:
                    st.text_input("Deposit (£)", key="c_form_dep", live=LIVE)
                pt1, pt2 = st.columns(2)
                with pt1:
                    st.date_input("Hire Start", key="c_form_start", format="DD/MM/YYYY", on_change=_sync_pair, args=("c_form_start", "p_form_start"))
                with pt2:
                    st.date_input("Expected Return", key="c_form_return", format="DD/MM/YYYY", on_change=_sync_pair, args=("c_form_return", "p_form_end"))
                tm1, tm2 = st.columns(2)
                with tm1:
                    st.time_input("Time Car Given", key="c_form_start_time")
                with tm2:
                    st.time_input("Time Car Returned", key="c_form_return_time")

            with st.container(border=True):
                sig_col1, sig_col2 = st.columns(2)
                with sig_col1:
                    st.selectbox("Hirer Signature", ["Scanned Licence Signature", "-- No Signature --"], key="c_form_hirer_sig")
                with sig_col2:
                    st.selectbox("Owner Signature", SIGNATURE_OPTIONS, key="c_form_owner_sig")
                c_doc_name = st.text_input("Document Name", key="contract_document_name")
                missing = _missing([("c_form_name", "full name"), ("c_form_addr", "address"), ("c_form_post", "postcode"),
                                    ("c_form_dob", "date of birth"), ("c_form_lic", "licence no"), ("c_form_ph", "phone"),
                                    ("c_form_rv", "reg"), ("c_form_mk", "make"), ("c_form_mv", "model")])
                if missing:
                    st.caption(f"Still empty: {', '.join(missing)}")
                go_c = st.button("Generate 2-Page Contract PDF", key="go_c_btn", type="primary", width="stretch", icon=":material/print:")

                if go_c:
                    cdata = contract_data_from_state()
                    expected = build_default_doc_name("Contract", cdata["driver_name"], cdata["registration"], "Contract")
                    contract_clean_name = clean_document_name(c_doc_name, expected)
                    if contract_clean_name in ("Contract", "Contract Driver", "Driver") and cdata["driver_name"] and clean_name(cdata["driver_name"]).upper() != "DRIVER":
                        contract_clean_name = expected
                    try:
                        with st.spinner("Creating PDF…"):
                            pdf_bytes = generate_contract(cdata)
                        st.session_state.contract_pdf = pdf_bytes
                        st.session_state.contract_no = cdata["contract_no"]
                        st.session_state.contract_filename = contract_clean_name
                        sp_filename = sync_to_supabase(pdf_bytes, contract_clean_name, "Contract", driver_ref=cdata["driver_name"], vehicle_reg=cdata["registration"])
                        add_audit_log("Contract Generated",
                                      details=f"Contract No: {cdata['contract_no']}, Driver: {cdata['driver_name']}, Reg: {cdata['registration']}",
                                      doc_name=f"{contract_clean_name}.pdf", file_path=f"driver_documents/{sp_filename}" if sp_filename else "")
                        notify("Contract PDF created — download it below.", "success")
                    except Exception as e:
                        st.error(f"Render Error: {e}")

                if st.session_state.contract_pdf:
                    b1, b2 = st.columns(2)
                    with b1:
                        st.download_button("Download PDF", data=st.session_state.contract_pdf, file_name=f"{st.session_state.contract_filename}.pdf",
                                           mime="application/pdf", key="dl_contract_btn", width="stretch", icon=":material/download:", on_click="ignore")
                    with b2:
                        if st.button("Save to Google Drive", key="gdrive_contract_btn", width="stretch", icon=":material/cloud_upload:"):
                            with st.spinner("Uploading to Google Drive…"):
                                ok, msg = save_to_google_drive(st.session_state.contract_pdf, st.session_state.contract_filename, st.session_state.sel_reg or _ss("c_form_rv"))
                            if ok:
                                add_audit_log("Saved to Google Drive", details=msg, doc_name=f"{st.session_state.contract_filename}.pdf")
                            notify(msg, "success" if ok else "error")

            with st.expander("Field positions off? Calibrate them", icon=":material/grid_on:"):
                st.caption(
                    "Download this to see a red 20pt grid drawn over your actual "
                    "contract template. Read off the x/y where each field's blank "
                    "line sits, then update `CONTRACT_PAGE1_FIELDS` / "
                    "`CONTRACT_PAGE2_FIELDS` in src/streamlit_app.py."
                )
                st.download_button("Download Calibration Grid PDF", data=cached_calibration_grid(),
                                   file_name="Calibration_Grid.pdf", mime="application/pdf", key="dl_cal_btn",
                                   icon=":material/grid_on:", on_click="ignore")

        with col_preview:
            with st.container(border=True):
                st.html('<div class="fa-section-title">👁️ Live Document Preview</div>')
                hirer_sig = st.session_state.ocr_signature_bytes if _ss("c_form_hirer_sig") == "Scanned Licence Signature" else None
                show_preview("contract", contract_data_from_state(include_signature=False), hirer_sig)

documents_area()
