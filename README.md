# Enquiry Intelligence — CEO Demo

A browser-based Streamlit prototype for monitoring enquiry and quotation registers. It uses **synthetic demo records only** and does not connect to an AI provider, send email, or persist changes.

## Features
- Executive snapshot of enquiry and quotation activity
- Enquiry workbench with search and filters
- Transparent rule-based follow-up findings
- Demo assistant for supported questions
- Work-order preparation check when `Remark` indicates an order was received but `WO No.` is blank
- Unknown outcomes stay unknown when remark and work-order fields are blank

## Deploy from GitHub
1. Create a **private** GitHub repository named `enquiry-monitoring-agent`.
2. Upload the files and folders from this project to the repository root.
3. Open Streamlit Community Cloud and sign in with GitHub.
4. Create a new app and select the repository, branch, and `app.py` as the main file.
5. Deploy. Use the app's shareable URL for the CEO demo.
6. In a separate browser or private/incognito window, verify that the app opens without a login prompt before sharing the link.

The deployed app is intended to be publicly accessible. **Anyone who obtains the URL may be able to open it.** Keep this build limited to synthetic data. A private GitHub repository protects repository access; it does not make the deployed app private.

## Run locally (optional for developers)
```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Test business rules
```bash
python -m pip install pytest
pytest -q
```

## Data and privacy
- The CSV files in `sample_data/` contain fictional names, references, dates, and values.
- Never commit real enquiry/quotation registers, customer information, API keys, `.env` files, or secrets.
- This first build uses Python rules only. It does not send data to an external LLM.
- The app is a demonstration, not a production system of record. It does not provide durable shared storage or authenticated access.
- Follow-up recommendations are advisory and require human verification.
