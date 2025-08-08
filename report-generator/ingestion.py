import json
from typing import Any, List


def flatten_json(data: Any, prefix: str = "") -> List[str]:
    """
    Recursively flatten a JSON-like structure into a list of "path: value" strings.

    Args:
        data: The JSON data (dict, list, or primitive).
        prefix: The prefix path for nested keys.

    Returns:
        A list of flattened "path: value" entries.
    """
    items: List[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            new_prefix = f"{prefix}.{key}" if prefix else key
            items.extend(flatten_json(value, new_prefix))
    elif isinstance(data, list):
        for idx, value in enumerate(data):
            new_prefix = f"{prefix}[{idx}]"
            items.extend(flatten_json(value, new_prefix))
    else:
        # Primitive value
        items.append(f"{prefix}: {data}")
    return items


def load_markdown(path: str) -> str:
    """
    Read a Markdown file and return its content as a single string.

    Args:
        path: Filesystem path to the .md file.

    Returns:
        Raw markdown text.
    """
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def load_json(path: str) -> List[str]:
    """
    Read a JSON file, parse it, and flatten into key-value strings.

    Args:
        path: Filesystem path to the .json file.

    Returns:
        A list of flattened JSON entries.
    """
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return flatten_json(data)


def ingest(path: str) -> Any:
    """
    Ingests a report file, returning raw text for markdown or a list of strings for JSON.

    Args:
        path: Path to the report (.md or .json).

    Returns:
        - str: Raw markdown content if .md
        - List[str]: Flattened JSON entries if .json

    Raises:
        ValueError: If file extension is not supported.
    """
    lowered = path.lower()
    if lowered.endswith('.md'):
        return load_markdown(path)
    elif lowered.endswith('.json'):
        return load_json(path)
    else:
        raise ValueError(f"Unsupported file type '{path}', only .md and .json are supported.")
