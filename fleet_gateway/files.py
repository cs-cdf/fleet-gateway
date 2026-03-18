"""
fleet_gateway.files — File attachment support.

Loads local files and converts them to OpenAI-compatible content blocks
for injection into LLM messages. Handles images (base64 data URI),
text/code (plain text), PDF (extracted text if pypdf available), and
unknown binary files (placeholder).

Zero external dependencies for core functionality. pypdf is optional.

Usage:
    from fleet_gateway.files import inject_files, suggest_capability

    messages = inject_files(
        [{"role": "user", "content": "Review this"}],
        files=["src/auth.py", "diagram.png"],
    )
    fleet.call("vision", messages)
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import List, Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Extension sets
# ---------------------------------------------------------------------------

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
_TEXT_EXTENSIONS = {
    ".txt", ".py", ".js", ".ts", ".mjs", ".cjs",
    ".md", ".json", ".yaml", ".yml", ".toml", ".csv",
    ".xml", ".html", ".htm", ".sh", ".bash", ".zsh",
    ".rs", ".go", ".java", ".c", ".cpp", ".h", ".hpp",
    ".rb", ".php", ".swift", ".kt", ".scala", ".r",
    ".sql", ".graphql", ".proto", ".tf", ".env",
    ".ini", ".cfg", ".conf", ".log",
}
_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

# Size guards to prevent accidental loading of huge files
_MAX_IMAGE_BYTES = 50 * 1024 * 1024   # 50 MB
_MAX_TEXT_BYTES  = 10 * 1024 * 1024   # 10 MB


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_file(path) -> dict:
    """Load a file and return an OpenAI-compatible content block.

    - Images  → {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
    - Text    → {"type": "text", "text": "# filename\\n...file contents..."}
    - PDF     → {"type": "text", "text": "...extracted text..."} (requires pypdf, else placeholder)
    - Unknown → {"type": "text", "text": "[binary file: filename, N bytes]"}

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file exceeds the size limit.
    """
    # Resolve to canonical absolute path — eliminates ../ traversal and symlinks
    p = Path(path).resolve()
    ext = p.suffix.lower()
    name = p.name

    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if ext in _IMAGE_EXTENSIONS:
        size = p.stat().st_size
        if size > _MAX_IMAGE_BYTES:
            raise ValueError(f"Image too large: {size:,} bytes (max {_MAX_IMAGE_BYTES:,})")
        mime = _MIME.get(ext, "image/jpeg")
        data = p.read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        return {
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{b64}"},
        }

    if ext in _TEXT_EXTENSIONS:
        size = p.stat().st_size
        if size > _MAX_TEXT_BYTES:
            raise ValueError(f"File too large: {size:,} bytes (max {_MAX_TEXT_BYTES:,})")
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
            return {"type": "text", "text": f"# {name}\n{text}"}
        except Exception as e:
            log.warning("Could not read text file %s: %s", path, e)
            return {"type": "text", "text": f"[could not read {name}: {e}]"}

    if ext == ".pdf":
        return _load_pdf(p)

    size = p.stat().st_size
    return {"type": "text", "text": f"[binary file: {name}, {size} bytes]"}


def files_to_blocks(files: list) -> list:
    """Convert a list of file paths to OpenAI content blocks.

    Skips missing or unreadable files with a warning instead of raising.
    """
    blocks = []
    for path in files:
        try:
            block = load_file(path)
            blocks.append(block)
        except FileNotFoundError:
            log.warning("Skipping missing file: %s", path)
        except Exception as e:
            log.warning("Skipping file %s: %s", path, e)
    return blocks


def inject_files(messages: list, files: list) -> list:
    """Inject file content blocks into the last user message.

    Converts the last user message content from str to list:
        {"role": "user", "content": "prompt"}
      → {"role": "user", "content": [{"type":"text","text":"prompt"}, ...blocks]}

    System messages are left untouched. Returns a new list (no mutation).
    If files is empty or all files are missing, returns messages unchanged.
    """
    if not files:
        return messages

    blocks = files_to_blocks(files)
    if not blocks:
        return messages

    result = [dict(msg) for msg in messages]

    last_user_idx = next(
        (i for i in range(len(result) - 1, -1, -1) if result[i].get("role") == "user"),
        None,
    )

    if last_user_idx is None:
        result.append({"role": "user", "content": blocks})
        return result

    msg = result[last_user_idx]
    content = msg.get("content", "")

    if isinstance(content, str):
        new_content = []
        if content:
            new_content.append({"type": "text", "text": content})
        new_content.extend(blocks)
    elif isinstance(content, list):
        new_content = list(content) + blocks
    else:
        new_content = blocks

    result[last_user_idx] = {**msg, "content": new_content}
    return result


def suggest_capability(files: list) -> str:
    """Suggest a routing capability based on file types.

    Returns 'vision' if any image is present, 'coding' if all are code/text,
    'general' otherwise.
    """
    if not files:
        return "general"

    has_image = any(Path(f).suffix.lower() in _IMAGE_EXTENSIONS for f in files)
    if has_image:
        return "vision"

    has_text = any(
        Path(f).suffix.lower() in _TEXT_EXTENSIONS or Path(f).suffix.lower() == ".pdf"
        for f in files
    )
    return "coding" if has_text else "general"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_pdf(p: Path) -> dict:
    try:
        import pypdf  # type: ignore
        reader = pypdf.PdfReader(str(p))
        pages = [
            f"[Page {i}]\n{page.extract_text()}"
            for i, page in enumerate(reader.pages, 1)
            if page.extract_text() and page.extract_text().strip()
        ]
        extracted = "\n\n".join(pages) if pages else "[PDF: no extractable text]"
        return {"type": "text", "text": f"# {p.name}\n{extracted}"}
    except ImportError:
        size = p.stat().st_size
        return {
            "type": "text",
            "text": f"[PDF file: {p.name}, {size} bytes — install pypdf to extract text]",
        }
    except Exception as e:
        log.warning("Could not extract PDF %s: %s", p, e)
        return {"type": "text", "text": f"[PDF extraction failed for {p.name}: {e}]"}
