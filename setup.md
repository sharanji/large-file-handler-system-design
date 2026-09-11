# Running this app

If you just want to click around, the live Cloud Run deploy is here:

**https://dev---largefile-searching-system-pave2cceiq-uc.a.run.app/**

Health check: https://dev---largefile-searching-system-pave2cceiq-uc.a.run.app/hello

---

## Local setup

This is the short path if you want it on your machine. You do not need to fill in env vars yourself — I sent the `.env` file and the GCP service-account JSON in the mail. Drop those in, install deps, run.

## What you need

- Python 3.11 (the Dockerfile uses this; 3.10+ should be fine)
- The two files from the mail:
  - `.env`
  - the service-account JSON (whatever it is named)

## 1. Clone / open the repo

```bash
cd largefile-searching-system
```

## 2. Put the mailed files in the project root

Same folder as `main.py`.

1. Save `.env` as `.env` (exactly that name, not `.env.txt`).
2. Save the JSON next to it.
3. Open `.env` and check `GOOGLE_APPLICATION_CREDENTIALS`. It should match the JSON filename, for example:

```
GOOGLE_APPLICATION_CREDENTIALS=your-service-account.json
```

If the file on disk is named something else, change that line to match. You can use a relative path from the repo root; the app resolves it.

Do not commit `.env` or the JSON. They are credentials.

## 3. Virtualenv and install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 4. Run it

```bash
python main.py
```

The Flask app starts on **port 8091**.

- Health check: http://localhost:8091/hello — should say `Server is running`
- UI: http://localhost:8091/

On first start it will try to talk to Elasticsearch, GCS, and Pub/Sub using the values in `.env` and the service account. If something in GCP is down you may still see the server come up (those setup calls are swallowed), but upload/index/search will fail until the credentials and network are right.

## If it does not start

- `Environment file` / missing keys: `.env` is not in the repo root, or the name is wrong.
- Google auth errors: JSON path in `GOOGLE_APPLICATION_CREDENTIALS` does not match the file you saved.
- Elasticsearch errors: the Elastic URL / API key in the mailed `.env` is stale, or your network cannot reach Elastic Cloud.

That is it for local. No extra GCP setup if you use the files from the mail. For the hosted version, use the live link at the top.
