import os
import time
from typing import List
import openai
from google import genai  # Correct import for the Google GenAI SDK
from google.genai import types  # for GenerateContentConfig

class BaseClient:
    def send_chunk(self, chunk: str) -> str:
        raise NotImplementedError

    def send_chunks(self, chunks: List[str]) -> List[str]:
        return [self.send_chunk(c) for c in chunks]

class OpenAIClient(BaseClient):
    """Client for sending chunks to OpenAI API."""
    def __init__(self, model: str = "gpt-4o-mini", max_retries: int = 3, retry_backoff: float = 2.0):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")
        openai.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

    def send_chunk(self, chunk: str) -> str:
        system_prompt = ("You are a security auditor. Identify up to 3 key findings from the text below. Output a Markdown table with columns: Section, Issue, Recommendation. Be as concise as possible.")
        for attempt in range(1, self.max_retries + 1):
            try:
                response = openai.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {"role": "system",  "content": system_prompt},
                        {"role": "user",    "content": chunk},
                    ],
                    temperature=0.2,
                )
                return response.choices[0].message.content.strip()
            except Exception:
                if attempt == self.max_retries:
                    raise
                time.sleep(self.retry_backoff ** attempt)

class GoogleClient(BaseClient):
    """Client for Google GenAI (Gemini) via the google-genai SDK."""
    def __init__(self, model: str = "gemini-2.5-flash", max_retries: int = 3, retry_backoff: float = 2.0):
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY must be set.")
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

    def send_chunk(self, chunk: str) -> str:
        # 1) Build your instruction
        prompt = (
        "You are a security auditor. For the text below, extract up to 3 findings."
        "Return a JSON array where each item has:"
        "- chunk: the chunk index (integer)"
        "- section: section heading or JSON path (string)"
        "- issue: one-sentence description of the problem (string)"
        "- recommendation: one-sentence fix (string)"
        "Do not output anything else."
        )
        # 2) Combine it with the actual report text
        full_content = prompt + chunk

        # 3) Create the config
        config = types.GenerateContentConfig(temperature=0.2)

        # 4) Send it
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=full_content,    # now includes both prompt *and* chunk
                    config=config,
                )
                return response.text
            except Exception:
                if attempt == self.max_retries:
                    raise
                time.sleep(self.retry_backoff ** attempt)
