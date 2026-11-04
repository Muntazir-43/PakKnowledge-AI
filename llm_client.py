
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL_NAME = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

_api_key = os.getenv("GROQ_API_KEY")

if not _api_key:
    raise RuntimeError(
        "GROQ_API_KEY was not found. "
        "Add it to the project's .env file."
    )

_client = OpenAI(
    api_key=_api_key,
    base_url="https://api.groq.com/openai/v1",
    timeout=60.0,
    max_retries=2,
)


def generate_text(
    prompt: str,
    system_prompt: str = (
        "You are a helpful AI assistant. "
        "Provide clear, accurate, and relevant responses."
    ),
) -> str:
    """Generate text using the configured Groq model."""

    if not prompt or not prompt.strip():
        raise ValueError("The prompt cannot be empty.")

    response = _client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
    )

    content = response.choices[0].message.content

    if not content:
        raise RuntimeError("The model returned an empty response.")

    return content.strip()
