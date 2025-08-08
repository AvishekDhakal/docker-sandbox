# cost_estimator.py

import tiktoken

# ―――――――――――――――――――――――
# Pricing tables in USD per 1 000 000 tokens
# ―――――――――――――――――――――――

# OpenAI API pricing
OPENAI_PRICING = {
    # GPT-4 Turbo: $10 input / $30 output per 1M tokens
    # :contentReference[oaicite:0]{index=0}
    "gpt-4-turbo":     {"input": 10.0,  "output": 30.0},
    # GPT-4: $30 input / $60 output per 1M tokens
    # :contentReference[oaicite:1]{index=1}
    "gpt-4":           {"input": 30.0,  "output": 60.0},
    # GPT-4-32k: $60 input / $120 output per 1M tokens
    # :contentReference[oaicite:2]{index=2}
    "gpt-4-32k":       {"input": 60.0,  "output":120.0},
    # GPT-3.5 Turbo: $0.50 input / $1.50 output per 1M tokens
    # :contentReference[oaicite:3]{index=3}
    "gpt-3.5-turbo":   {"input": 0.5,   "output": 1.5},
    # GPT-4o-mini (optional): $0.00003 per token ≈ $30 per 1M tokens
    # :contentReference[oaicite:4]{index=4}
    "gpt-4o-mini":     {"input":30.0,   "output":30.0},
}

# Google Gemini Developer API pricing
GOOGLE_PRICING = {
    # Gemini 2.5 Pro: $1.25 input / $10.00 output per 1M tokens
    # :contentReference[oaicite:5]{index=5}
    "gemini-2.5-pro":       {"input": 1.25, "output": 10.0},
    # Gemini 2.5 Flash: $0.30 input / $2.50 output per 1M tokens
    # :contentReference[oaicite:6]{index=6}
    "gemini-2.5-flash":     {"input": 0.30, "output":  2.50},
    # Gemini 2.5 Flash-Lite: $0.10 input / $0.40 output per 1M tokens
    # :contentReference[oaicite:7]{index=7}
    "gemini-2.5-flash-lite":{"input": 0.10, "output":  0.40},
    # Gemini 2.0 Flash: $0.10 input / $0.40 output per 1M tokens
    # :contentReference[oaicite:8]{index=8}
    "gemini-2.0-flash":     {"input": 0.10, "output":  0.40},
    # Note: Reuters reported cost-effective usage of Flash-Lite at $0.019 per 1M tokens
    # :contentReference[oaicite:9]{index=9}
}

def estimate_tokens(chunks):
    """
    Count total tokens across all chunks using cl100k_base encoding.
    """
    enc = tiktoken.get_encoding("cl100k_base")
    return sum(len(enc.encode(chunk)) for chunk in chunks)

def estimate_cost(chunks, model, provider="OpenAI"):
    """
    Estimate total tokens and cost in USD for the given model/provider.
    
    Returns:
        total_tokens (int): Sum of input tokens.
        total_cost   (float): Combined input+output cost in USD.
    """
    total_tokens = estimate_tokens(chunks)

    if provider == "OpenAI":
        pricing = OPENAI_PRICING.get(model)
        if not pricing:
            raise ValueError(f"Unknown OpenAI model: {model}")
    else:  # Google
        pricing = GOOGLE_PRICING.get(model)
        if not pricing:
            raise ValueError(f"Unknown Google model: {model}")

    # Convert tokens to millions
    millions = total_tokens / 1_000_000

    input_cost  = pricing["input"]  * millions
    output_cost = pricing["output"] * millions
    total_cost  = input_cost + output_cost

    return total_tokens, total_cost
