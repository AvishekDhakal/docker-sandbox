import re
from typing import List, Union
import tiktoken

# Initialize tokenizer (for OpenAI-compatible models)
ENCODING_NAME = "cl100k_base"
_tokenizer = tiktoken.get_encoding(ENCODING_NAME)


def count_tokens(text: str) -> int:
    """
    Count the number of tokens in a given text string using the configured tokenizer.
    """
    return len(_tokenizer.encode(text))


def sliding_window(snippets: List[str], max_tokens: int, overlap: int) -> List[str]:
    """
    Combine snippets into chunks based on a token budget with overlap.

    Args:
        snippets: List of text snippets.
        max_tokens: Maximum tokens per chunk.
        overlap: Number of tokens to carry over between chunks.

    Returns:
        List of chunk strings.
    """
    chunks: List[str] = []
    current: List[str] = []
    current_tokens = 0

    for snippet in snippets:
        t = count_tokens(snippet)
        # If adding this snippet would exceed the budget
        if current_tokens + t > max_tokens:
            # Emit current chunk
            chunk_text = "\n".join(current)
            chunks.append(chunk_text)
            # Prepare overlap carry
            encoded = _tokenizer.encode(chunk_text)
            carry_ids = encoded[-overlap:] if overlap < len(encoded) else encoded
            carry_text = _tokenizer.decode(carry_ids)
            # Start new chunk with carry + current snippet
            current = [carry_text, snippet]
            current_tokens = count_tokens(carry_text) + t
        else:
            current.append(snippet)
            current_tokens += t

    # Emit any remaining text
    if current:
        chunks.append("\n".join(current))
    return chunks


def split_markdown_sections(text: str) -> List[str]:
    """
    Split markdown text into sections based on level-2 to level-6 headings.

    Args:
        text: Raw markdown string.

    Returns:
        List of markdown sections (each including its heading).
    """
    # Regex splits on heading lines; keeps the delimiter
    pattern = re.compile(r'(?m)(^#{2,6} .*)')
    parts = pattern.split(text)
    sections: List[str] = []
    if not parts:
        return [text]

    # parts: [pre_content, heading1, content1, heading2, content2, ...]
    it = iter(parts)
    pre = next(it)
    if pre.strip():
        sections.append(pre)
    while True:
        try:
            heading = next(it)
            content = next(it)
            sections.append(heading + "\n" + content)
        except StopIteration:
            break
    return sections


def chunk_markdown(text: str, max_tokens: int, overlap: int) -> List[str]:
    """
    Chunk markdown text by splitting on headings, then applying a sliding window if needed.

    Args:
        text: Raw markdown content.
        max_tokens: Maximum tokens per chunk.
        overlap: Token overlap between chunks.

    Returns:
        List of markdown chunks.
    """
    sections = split_markdown_sections(text)
    # If sections are small enough, return directly; else use sliding window
    return sliding_window(sections, max_tokens, overlap)


def chunk_json_snippets(snippets: List[str], max_tokens: int, overlap: int) -> List[str]:
    """
    Chunk a list of JSON-derived text snippets using the sliding window strategy.

    Args:
        snippets: List of "path: value" strings.
        max_tokens: Maximum tokens per chunk.
        overlap: Token overlap between chunks.

    Returns:
        List of text chunks.
    """
    return sliding_window(snippets, max_tokens, overlap)


def make_chunks(
    data: Union[str, List[str]],
    max_tokens: int = 1000,
    overlap: int = 200
) -> List[str]:
    """
    Unified entrypoint to chunk either markdown text or flattened JSON snippets.

    Args:
        data: Raw markdown string or list of JSON snippet strings.
        max_tokens: Max tokens per chunk (default=1000).
        overlap: Number of tokens to overlap (default=200).

    Returns:
        List of string chunks ready for LLM consumption.
    """
    if isinstance(data, str):
        return chunk_markdown(data, max_tokens, overlap)
    elif isinstance(data, list):
        return chunk_json_snippets(data, max_tokens, overlap)
    else:
        raise TypeError("Data must be either markdown text (str) or list of JSON snippets.")
