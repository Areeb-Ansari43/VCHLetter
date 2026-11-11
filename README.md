# VCHLetter — FA-IBI Workspace

Streamlit app for creating permission letters and 2-page hire contracts.
Main file: `streamlit_app.py` (it runs `src/streamlit_app.py`).

## Features
- **Driver's licence scanner** – accepts any photo (JPG, PNG, HEIC, WEBP, AVIF, TIFF, GIF…),
  PDFs (page 1) and documents with an embedded photo. Finds and straightens the card,
  then reads it with Azure AI Document Intelligence (Tesseract as fallback).
- **Fleet vehicle picker** – 93 vehicles from `VCH_Car_Fleet_01092026.numbers`, grouped by make.
  Picking a car fills reg, make, model, rent and deposit on both documents.
- **Live document preview** – updates while you type (0.3 s after you pause).
  Name, licence, address, vehicle and dates are shared between both documents.
- **Audit logs** – searchable history with links to stored PDFs.

## Secrets (Streamlit Cloud → App settings → Secrets)
`ACCESS_KEY`, `AZURE_DOCINTEL_ENDPOINT`, `AZURE_DOCINTEL_KEY`, `SUPABASE_URL`,
`SUPABASE_SERVICE_ROLE_KEY`, `gcp_service_account` (optional Google Drive).

## Keeping audit logs after a restart (optional)
Streamlit Cloud wipes local files when the app restarts. The audit page rebuilds the
document history from the Supabase `driver_documents` table automatically. To also keep
PIN / scan events, create this table once in the Supabase SQL editor:

```sql
create table if not exists audit_logs (
  id bigint generated always as identity primary key,
  timestamp text, event_type text, doc_name text, details text, file_path text,
  created_at timestamptz default now()
);
```

## Run locally
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```
