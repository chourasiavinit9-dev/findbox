"""
sloth_box.extractor
File ingestion, hash calculation, text extraction (PDF, DOCX, TXT, Images),
malware magic-byte inspection, and deterministic fallback heuristics.
"""

import base64
import datetime
import hashlib
import pathlib
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zipfile
import zlib
from .config import BASE_DIR, CATEGORIES
from .errors import ExtractionError
from .security import check_executable_magic_bytes, sanitize_filename


def compute_sha256(filepath: pathlib.Path) -> str:
    """Calculates SHA256 checksum for deduplication and audit tracking."""
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        raise ExtractionError(f"Failed to calculate SHA256 for {filepath.name}: {e}")


def extract_docx_text(filepath: pathlib.Path) -> str:
    """Extract text from docx via zipfile and XML parsing (stdlib only)."""
    try:
        with zipfile.ZipFile(filepath, "r") as z:
            if "word/document.xml" not in z.namelist():
                return ""
            xml_data = z.read("word/document.xml")
            tree = ET.fromstring(xml_data)
            namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            texts = [node.text for node in tree.findall(".//w:t", namespaces) if node.text]
            return " ".join(texts)
    except Exception:
        return ""


def extract_pdf_text(filepath: pathlib.Path) -> str:
    """Try pdftotext if available; fallback to standard library byte stream decompression."""
    if shutil.which("pdftotext"):
        try:
            res = subprocess.run(["pdftotext", str(filepath), "-"], capture_output=True, text=True, check=True, timeout=15)
            if res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass

    # Basic Stdlib Fallback: Parse decompressed PDF text streams
    try:
        with open(filepath, "rb") as f:
            content = f.read()
        text_parts = []
        streams = re.findall(rb"stream[\r\n]+(.*?)[\r\n]+endstream", content, re.DOTALL)
        for s in streams:
            try:
                decomp = zlib.decompress(s)
                matches = re.findall(rb"\((.*?)\)\s*(?:Tj|'|\")", decomp)
                for m in matches:
                    text_parts.append(m.decode("latin1", errors="ignore"))
            except Exception:
                continue
        if text_parts:
            return " ".join(text_parts)
    except Exception:
        pass

    return ""


def render_pdf_first_page_image(filepath: pathlib.Path):
    """Try pdftoppm to render first page of a scanned PDF for vision analysis."""
    tmp_out = BASE_DIR / ".tmp_pdf_preview.png"
    if shutil.which("pdftoppm"):
        try:
            subprocess.run(
                ["pdftoppm", "-png", "-f", "1", "-l", "1", str(filepath), str(tmp_out.with_suffix(""))],
                check=True, capture_output=True, timeout=20
            )
            candidate = tmp_out.parent / f"{tmp_out.stem}-1.png"
            if candidate.exists():
                return candidate
        except Exception:
            pass
    return None


def extract_content(filepath: pathlib.Path):
    """Extract readable text or base64 image data depending on file type."""
    # First: Check for executable magic bytes
    if check_executable_magic_bytes(filepath):
        return {
            "type": "binary",
            "text": f"Executable or binary file quarantined: {filepath.name}",
            "is_quarantine": True
        }

    ext = filepath.suffix.lower()
    img_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    text_exts = {".txt", ".md", ".csv", ".json", ".log"}

    if ext in img_exts:
        try:
            with open(filepath, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
                return {"type": "image", "data": b64, "ext": ext[1:]}
        except Exception:
            return {"type": "binary", "text": ""}

    if ext == ".docx":
        return {"type": "text", "text": extract_docx_text(filepath)}

    if ext == ".pdf":
        txt = extract_pdf_text(filepath)
        if len(txt.strip()) > 30:
            return {"type": "text", "text": txt}
        img_page = render_pdf_first_page_image(filepath)
        if img_page and img_page.exists():
            try:
                with open(img_page, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                img_page.unlink(missing_ok=True)
                return {"type": "image", "data": b64, "ext": "png"}
            except Exception:
                pass
        return {"type": "text", "text": txt}

    if ext in text_exts:
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                return {"type": "text", "text": f.read()}
        except Exception:
            pass

    return {"type": "binary", "text": f"File name: {filepath.name}"}


def _match_any(keywords, text):
    for k in keywords:
        pattern = r"\b" + re.escape(k) + r"\b" if len(k) <= 4 else re.escape(k)
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def fallback_heuristics(filepath: pathlib.Path, content_text: str):
    """Deterministic fallback analysis when Ollama is offline or unparseable."""
    name = filepath.name.lower()
    text = (content_text or "").lower()
    combined = f"{name} {text}"

    # If quarantined executable
    if check_executable_magic_bytes(filepath):
        return {
            "title": sanitize_filename(filepath.stem),
            "category": "other",
            "document_date": datetime.date.today().isoformat(),
            "issuer_or_person": "system",
            "one_sentence_summary": f"Binary executable blocked for security: {filepath.name}",
            "app": "",
            "readable_text": "Quarantined binary file",
            "search_tags": ["binary", "executable", "quarantine", "other"],
            "todos": [],
            "amounts": []
        }

    cat = "other"
    if (("chat" in name and "receipt" not in name) or "whatsapp" in name) or (("whatsapp" in text or "chat" in name) and "order" not in text and "receipt" not in text):
        cat = "chats"
    elif _match_any(["bill", "electricity", "wbsedcl", "invoice", "power", "utility", "tariff", "kwh"], combined):
        cat = "bills"
    elif _match_any(["receipt", "order", "subtotal", "store", "supermarket", "swiggy", "zomato", "instamart"], combined):
        cat = "receipts"
    elif _match_any(["recipe", "paneer", "ingredient", "cook", "masala", "curry", "tablespoon", "tsp", "simmer"], combined):
        cat = "recipes"
    elif _match_any(["flight", "boarding", "train", "pnr", "seat", "indigo", "airline", "airport"], combined):
        cat = "travel"
    elif _match_any(["prescription", "clinic", "hospital", "patient", "tablets", "syrup", "dosage", "doctor", "apollo"], combined):
        cat = "medical"
    elif _match_any(["passport", "aadhaar", "pan card", "license", "voter id", "identity", "form 12bb"], combined):
        cat = "identity" if "aadhaar" in combined or "passport" in combined else "forms"
    elif _match_any(["syllabus", "exam", "course", "assignment", "university", "lecture", "student"], combined):
        cat = "study"
    elif _match_any(["roadmap", "milestone", "sprint", "specification", "architecture", "client", "work"], combined):
        cat = "work"
    elif filepath.suffix.lower() in [".png", ".jpg", ".jpeg"] and ("screenshot" in name or "screenshot" in text):
        cat = "screenshots"
    elif "screenshot" in combined or "wpa2" in combined or "wifi" in combined:
        cat = "screenshots"

    date_match = re.search(r"\b(202[0-9]-[01][0-9]-[0-3][0-9])\b", combined)
    if date_match:
        doc_date = date_match.group(1)
    else:
        mtime = datetime.datetime.fromtimestamp(filepath.stat().st_mtime)
        doc_date = mtime.strftime("%Y-%m-%d")

    amounts = re.findall(r"(?:₹|\$|rs\.?|inr)\s?(\d+(?:,\d+)*(?:\.\d{2})?)", combined)

    todos = []
    if any(k in combined for k in ["due", "pay", "deadline", "send", "friday", "submit"]):
        if "pay" in combined:
            task_snippet = "Pay bill / outstanding amount"
        elif "send" in combined or "friday" in combined:
            task_snippet = "Send promised documents or reply to message"
        elif "form" in combined or "submit" in combined:
            task_snippet = "Submit required registration / form"
        else:
            task_snippet = "Action item found in document"
        todos.append({"task": task_snippet, "deadline_or_empty": doc_date})

    issuer = "unknown"
    if "wbsedcl" in combined:
        issuer = "WBSEDCL"
    elif "swiggy" in combined or "instamart" in combined:
        issuer = "Swiggy"
    elif "indigo" in combined:
        issuer = "IndiGo"
    elif "rahul" in combined:
        issuer = "rahul"
    elif "apollo" in combined:
        issuer = "ApolloClinic"

    clean_stem = sanitize_filename(filepath.stem)[:40]
    if not clean_stem:
        clean_stem = f"{cat}-item"

    return {
        "title": clean_stem,
        "category": cat,
        "document_date": doc_date,
        "issuer_or_person": issuer,
        "one_sentence_summary": f"{cat.capitalize()} record concerning {issuer if issuer != 'unknown' else clean_stem}.",
        "app": "WhatsApp" if "chat" in cat else ("Instagram" if "recipe" in cat or "instagram" in combined else ""),
        "readable_text": (content_text[:300] if content_text else filepath.name),
        "search_tags": [cat, clean_stem, issuer, "record", "slothbox", "personal", "document", "file"],
        "todos": todos,
        "amounts": amounts[:3]
    }
