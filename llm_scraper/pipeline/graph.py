# Graph.py
import asyncio
from loguru import logger
from langgraph.graph import StateGraph, END
from llm_scraper.utils.cleaner import extract_main_content, chunk_html
from llm_scraper.utils.fetcher import fetch_html_playwright
from llm_scraper.utils.llm_engine import get_llm, build_prompt
from llm_scraper.utils.parser import validation_and_parse_response
from typing import Dict, Any, TypedDict, List, Optional


class ScraperState(TypedDict):
    url: str
    instruction: str
    html: Optional[str]
    text: Optional[str]
    chunks: Optional[List[str]]
    prompt: Optional[str]
    llm_response: Optional[str]
    parsed_data: Optional[Dict[str, Any]]


def fetch_node(state: ScraperState) -> ScraperState:
    url = state['url']
    html = asyncio.run(fetch_html_playwright(url))
    state['html'] = html
    return state

def clean_node(state: ScraperState) -> ScraperState:
    html = state['html']
    text = extract_main_content(html)
    chunks = chunk_html(text)

    state['text'] = text
    state['chunks'] = chunks

    return state

def prompt_node(state: ScraperState) -> ScraperState:
    
    instruction = state['instruction']
    chunks = state['chunks']
    prompt = build_prompt(instruction, chunks)

    state['prompt'] = prompt

    return state

def llm_node(state: ScraperState) -> ScraperState:
    llm = get_llm()
    prompt = state['prompt']
    response = llm.invoke(prompt)

    state['llm_response'] = response.content

    return state

def parser_node(state: ScraperState) -> ScraperState:
    resp = state['llm_response']

    parsed_data = validation_and_parse_response(resp)

    state['parsed_data'] = parsed_data

    return state

def build_scraper_graph():
    workflow = StateGraph(ScraperState)

    # Register nodes
    workflow.add_node("fetch", fetch_node)
    workflow.add_node("clean", clean_node)
    workflow.add_node("prompt", prompt_node)
    workflow.add_node("llm", llm_node)
    workflow.add_node("parser", parser_node)

    # Define edges
    workflow.set_entry_point("fetch")
    workflow.add_edge("fetch", "clean")
    workflow.add_edge("clean", "prompt")
    workflow.add_edge("prompt", "llm")
    workflow.add_edge("llm", "parser")
    workflow.add_edge("parser", END)

    return workflow.compile()