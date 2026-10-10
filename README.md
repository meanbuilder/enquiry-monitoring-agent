# EnquiryPulse — CEO Command Centre

EnquiryPulse is a Streamlit demo for monitoring enquiry and quotation
registers. It combines deterministic Python business rules with
Gemini-powered question routing and evidence-backed explanations.

**Demo uses synthetic data only.** Do not commit customer records,
commercially sensitive information, API keys, or `.env` files.

## Features

- CEO overview of enquiries, quotations, recorded orders and work-order checks.
- Searchable enquiry workbench with priority filters.
- Gemini-powered natural-language question routing.
- Allowlisted Python analysis tools.
- Evidence-backed explanations and customer follow-up drafts.
- Session-only CEO decision inbox.
- Python-calculated metrics and record matching.
- No automatic email sending or source-register modification.

## Configure Gemini on Streamlit Community Cloud

Open your app's Settings → Secrets and add:

```toml
GEMINI_API_KEY = "your-Gemini-API-key"
GEMINI_MODEL = "gemini-2.5-flash"
