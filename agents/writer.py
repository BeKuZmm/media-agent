import os
import json
from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

async def write_content(topic: str, style: str = "informative", language: str = "uz") -> dict:
    lang_map = {"uz": "O'zbek tilida", "ru": "Rus tilida", "en": "Ingliz tilida"}
    style_map = {
        "informative": "ma'lumotli va tushunarli",
        "entertaining": "qiziqarli va kulgili",
        "news": "yangilik uslubida, qisqa va aniq",
        "promotional": "reklama uslubida, jalb qiluvchi"
    }

    prompt = f"""Sen media kontent yozuvchisan.

Mavzu: {topic}
Uslub: {style_map.get(style, 'informative')}
Til: {lang_map.get(language, "O'zbek tilida")}

Quyidagilarni yoz:
1. Instagram post matni (emoji bilan, 150-300 so'z)
2. Telegram post matni (biroz uzunroq, 200-400 so'z)
3. 5 ta hashtag (Instagram uchun)
4. Qisqa sarlavha (50 belgi)

JSON formatda javob ber:
{{
  "instagram_text": "...",
  "telegram_text": "...",
  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"],
  "title": "..."
}}

Faqat JSON, boshqa hech narsa yozma."""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )

    text = response.text.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except:
        return {
            "instagram_text": text,
            "telegram_text": text,
            "hashtags": [],
            "title": topic[:50]
        }
