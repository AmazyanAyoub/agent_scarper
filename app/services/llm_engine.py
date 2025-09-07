# llm_engine.py

from loguru import logger
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from app.core.config import GROQ_API_KEY, DEFAULT_MODEL, DEFAULT_PROVIDER


def get_llm(provider: str = DEFAULT_PROVIDER, model: str = DEFAULT_MODEL):

    if provider == "groq":
        logger.info(f"Using Groq model: {model}")
        return ChatGroq(model=model, temperature=0, api_key=GROQ_API_KEY)
    else:
        logger.info(f"We only provide groq model for now: {model}")
        return ""
    
def build_prompt(user_instraction: str, chunks: list) -> str:
    """
    Build the prompt for the LLM from instruction + content chunks.
    """

    template = ChatPromptTemplate.from_messages(
        [
            ("system", "You are an intelligent web scraping assistant. Always return JSON and always use data as the JSON key."),
            (
                "human",
                "Instruction: {instruction}\n\nPage content:\n{content}\n\nReturn JSON only.",
            ),
        ]
    )
    context = "\n\n".join(chunks[:3])
    return template.format(instruction=user_instraction, content=context)