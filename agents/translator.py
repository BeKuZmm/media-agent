import anthropic
import os

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

LANGUAGES = {
    "uz": "O'zbek",
    "ru": "Rus",
    "en": "Ingliz",
    "tr": "Turk",
    "ar": "Arab",
    "de": "Nemis",
    "fr": "Fransuz"
}

async def translate(text: str, target_lang: str, source_lang: str = "auto") -> str:
    """Matnni tarjima qiladi"""
    target = LANGUAGES.get(target_lang, target_lang)
    source = LANGUAGES.get(source_lang, "avtomatik aniqlanadi")

    prompt = f"""Quyidagi matnni {target} tiliga tarjima qil.
Manba til: {source}
Tarjima sifatli, tabiiy va o'qimishli bo'lsin.
Faqat tarjimani yoz, boshqa izoh yozma.

Matn:
{text}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()


async def translate_post(post: dict, target_lang: str) -> dict:
    """Butun postni tarjima qiladi (instagram, telegram, hashtags)"""
    target = LANGUAGES.get(target_lang, target_lang)

    import json
    prompt = f"""Quyidagi post ma'lumotlarini {target} tiliga tarjima qil.
Hashtaglarni tarjima qilma, faqat instagram_text, telegram_text va title ni tarjima qil.

Kirish:
{json.dumps(post, ensure_ascii=False, indent=2)}

Xuddi shu JSON strukturada qaytar, faqat matnlar tarjima qilingan bo'lsin.
Faqat JSON."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text.strip()
    text = text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(text)
    except:
        translated = post.copy()
        translated["instagram_text"] = await translate(post.get("instagram_text", ""), target_lang)
        translated["telegram_text"] = await translate(post.get("telegram_text", ""), target_lang)
        return translated


async def detect_language(text: str) -> str:
    """Matn tilini aniqlaydi"""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=50,
        messages=[{
            "role": "user",
            "content": f"Bu matn qaysi tilda yozilgan? Faqat til kodini yoz (uz/ru/en/tr/ar/de/fr): {text[:200]}"
        }]
    )
    return response.content[0].text.strip().lower()[:2]
