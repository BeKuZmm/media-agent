import os
import json
from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

LANGUAGES = {
    "uz": "O'zbek", "ru": "Rus", "en": "Ingliz",
    "tr": "Turk", "ar": "Arab", "de": "Nemis", "fr": "Fransuz"
}

async def translate(text: str, target_lang: str, source_lang: str = "auto") -> str:
    target = LANGUAGES.get(target_lang, target_lang)
    prompt = f"""{target} tiliga tarjima qil. Faqat tarjimani yoz, izoh yozma.

Matn:
{text}"""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )
    return response.text.strip()

async def translate_post(post: dict, target_lang: str) -> dict:
    target = LANGUAGES.get(target_lang, target_lang)
    prompt = f"""{target} tiliga tarjima qil.
Hashtaglarni tarjima qilma, faqat instagram_text, telegram_text va title ni tarjima qil.

{json.dumps(post, ensure_ascii=False, indent=2)}

Xuddi shu JSON strukturada qaytar. Faqat JSON."""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )
    text = response.text.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except:
        translated = post.copy()
        translated["instagram_text"] = await translate(post.get("instagram_text", ""), target_lang)
        translated["telegram_text"] = await translate(post.get("telegram_text", ""), target_lang)
        return translated

async def detect_language(text: str) -> str:
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=f"Bu matn qaysi tilda? Faqat til kodini yoz (uz/ru/en/tr/ar): {text[:200]}"
    )
    return response.text.strip().lower()[:2]
