"""
local Ollama vision model athat can analyze comic covers for identification. 

inputs: 
    - image_path: str

returns: 
    {
        "series_title": "the comic's series title, best guess, correcting for stylized fonts",
        "issue_number": "the issue number if visible, else null",
        "publisher": "DC, Marvel, or other/unknown",
        "creators_visible": ["any creator surnames visible on the cover, e.g. writer/artist credits"],
        "confidence": "high, medium, or low - your confidence in series_title",
        "cover_date": Optional[str] = None
        "storyline": Optional[str] = None
        "characters": Optional[str] = None  # comma separated
    }

Usage:
    ollama pull qwen3-vl:8b
    ollama serve
    on terminal run:
    python ollama_ocr.py path/to/cropped_cover.jpg
"""

import base64
import json
import subprocess
import sys
import time
from pathlib import Path

import requests

OLLAMA_BASE = "http://localhost:11434"
OLLAMA_URL = f"{OLLAMA_BASE}/api/generate"
MODEL = "qwen3-vl:8b"


def ensure_ollama_running(timeout: float = 15.0) -> None:
    """
    Check if the Ollama server is reachable. If not, launch `ollama serve`
    as a background process and wait for it to come up before continuing.
    This means the script works even if the Ollama tray app / GUI isn't open.
    """
    try:
        requests.get(f"{OLLAMA_BASE}/api/tags", timeout=1)
        return  # already running, nothing to do
    except requests.exceptions.ConnectionError:
        pass  # not running yet - fall through and start it

    print("Ollama server not detected. Starting it now...")

    # CREATE_NO_WINDOW keeps this from popping up a console window on Windows.
    # On Linux/Mac this flag doesn't apply, so we just omit it there.
    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

    subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )

    # Poll until it responds or we give up
    start = time.time()
    while time.time() - start < timeout:
        try:
            requests.get(f"{OLLAMA_BASE}/api/tags", timeout=1)
            print("Ollama server is up.")
            return
        except requests.exceptions.ConnectionError:
            time.sleep(0.5)

    raise RuntimeError(
        f"Ollama did not start within {timeout} seconds. "
        "Is it installed and on your PATH?"
    )

# Ask for strict JSON so this can be parsed and fed straight into SeriesMatcher
# as an additional candidate/signal, or compared directly against its output.
PROMPT = """You are looking at the cover of a single comic book issue.

Extract the following fields as JSON only, with no other text, no markdown
fences, and no commentary:

{
  "series_title": "the comic's series title, best guess, correcting for stylized fonts",
  "issue_number": "the issue number if visible, else null",
  "publisher": "DC, Marvel, or other/unknown",
  "creators_visible": ["any creator surnames visible on the cover, e.g. writer/artist credits"],
  "confidence": "high, medium, or low - your confidence in series_title",
  "cover_date": Optional[str] = None
  "storyline": Optional[str] = None
  "characters": Optional[str] = None  # comma separated

}

Be careful with heavily stylized logos (foil effects, unusual lettering) -
use surrounding visual context (character depicted, color scheme, layout)
to infer the correct title even if the letters are hard to read literally.
"""


def encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def query_ollama_vision(image_path: str) -> dict:
    payload = {
        "model": MODEL,
        "prompt": PROMPT,
        "images": [encode_image(image_path)],
        "stream": False,
        "options": {
            "temperature": 0.1,  # low temp - we want consistent extraction, not creativity
        },
    }

    start = time.time()
    resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
    resp.raise_for_status()
    elapsed = time.time() - start

    result = resp.json()
    raw_text = result.get("response", "")

    if not raw_text.strip():
        print("DEBUG: empty response. Full Ollama payload was:")
        print(json.dumps(result, indent=2))

    # Models sometimes wrap JSON in ```json fences even when not asked to -
    # strip those before parsing.
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        print("WARNING: model did not return valid JSON. Raw output:")
        print(raw_text)
        parsed = {"raw": raw_text}

    parsed["_elapsed_seconds"] = round(elapsed, 2)
    parsed["_model"] = MODEL
    return parsed


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_ollama_vision.py <image_path> [<image_path> ...]")
        sys.exit(1)

    ensure_ollama_running()

    for image_path in sys.argv[1:]:
        if not Path(image_path).exists():
            print(f"Skipping missing file: {image_path}")
            continue

        print(f"\n=== {image_path} ===")
        result = query_ollama_vision(image_path)
        print(json.dumps(result, indent=2))




if __name__ == "__main__":
    main()