# import json, re
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from enum import Enum
# from pathlib import Path
from typing import Sequence

from app.core.logger import get_logger

from urllib.parse import urlparse
from app.services.session_store import SessionStore
from app.core.config import SUSPECT_SELECTORS, SUSPECT_TEXT_KEYWORDS, SUSPECT_TITLE_PATTERNS

logger = get_logger(__name__)

session_store = SessionStore()

def heuristic_captcha_detect(url: str, html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True).lower()
    title = (soup.title.string or "").strip() if soup.title else ""
    length = len(html)
    netloc = urlparse(url).netloc.lower()
    domain = netloc.replace("www.", "")
    title_norm = title.lower().replace("www.", "")

    if length < 4096:
        if title_norm.startswith(domain) or not text:
            return "suspicious_small_response"

    for pat in SUSPECT_TITLE_PATTERNS:
        if pat.search(title):
            return pat.pattern

    if any(keyword in text for keyword in SUSPECT_TEXT_KEYWORDS):
        return "keyword_match"

    for selector in SUSPECT_SELECTORS:
        if soup.select_one(selector):
            return selector

    return None


class CaptchaDecision(str, Enum):
    reuse_session = "reuse_session"
    manual_solve = "manual_solve"


class CaptchaDetected(Exception):
    def __init__(self, url:str, signature: str, decision: CaptchaDecision):
        super().__init__(f"Captcha detected for {url} via '{signature}' → {decision.value}")
        self.url = url
        self.signature = signature
        self.decision = decision


@dataclass
class CaptchaManager:
    # log_path: Path = Path("app/data/captcha_log.json")
    signatures: Sequence[str] = field(default_factory= lambda:(
        "baxia-punish",
        "detected unusual traffic",
        "id=\"nocaptcha\"",
        "cf-challenge",
        "recaptcha/api.js",
        "verification required",
        "slide right to complete the puzzle",
        'id="cf-wrapper"',
        'id="cmsg"',
        'cf-error-code'
    ))


    def detect(self, html: str) -> str | None:
        lowered = html.lower()
        for sig in self.signatures:
            if sig in lowered:
                return sig 
        return None
    
    def _has_cached_session(self, url: str) -> bool:
        return session_store.has(url)
    
    def decide(self, url: str) -> CaptchaDecision:
        if self._has_cached_session(url):
            return CaptchaDecision.reuse_session
        return CaptchaDecision.manual_solve

    def handle(self, url: str, html: str) -> None:
        if not html.strip() or not html:
            decision = CaptchaDecision.manual_solve
            # self.log_event(url, "empty_response", decision)
            raise CaptchaDetected(url, "empty_response", decision)

        signature = self.detect(html)
        if not signature:
            heuristic = heuristic_captcha_detect(url, html)
            if heuristic:
                signature = heuristic
            
        if not signature:
            return
        
        decision = self.decide(url)
        # self.log_event(url, signature, decision)
        raise CaptchaDetected(url, signature, decision)

