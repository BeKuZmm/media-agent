import os
import json
from google import genai
from google.genai import types
from agents.writer import write_content
from agents.analyst import analyze_image_from_url, analyze_image_from_bytes, suggest_image_for_topic, create_post_from_image_analysis
from agents.news import get_news_summary, get_trending_topics
from agents.translator import translate, translate_post, detect_language
from agents.scheduler import schedule_post, get_scheduled_posts, cancel_post, parse_time_from_text, start_scheduler
from publisher.telegram_pub import post_to_channel
from publisher.instagram import post_to_instagram
from publisher.image_fetcher import find_image, get_image_bytes

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

conversation_history = {}

TOOLS_SCHEMA = [
    {
        "name": "write_content",
        "description": "Berilgan mavzu bo'yicha Instagram va Telegram uchun kontent yozadi",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "style": {"type": "string", "enum": ["informative", "entertaining", "news", "promotional"]},
                "language": {"type": "string", "enum": ["uz", "ru", "en"]}
            },
            "required": ["topic"]
        }
    },
    {
        "name": "get_news",
        "description": "Mavzu bo'yicha yangiliklar qidirib post tayyorlaydi",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "language": {"type": "string", "enum": ["uz", "ru", "en"]}
            },
            "required": ["topic"]
        }
    },
    {
        "name": "translate_content",
        "description": "Matnni boshqa tilga tarjima qiladi",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "target_lang": {"type": "string", "enum": ["uz", "ru", "en", "tr", "ar"]}
            },
            "required": ["text", "target_lang"]
        }
    },
    {
        "name": "post_now",
        "description": "Kontentni hozir Telegram kanal va Instagram ga post qiladi",
        "input_schema": {
            "type": "object",
            "properties": {
                "post_data": {"type": "object"},
                "platforms": {"type": "array", "items": {"type": "string"}},
                "image_query": {"type": "string"}
            },
            "required": ["post_data"]
        }
    },
    {
        "name": "schedule_post",
        "description": "Kontentni kelajakda ma'lum vaqtda post qilishni rejalashtiradi",
        "input_schema": {
            "type": "object",
            "properties": {
                "post_data": {"type": "object"},
                "time_text": {"type": "string"},
                "platforms": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["post_data", "time_text"]
        }
    },
    {
        "name": "get_scheduled",
        "description": "Rejalashtirilgan postlar ro'yxatini ko'rsatadi",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "cancel_scheduled",
        "description": "Rejalashtirilgan postni bekor qiladi",
        "input_schema": {
            "type": "object",
            "properties": {"job_id": {"type": "string"}},
            "required": ["job_id"]
        }
    },
    {
        "name": "get_trending",
        "description": "Trend mavzularni ko'rsatadi",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": ["general", "tech", "business", "sports", "entertainment"]}
            }
        }
    }
]

# Gemini uchun tool formatiga o'tkazish
def build_gemini_tools():
    from google.genai.types import Tool, FunctionDeclaration
    declarations = []
    for t in TOOLS_SCHEMA:
        declarations.append(FunctionDeclaration(
            name=t["name"],
            description=t["description"],
            parameters=t["input_schema"]
        ))
    return [Tool(function_declarations=declarations)]


async def run_tool(name: str, inputs: dict, image_bytes: bytes = None) -> str:
    if name == "write_content":
        result = await write_content(inputs["topic"], inputs.get("style", "informative"), inputs.get("language", "uz"))
        return json.dumps(result, ensure_ascii=False)

    elif name == "get_news":
        result = await get_news_summary(inputs["topic"], inputs.get("language", "uz"))
        return json.dumps(result, ensure_ascii=False)

    elif name == "translate_content":
        return await translate(inputs["text"], inputs["target_lang"])

    elif name == "post_now":
        post_data = inputs["post_data"]
        platforms = inputs.get("platforms", ["telegram", "instagram"])
        image_query = inputs.get("image_query", post_data.get("title", ""))
        results = {}

        image_url = None
        if image_query:
            image_info = await find_image(image_query)
            if image_info:
                image_url = image_info["url"]

        if "telegram" in platforms:
            results["telegram"] = await post_to_channel(post_data, image_url)
        if "instagram" in platforms:
            results["instagram"] = await post_to_instagram(post_data, image_url)

        return json.dumps(results, ensure_ascii=False)

    elif name == "schedule_post":
        post_data = inputs["post_data"]
        platforms = inputs.get("platforms", ["telegram", "instagram"])
        publish_time = parse_time_from_text(inputs["time_text"])

        async def publish(pd):
            if "telegram" in platforms:
                await post_to_channel(pd)
            if "instagram" in platforms:
                await post_to_instagram(pd)

        job_id = await schedule_post(post_data, publish_time, publish)
        return f"✅ Post rejalashtirildi! ID: {job_id}, Vaqt: {publish_time.strftime('%d.%m.%Y %H:%M')}"

    elif name == "get_scheduled":
        posts = get_scheduled_posts()
        if not posts:
            return "Rejalashtirilgan postlar yo'q"
        result = "📅 Rejalashtirilgan postlar:\n\n"
        for p in posts:
            result += f"🔹 {p['title']}\n   Vaqt: {p['time']}\n   ID: {p['id']}\n\n"
        return result

    elif name == "cancel_scheduled":
        success = cancel_post(inputs["job_id"])
        return "✅ Bekor qilindi" if success else "❌ Topilmadi"

    elif name == "get_trending":
        topics = await get_trending_topics(inputs.get("category", "general"))
        if not topics:
            return "Trend mavzular topilmadi"
        result = "🔥 Trend mavzular:\n\n"
        for i, t in enumerate(topics[:5], 1):
            result += f"{i}. {t['title']}\n"
        return result

    return "Noma'lum tool"


async def process_message(user_id: int, message: str, image_bytes: bytes = None) -> str:
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    history = conversation_history[user_id]

    # Rasm bo'lsa Gemini bilan tahlil
    extra_context = ""
    if image_bytes:
        analysis = await create_post_from_image_analysis(image_bytes)
        extra_context = f"\n\n[Foydalanuvchi rasm yubordi. Tahlil: {json.dumps(analysis, ensure_ascii=False)}]"

    system_prompt = """Sen media menejeri AI agentsan. O'zbek tilida javob berasan.
Vazifalar: kontent yozish, yangiliklar qidirish, tarjima, post rejalashtirish, publish qilish.
Har doim aniq va foydali bo'l."""

    # Tarix + yangi xabar
    contents = []
    for h in history:
        contents.append({"role": h["role"], "parts": [{"text": h["content"]}]})
    contents.append({"role": "user", "parts": [{"text": system_prompt + "\n\n" + message + extra_context}]})

    gemini_tools = build_gemini_tools()

    # Agent sikli
    while True:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=contents,
            config=types.GenerateContentConfig(tools=gemini_tools)
        )

        candidate = response.candidates[0]
        parts = candidate.content.parts

        # Tool chaqirilganmi?
        tool_calls = [p for p in parts if hasattr(p, "function_call") and p.function_call]

        if not tool_calls:
            # Javob tayyor
            text = ""
            for p in parts:
                if hasattr(p, "text") and p.text:
                    text += p.text
            history.append({"role": "user", "content": message})
            history.append({"role": "model", "content": text})
            if len(history) > 30:
                conversation_history[user_id] = history[-30:]
            return text or "Javob yo'q"

        # Tool natijalarini bajarish
        contents.append({"role": "model", "parts": [{"function_call": p.function_call} for p in tool_calls]})

        tool_results = []
        for p in tool_calls:
            fc = p.function_call
            result = await run_tool(fc.name, dict(fc.args))
            tool_results.append({
                "function_response": {
                    "name": fc.name,
                    "response": {"result": result}
                }
            })

        contents.append({"role": "user", "parts": tool_results})


def clear_history(user_id: int):
    if user_id in conversation_history:
        del conversation_history[user_id]
