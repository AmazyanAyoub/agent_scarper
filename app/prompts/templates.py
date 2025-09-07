# templates.py

def get_extraction_prompt(instruction : str, chunks : list) -> str:
    """
    Build a prompt for the LLM combining user instruction with cleaned HTML chunks.
    """
    context = "\n\n".join(chunks[:3])  # limit to first 3 chunks for prompt size
    prompt = f"""
You are an intelligent web scraper assistant.

Task:
- Extract information based on the following user instruction:
  "{instruction}"

Page content (partial):
{context}

Return the result in valid JSON format.
"""
    return prompt.strip()
