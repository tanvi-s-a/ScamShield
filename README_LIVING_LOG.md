README — Living Setup & Debug Log
=================================

Last updated: 2026-07-28

Purpose
-------
This file is a living, plain-English record of what we've done in this workspace, what failed, and how we fixed it.
Whenever something new happens during setup, training, testing, or deployment, I'll append a concise dated entry here that explains: what happened, why it happened (simple terms), and the exact commands or steps we used to resolve it.

How to use this file
--------------------
- Read the timeline for a chronological history of actions and fixes.
- Follow the exact commands in the “Quick commands” sections when reproducing steps.
- If you'd like me to commit this file to the repository, tell me and I'll stage a commit for you.

Timeline (chronological)
------------------------
2026-07-28 — Initial entries
- Started: connected my local workspace and investigated Git remote and install issues.

Git / remote troubleshooting
- Observation: the repo's local Git config initially used a misspelled remote name: `orgin` instead of `origin`. This caused confusion when pushing and when VS Code showed merge-base info referencing `orgin/main`.
- Fix applied (what we recommended to run locally):
  ```bash
  git remote rename orgin origin
  git fetch origin
  git branch -vv
  ```
- Push conflict seen later: `error: failed to push some refs ... tip of your current branch is behind`. That means there were commits on GitHub that the local branch didn't have.
- Resolution approach used: fetch and rebase (safe for a clean local branch):
  ```bash
  git fetch origin
  git pull --rebase origin main
  git push origin main
  ```
- Final state (checked locally): `Your branch is up to date with 'origin/main'` and `nothing to commit, working tree clean`.

Python environment & dependency installation
- Goal: create an isolated environment and install the project's Python dependencies from `backend/requirements.txt`.
- Commands we ran (or recommended) from the `backend` folder:
  ```powershell
  py -3 -m venv .venv
  .\.venv\Scripts\Activate.ps1
  python -m pip install --upgrade pip
  pip install -r requirements.txt pytest
  ```

scikit-learn build failure (root cause)
- Symptom: `pip install -r requirements.txt` failed while preparing metadata for `scikit-learn==1.5.1` with a Meson/MesonPy error:
  - Meson attempted to detect a C/C++ compiler (cl, gcc, clang, etc.) and couldn't find one.
  - Error message: `Unknown compiler(s)` and `Failed to activate VS environment: Could not find ... vswhere.exe`.
- Why: on Windows pip prefers to download a prebuilt wheel. If a matching wheel is not available for the current Python version / platform combination, pip falls back to building from source — and that requires a C/C++ toolchain.
- Two reliable fixes:
  1. Use Python 3.11 (preferred): many packages publish wheels for 3.11 on Windows, avoiding the need to compile.
     Commands:
     ```powershell
     # install via winget if missing
     winget install -e --id Python.Python.3.11
     # recreate venv with 3.11
     Remove-Item -Recurse -Force .venv
     py -3.11 -m venv .venv
     Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
     .\.venv\Scripts\Activate.ps1
     python -m pip install --upgrade pip
     pip install -r requirements.txt pytest
     ```
  2. Keep your current Python but install Microsoft Build Tools (heavy):
     - Run the Visual Studio Build Tools installer and include the "Desktop development with C++" workload. After that, retry `pip install -r requirements.txt`.
     ```powershell
     winget install -e --id Microsoft.VisualStudio.2022.BuildTools
     # then run installer and select the C++ workload
     .\.venv\Scripts\Activate.ps1
     pip install -r requirements.txt pytest
     ```
- Which we recommended: option (1) — install Python 3.11 and recreate the `.venv`.

User command mistakes we observed
- Combined commands incorrectly. Example of a malformed command typed earlier:
  ```powershell
  pip install -r requirements.txt pytestpython -m pip install --upgrade pip
  ```
  That merges two commands and confuses `pip`.
- Correct sequence: run `pip install -r requirements.txt pytest` to install packages, and run `python -m pip install --upgrade pip` separately to upgrade pip.

Training, testing, and running the backend — quick reference
- From the `backend` folder, after dependencies are installed and the venv is active:
  1) Generate synthetic and normalized data
  ```powershell
  python training\generate_synthetic_ads.py
  python training\normalize_datasets.py
  python training\extract_features.py
  ```
  2) Train the model
  ```powershell
  python training\train_model.py
  ```
  This saves the pipeline to: `models/mailshield_random_forest.joblib`
  3) Evaluate the model
  ```powershell
  python training\evaluate_model.py
  ```
  Reports go to: `reports/model_metrics.json`, `reports/evaluation_metrics.json`, `reports/confusion_matrix.png`
  4) Run backend
  ```powershell
  uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
  ```
  Health endpoint: `http://127.0.0.1:8000/health` — the JSON should contain `"model_loaded": true` after a trained model exists.

Tests
- Run the unit tests:
  ```powershell
  pytest tests\ -v
  ```
- To check the specific lookalike-domain fix we were tracking:
  ```powershell
  pytest tests\test_sender_analyzer.py -v
  ```

What I did for you so far (summary)
- Investigated Git remote naming and push errors; recommended `git remote rename orgin origin` and rebase-based pull to reconcile histories.
- Inspected `backend/requirements.txt` and reproduced the failure reason: scikit-learn attempted to build from source because a compatible wheel was not available for the active Python runtime.
- Recommended a minimal, reliable fix (install Python 3.11 and recreate `.venv`) and provided exact commands.
- Created this living log file so we can record each subsequent event and resolution.

How I will keep this file updated
- I will append a new dated entry here whenever you report a new error or when I run a step that produces a noteworthy result (e.g., tests now pass, model trained, server runs, etc.).
- If you want automatic commits, tell me and I'll stage and commit each update to git; otherwise I will keep it as an editable local file until you ask for commits.

If you want me to do any of the following, tell me which and I will proceed:
- Create a PowerShell script that automates venv creation, dependency install, data generation, training, and evaluation.
- Try to run the training steps here (I can only edit files; I cannot run commands in your shell). Paste terminal output and I will append the results.
- Commit `README_LIVING_LOG.md` into Git and push to `origin` for you.

Contact / next steps
- To have me commit the file: say `commit` and I'll prepare the commit command to run locally.
- To have me generate the automation script: say `script` and I'll add it to `backend/scripts/setup_train.ps1`.


