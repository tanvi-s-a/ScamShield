from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

app = FastAPI(title="MailShield AI Backend", version="0.1.0")

# CORS: only the Chrome extension origin and local dev tools need access.
# Chrome extension origins look like chrome-extension://<extension-id>.
# Replace EXTENSION_ID below once the extension is loaded (see chrome://extensions).
ALLOWED_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1",
    # "chrome-extension://EXTENSION_ID_HERE",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"chrome-extension://.*",  # tighten to a specific ID before sharing publicly
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {"service": "MailShield AI Backend", "status": "running"}
