# import json, re
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from enum import Enum
# from pathlib import Path
from typing import Sequence

from app.core.logger import get_logger
logger = get_logger(__name__)


# from app.services.llm_engine import get_llm
# from app.prompts.prompts import CAPTCHA_DECISION_PROMPT

# from typing import Literal
# from pydantic import BaseModel
# from langchain.output_parsers.openai_functions import PydanticAttrOutputFunctionsParser
# from langchain_core.utils.function_calling import convert_to_openai_function
from urllib.parse import urlparse
from app.services.session_store import SessionStore
from app.core.config import SUSPECT_SELECTORS, SUSPECT_TEXT_KEYWORDS, SUSPECT_TITLE_PATTERNS

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
    # solver_service = "solver_service"
    # abort = "abort"

# class CaptchaDecisionSchema(BaseModel):
#     decision: Literal["reuse_session", "manual_solve", "solver_service", "abort"]


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

    # history_window: int = 10

    def detect(self, html: str) -> str | None:
        lowered = html.lower()
        for sig in self.signatures:
            if sig in lowered:
                return sig 
        return None
    
    # def _load_history(self) -> list[dict]:
    #     if not self.log_path.exists():
    #         return []
    #     try:
    #         return json.loads(self.log_path.read_text(encoding="utf-8"))
    #     except json.JSONDecodeError:
    #         logger.warning("Captcha log corrupted, starting fresh.")
    #         return []
        
    # def _write_history(self, history: list[str]) -> None:
    #     self.log_path.parent.mkdir(parents=True, exist_ok=True)
    #     self.log_path.write_text(json.dumps(history, indent=2), encoding="utf-8")

    # def log_event(self, url: str, signature: str, decision: CaptchaDecision) -> None:
    #     history = self._load_history()
    #     history.append({
    #         "url": url,
    #         "signature": signature,
    #         "decision": decision.value
    #     })

    #     self._write_history(history)
    #     logger.warning(f"[CAPTCHA] {url} hit '{signature}' → {decision.value}")
    
    # def _llm_decide(self, url: str, signature: str, history: list[dict]) -> CaptchaDecision | None:

    #     tail = list(reversed(history[-self.history_window:]))
    #     history_lines = "\n".join(
    #         f"- {entry['url']} | {entry['signature']} → {entry['decision']}"
    #         for entry in tail
    #     )

    #     decision_function = convert_to_openai_function(CaptchaDecisionSchema)
    #     llm = get_llm().bind(functions=[decision_function], function_call={"name": "CaptchaDecisionSchema"})
    #     decision_parser = PydanticAttrOutputFunctionsParser(
    #         pydantic_schema=CaptchaDecisionSchema,
    #         attr_name="decision",
    #     )

    #     chain = CAPTCHA_DECISION_PROMPT | llm | decision_parser
    #     try:
    #         decision = chain.invoke({"url": url, "signature": signature, "history": history_lines})
    #     except Exception as e:
    #         logger.error(f"LLM decision failed: {e}")
    #         return None
        
    #     try:
    #         return CaptchaDecision(decision)
    #     except ValueError:
    #         logger.warning(f"LLM returned unknown decision '{decision}', falling back.")
    #         return None

    def _has_cached_session(self, url: str) -> bool:
        return session_store.has(url)
    
    def decide(self, url: str) -> CaptchaDecision:
        if self._has_cached_session(url):
            return CaptchaDecision.reuse_session
        return CaptchaDecision.manual_solve
    
    
    # def decide(self, url: str) -> CaptchaDecision:
    #     # if a storage_state file already exists, retry with it before bothering the LLM
    #     if self._has_cached_session(url):
    #         return CaptchaDecision.reuse_session

    #     # history = self._load_history()
    #     # decision = self._llm_decide(url, signature, history)

    #     if decision is None:
    #         decision = self._fallback_decide(url)
    #     return decision
    
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

