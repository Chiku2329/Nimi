"""Conservative per-request tool selection to reduce prompt overhead."""
from __future__ import annotations

import re

from math_utils import extract_arithmetic_expression


def select_relevant_tools(user_text: str, allowed_tools) -> frozenset[str]:
    """Return only tools clearly relevant to the current user request.

    Ambiguous/general questions deliberately get no tools; current-information,
    weather, time, arithmetic, memory and file intents are detected separately.
    The server-side agent allowlist remains authoritative.
    """
    if isinstance(user_text, list):
        user_text = " ".join(
            part.get("text", "") for part in user_text
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        )
    if not isinstance(user_text, str):
        return frozenset()
    text = user_text.strip().lower()[:20000]
    if not text:
        return frozenset()

    selected = set()
    has_math_numbers = len(re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?", text)) >= 2
    has_math_operator = bool(re.search(r"[+*/×÷^%]|\b(plus|minus|multiply|divided|divid|times)\b", text))
    explicit_calculation = bool(re.search(r"\b(calculate|compute|evaluate|solve)\b", text))
    if extract_arithmetic_expression(text) or (
        has_math_numbers and (has_math_operator or explicit_calculation)
    ):
        selected.add("calculate")

    if re.search(r"\b(weather|forecast|temperature|rain|snow|wind speed)\b", text):
        selected.add("get_weather")
    if re.search(r"\b(time in|current time|local time|what time|tell me the time|time zone|timezone)\b", text):
        selected.add("get_time")
    if re.search(
        r"\b(search the web|web search|search for|look up|find me|find sources|cite sources|"
        r"latest|today|currently|current news|headlines|recent news|research|"
        r"compare sources|verify this|fact.?check|price today|yesterday|last night|this week|this month|this year|upcoming|schedule|scores|results|exchange rate|stock price|election results|release date|as of)\b",
        text,
    ):
        selected.add("web_search")
    if re.search(r"\b(remember this|remember that|remember i |remember my |save this|save to memory|"
                 r"remember for next time|don't forget)\b", text):
        selected.add("remember")
    if re.search(r"\b(forget|delete|remove).{0,40}\b(memory|memories|saved)\b", text):
        selected.add("forget")
    if re.search(
        r"\b(create|make|generate|prepare|export|write)\b.{0,80}\b("
        r"pdf|docx|document|word document|xlsx|spreadsheet|excel|pptx|powerpoint|"
        r"csv|text file|markdown file|json file)\b",
        text,
    ):
        selected.add("create_file")

    return frozenset(selected.intersection(allowed_tools))
