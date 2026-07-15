import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# gemma2-9b-it has been deprecated on Groq. openai/gpt-oss-120b is Groq's
# current recommended production model with reliable tool-calling support.
# Override via MODEL_NAME in .env if you'd like to use a different model.
MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-oss-120b")


def get_llm() -> ChatGroq:
    """Returns a configured Groq chat model client with tool-calling enabled."""
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your "
            "Groq API key from https://console.groq.com/keys."
        )
    return ChatGroq(
        model=MODEL_NAME,
        api_key=GROQ_API_KEY,
        temperature=0.2,
    )
