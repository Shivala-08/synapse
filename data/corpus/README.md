# Corpus Directory

Place your documents here for ingestion:

- **real/** — Your primary document corpus (PDF, DOCX, TXT)
- **synthetic/** — Generated or supplementary data (CSV logs, etc.)
- **uploads/** — Files uploaded via the API (auto-managed)

Supported formats: `.pdf`, `.docx`, `.txt`, `.csv`

After adding documents, initialize the corpus via the UI or API:
```bash
curl -X POST http://localhost:8000/ingest/initialize
```
