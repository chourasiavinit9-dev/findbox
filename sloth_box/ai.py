"""
sloth_box.ai
Local open-weight Gemma 3 client via Ollama on 127.0.0.1:11434,
with structured JSON generation, schema enforcement, and natural query parsing.
"""

import datetime
import json
import re
import urllib.error
import urllib.request
from .config import CATEGORIES, DEFAULT_MODEL, OLLAMA_API_BASE
from .extractor import fallback_heuristics


def call_ollama(prompt, image_b64=None, model=DEFAULT_MODEL, timeout=120):
    """Executes a 100% local inference call against Ollama HTTP API."""
    url = f"{OLLAMA_API_BASE}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    if image_b64:
        payload["images"] = [image_b64]

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("response", "")
    except Exception:
        return None


def clean_json_string(s):
    """Extracts valid JSON payload from model response."""
    if not s:
        return None
    s = s.strip()
    match = re.search(r"\{.*\}", s, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return None


def analyze_file_with_gemma(filepath, extracted, model=DEFAULT_MODEL):
    """Invokes Gemma 3 to extract structured metadata, tasks, dates, and memory tags."""
    prompt = f"""
You are FindBox (SlothBox), an intelligent document organizer running locally.
Analyze the provided document/image and return ONLY a valid JSON object.

Allowed categories: bills, receipts, identity, medical, work, study, travel, recipes, chats, screenshots, photos, forms, other.

JSON Schema:
{{
  "title": "kebab-case-concise-descriptor",
  "category": "one_of_the_allowed_categories",
  "document_date": "YYYY-MM-DD or empty string",
  "issuer_or_person": "company, authority, or person name, or unknown",
  "one_sentence_summary": "Crisp one-sentence summary of what this is",
  "app": "source app if screenshot like WhatsApp, Instagram, or empty",
  "readable_text": "up to 60 words of primary text content or key points",
  "search_tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8"],
  "todos": [{{"task": "actionable task", "deadline_or_empty": "YYYY-MM-DD or empty"}}],
  "amounts": ["amounts mentioned like ₹450 or $20"]
}}

Rules:
- For chats: extract who/what it is about, key decisions, amounts, and any promised actions.
- Multilingual support: handle Hindi and Bengali transliterations natively (e.g. rent, kharcha, paneer).
- Return ONLY the JSON object.
"""
    if extracted["type"] == "text":
        prompt += f"\n\nDocument Text Sample:\n{extracted['text'][:2500]}"
        resp = call_ollama(prompt, image_b64=None, model=model)
    elif extracted["type"] == "image":
        resp = call_ollama(prompt, image_b64=extracted["data"], model=model)
    else:
        prompt += f"\n\nFile Name: {filepath.name}"
        resp = call_ollama(prompt, image_b64=None, model=model)

    parsed = clean_json_string(resp)
    if parsed and "category" in parsed:
        if parsed.get("category") not in CATEGORIES:
            parsed["category"] = "other"
        if not parsed.get("document_date"):
            mtime = datetime.datetime.fromtimestamp(filepath.stat().st_mtime)
            parsed["document_date"] = mtime.strftime("%Y-%m-%d")
        if not parsed.get("title"):
            parsed["title"] = re.sub(r"[^a-zA-Z0-9]+", "-", filepath.stem.lower()).strip("-")
        return parsed

    # Deterministic fallback heuristics when Ollama is offline or model fails
    return fallback_heuristics(filepath, extracted.get("text", ""))


def parse_vague_query(query, model=DEFAULT_MODEL):
    """Converts vague natural memory query to search parameters."""
    today_str = datetime.date.today().isoformat()
    prompt = f"""
You are a search query interpreter for personal files.
Today's date is: {today_str}
Query: "{query}"

Return a JSON object:
{{
  "keywords": ["expanded", "synonyms", "clean", "terms"],
  "category_hint": "category name or empty string",
  "date_from": "YYYY-MM-DD or empty string",
  "date_to": "YYYY-MM-DD or empty string"
}}

Handle relative dates: "last month", "early September", "yesterday".
Return ONLY the raw JSON object.
"""
    resp = call_ollama(prompt, model=model, timeout=30)
    parsed = clean_json_string(resp)
    if parsed and "keywords" in parsed:
        return parsed

    # Deterministic fallback parser
    q_lower = query.lower()
    cat_hint = ""
    for c in CATEGORIES:
        if c in q_lower or (c == "recipes" and "recipe" in q_lower) or (c == "bills" and "bill" in q_lower):
            cat_hint = c
            break

    date_from, date_to = "", ""
    if "september" in q_lower:
        year = str(datetime.date.today().year)
        date_from, date_to = f"{year}-09-01", f"{year}-09-30"
    elif "last month" in q_lower:
        today = datetime.date.today()
        first_this_month = today.replace(day=1)
        last_month_end = first_this_month - datetime.timedelta(days=1)
        date_from = last_month_end.replace(day=1).isoformat()
        date_to = last_month_end.isoformat()

    words = re.findall(r"\b[a-zA-Z0-9_\u0900-\u097F\u0980-\u09FF]{2,}\b", query)
    stop_words = {"the", "that", "with", "from", "and", "for", "thing", "about", "show", "find"}
    filtered_words = [w for w in words if w.lower() not in stop_words]

    return {
        "keywords": filtered_words,
        "category_hint": cat_hint,
        "date_from": date_from,
        "date_to": date_to
    }
