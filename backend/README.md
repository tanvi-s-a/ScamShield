# MailShield AI — Backend

## Setup

```powershell
cd mailshield-ai\backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 1. Build the training data

Only the synthetic advertisement dataset is generated locally (no external
downloads needed). The other four sources need to be downloaded manually —
see the docstring at the top of `training/normalize_datasets.py` for exact
paths and sources. The pipeline works fine with just the synthetic set for
initial testing; add the real datasets before your final training run.

```powershell
python training\generate_synthetic_ads.py
python training\normalize_datasets.py
python training\extract_features.py
python training\train_model.py
python training\evaluate_model.py
```

This produces:
- `models/mailshield_random_forest.joblib` — the trained pipeline
- `reports/model_metrics.json`, `reports/evaluation_metrics.json`, `reports/confusion_matrix.png`

## 2. Run the backend

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Check `http://127.0.0.1:8000/health` — should show `"model_loaded": true`
once you've trained a model.

## 3. Test the analyze endpoint

```powershell
curl -X POST http://127.0.0.1:8000/analyze -H "Content-Type: application/json" -d "{\"subject\": \"You won a free phone\", \"body\": \"Verify your account immediately.\", \"from_address\": \"winner@reward-confirmation.example\", \"links\": [{\"visible_text\": \"Claim Prize\", \"href\": \"https://account-check.example\"}]}"
```

## Notes

- This backend has been verified to run end-to-end in a sandboxed
  environment using synthetic data only (sklearn/pandas/joblib/bs4 —
  no network access). FastAPI/pydantic themselves haven't been run in that
  same sandbox since it had no internet to install them, so do a smoke
  test with `uvicorn` locally before relying on it for a live demo.
- 100% accuracy on synthetic-only data is expected and not meaningful —
  the synthetic templates are easy to separate. Real numbers will emerge
  once Kaggle/SpamAssassin/Enron data is mixed in.

## Fast Windows setup (Python 3.12)

From PowerShell inside the `backend` folder:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\setup_windows.ps1
```

This creates an isolated `.venv`, installs compatible packages, trains three
candidate models, selects the model with the best phishing recall, evaluates
it, and saves it under `models/mailshield_model.joblib`.

Start the API afterward:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/health`. `model_loaded` should be `true`.
