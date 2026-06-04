import anthropic
import os
from duckduckgo_search import DDGS

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

async def search_news(topic: str, max_results: int = 5) -> list:
    """Mavzu bo'yicha so'nggi yangiliklar qidiradi"""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.news(topic, max_results=max_results))
        return results
    except Exception as e:
        return []

async def get_news_summary(topic: str, language: str = "uz") -> dict:
    """Yangiliklar qidirib, ulardan post tayyorlaydi"""
    lang_map = {"uz": "O'zbek", "ru": "Rus", "en": "Ingliz"}

    # Yangiliklar qidirish
    news_items = await search_news(topic)

    if not news_items:
        return {
            "found": False,
            "message": f"'{topic}' bo'yicha yangilik topilmadi"
        }

    # Yangiliklar mazmunini birlashtirish
    news_text = ""
    sources = []
    for i, item in enumerate(news_items[:3], 1):
        news_text += f"{i}. {item.get('title', '')}\n{item.get('body', '')}\n\n"
        sources.append({
            "title": item.get('title', ''),
            "url": item.get('url', ''),
            "date": item.get('date', '')
        })

    # Claude bilan post tayyorlash
    prompt = f"""{lang_map.get(language, 'O\'zbek')} tilida yangiliklar asosida post tayyorla.

Yangiliklar:
{news_text}

Quyidagilarni yoz:
1. Instagram post (emoji bilan, qisqa va jalb qiluvchi)
2. Telegram post (batafsil, havolalar bilan)
3. 5 ta hashtag
4. Sarlavha

JSON formatda:
{{
  "instagram_text": "...",
  "telegram_text": "...",
  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"],
  "title": "...",
  "sources": []
}}

Faqat JSON."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    import json
    text = response.content[0].text.strip()
    text = text.replace("```json", "").replace("```", "").strip()

    try:
        result = json.loads(text)
        result["found"] = True
        result["sources"] = sources
        return result
    except:
        return {
            "found": True,
            "instagram_text": text,
            "telegram_text": text,
            "hashtags": [],
            "title": topic,
            "sources": sources
        }


async def get_trending_topics(category: str = "general") -> list:
    """Trend mavzularni qidiradi"""
    queries = {
        "general": "bugungi eng muhim yangiliklar",
        "tech": "texnologiya yangiliklari 2024",
        "business": "iqtisodiyot biznes yangiliklari",
        "sports": "sport yangiliklari bugun",
        "entertainment": "ko'ngilochar yangiliklar"
    }
    query = queries.get(category, queries["general"])
    
    try:
        with DDGS() as ddgs:
            results = list(ddgs.news(query, max_results=10))
        return [{"title": r.get("title"), "url": r.get("url")} for r in results]
    except:
        return []
