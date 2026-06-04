import os
import json
from google import genai
from duckduckgo_search import DDGS

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

async def search_news(topic: str, max_results: int = 5) -> list:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.news(topic, max_results=max_results))
        return results
    except Exception as e:
        return []

async def get_news_summary(topic: str, language: str = "uz") -> dict:
    lang_map = {"uz": "O'zbek", "ru": "Rus", "en": "Ingliz"}
    news_items = await search_news(topic)

    if not news_items:
        return {"found": False, "message": f"'{topic}' bo'yicha yangilik topilmadi"}

    news_text = ""
    sources = []
    for i, item in enumerate(news_items[:3], 1):
        news_text += f"{i}. {item.get('title', '')}\n{item.get('body', '')}\n\n"
        sources.append({
            "title": item.get('title', ''),
            "url": item.get('url', ''),
            "date": item.get('date', '')
        })

    prompt = f"""{lang_map.get(language, "O'zbek")} tilida yangiliklar asosida post tayyorla.

Yangiliklar:
{news_text}

JSON formatda:
{{
  "instagram_text": "...",
  "telegram_text": "...",
  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"],
  "title": "..."
}}

Faqat JSON."""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )

    text = response.text.strip().replace("```json", "").replace("```", "").strip()
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
    queries = {
        "general": "bugungi eng muhim yangiliklar",
        "tech": "texnologiya yangiliklari",
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
