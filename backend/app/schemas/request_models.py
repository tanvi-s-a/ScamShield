from pydantic import BaseModel, Field


class LinkItem(BaseModel):
    visible_text: str = ""
    href: str = ""


class ImageItem(BaseModel):
    src: str = ""
    width: int | float | None = None
    height: int | float | None = None
    hidden: bool = False


class ButtonItem(BaseModel):
    text: str = ""
    target: str = ""


class AuthResults(BaseModel):
    spf: str | None = None
    dkim: str | None = None
    dmarc: str | None = None


class AnalyzeRequest(BaseModel):
    subject: str = ""
    body: str = ""
    html_content: str = ""
    from_address: str = ""
    reply_to_address: str = ""
    return_path: str = ""
    message_id: str = ""
    auth_results: AuthResults | None = None
    links: list[LinkItem] = Field(default_factory=list)
    images: list[ImageItem] = Field(default_factory=list)
    buttons: list[ButtonItem] = Field(default_factory=list)
    forms_present: bool = False


class AnalyzeResponse(BaseModel):
    classification: str
    confidence: float
    probabilities: dict
    risk_score: int
    risk_level: str
    findings: list[str]
    blocking_actions: dict
