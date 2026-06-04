import anthropic
import os

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

async def write_content(topic: str, style: str = "informative", language: str = "uz") -> dict:
    """
    Kontent yozuvchi agent
    style: informative, entertaining, news, promotional
    language: uz (o'zbek), ru (rus), en (ingliz)
    """
    lang_map = {
        "uz": "O'zbek tilida",
        "ru": "Rus tilida", 
        "en": "Ingliz tilida"
    }
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

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    import json
    text = response.content[0].text.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    
    try:
        return json.loads(text)
    except:
        return {
            "instagram_text": text,
            "telegram_text": text,
            "hashtags": [],
            "title": topic[:50]
        }
