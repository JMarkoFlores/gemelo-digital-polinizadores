from __future__ import annotations

from groq import Groq

from app.config import get_settings


SYSTEM_PROMPT = """
You are an assistant for a digital twin platform focused on agricultural landscapes and pollinator networks.
Answer clearly, avoid inventing unavailable simulation results, and stay grounded in sustainable agriculture,
pollination ecosystem services, and use of the application.
""".strip()


def generate_chat_reply(message: str) -> tuple[str, str]:
    settings = get_settings()
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    client = Groq(api_key=settings.groq_api_key)
    response = client.chat.completions.create(
        model=settings.groq_model,
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
    )
    return response.choices[0].message.content or "", settings.groq_model
