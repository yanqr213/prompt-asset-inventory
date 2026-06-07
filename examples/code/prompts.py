SYSTEM_PROMPT = """
owner: search-team
purpose: answer repository search questions
version: 1.4.0
privacy: repository text only
source: examples/code/prompts.py
citations: evals/search.yaml

System prompt:
You are a precise code search assistant. Cite matching file paths.
"""

UNOWNED_EVAL_PROMPT = """
Eval case:
The assistant should identify missing metadata fields.
"""
