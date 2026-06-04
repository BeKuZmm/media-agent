import anthropic
import os
import json
from agents.writer import write_content
from agents.analyst import analyze_image_from_url, analyze_image_from_bytes, suggest_image_for_topic
from agents.news import get_news_summary, get_trending_topics
from agents.translator import translate, translate_post, detect_language
from agents.scheduler import schedule_post, get_scheduled_posts, cancel_post, parse_time_from_text, start_scheduler
from publisher.telegram_pub import post_to_channel
from publisher.instagram import post_to_instagram
from publisher.image_fetcher import find_image, get_image_bytes

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# Foydalanuvchi suhbat tarixlari
conversation_history = {}

TOOLS = [
    {
        "name": "write_content",
        "description": "Berilgan mavzu bo'yicha Instagram va Telegram uchun kontent yozadi",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Kontent mavzusi"},
                "style": {"type": "string", "enum": ["informative", "entertaining", "news", "promotional"], "default": "informative"},
                "language": {"type": "string", "enum": ["uz", "ru", "en"], "default": "uz"}
            },
            "required": ["topic"]
        }
    },
    {
        "name": "get_news",
        "description": "Mavzu bo'yicha yangiliklar qidirib, post tayyorlaydi",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Yangilik mavzusi"},
                "language": {"type": "string", "enum": ["uz", "ru", "en"], "default": "uz"}
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
                "target_lang": {"type": "string", "enum": ["uz", "ru", "en", "tr", "ar"], "description": "Maqsad til"}
            },
            "required": ["text", "target_lang"]
        }
    },
    {
        "name": "post_now",
        "description": "Tayyorlangan kontentni hozir Telegram kanal va/yoki Instagram ga post qiladi",
        "input_schema": {
            "type": "object",
            "properties": {
                "post_data": {"type": "object", "description": "Post ma'lumotlari (instagram_text, telegram_text, hashtags, title)"},
                "platforms": {"type": "array", "items": {"type": "string", "enum": ["telegram", "instagram"]}, "default": ["telegram", "instagram"]},
                "image_query": {"type": "string", "description": "Rasm qidirish so'zi (inglizcha)"}
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
                "time_text": {"type": "string", "description": "Vaqt matni, masalan: 'ertaga soat 10:00', '2 soatdan keyin'"},
                "platforms": {"type": "array", "items": {"type": "string"}, "default": ["telegram", "instagram"]}
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
                "category": {"type": "string", "enum": ["general", "tech", "business", "sports", "entertainment"], "default": "general"}
            }
        }
    }
]


async def run_tool(name: str, inputs: dict, image_bytes: bytes = None) -> str:
    """Tool ni bajaradi"""

    if name == "write_content":
        result = await write_content(
            inputs["topic"],
            inputs.get("style", "informative"),
            inputs.get("language", "uz")
        )
        return json.dumps(result, ensure_ascii=False)

    elif name == "get_news":
        result = await get_news_summary(inputs["topic"], inputs.get("language", "uz"))
        return json.dumps(result, ensure_ascii=False)

    elif name == "translate_content":
        result = await translate(inputs["text"], inputs["target_lang"])
        return result

    elif name == "post_now":
        post_data = inputs["post_data"]
        platforms = inputs.get("platforms", ["telegram", "instagram"])
        image_query = inputs.get("image_query", post_data.get("title", ""))
        results = {}

        # Rasm qidirish
        image_url = None
        if image_query:
            image_info = await find_image(image_query)
            if image_info:
                image_url = image_info["url"]

        # Telegram ga post
        if "telegram" in platforms:
            tg_result = await post_to_channel(post_data, image_url)
            results["telegram"] = tg_result

        # Instagram ga post
        if "instagram" in platforms:
            ig_result = await post_to_instagram(post_data, image_url)
            results["instagram"] = ig_result

        return json.dumps(results, ensure_ascii=False)

    elif name == "schedule_post":
        from datetime import datetime
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
            result += f"🔹 {p['title']}\n   Vaqt: {p['time']}\n   ID: {p['id']}\n   Status: {p['status']}\n\n"
        return result

    elif name == "cancel_scheduled":
        success = cancel_post(inputs["job_id"])
        return "✅ Post bekor qilindi" if success else "❌ Post topilmadi"

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
    """Foydalanuvchi xabarini qayta ishlaydi"""

    if user_id not in conversation_history:
        conversation_history[user_id] = []

    history = conversation_history[user_id]

    # Rasm bo'lsa Gemini bilan tahlil qilamiz
    extra_context = ""
    if image_bytes:
        from agents.analyst import create_post_from_image_analysis
        analysis = await create_post_from_image_analysis(image_bytes)
        import json
        extra_context = f"\n\n[Foydalanuvchi rasm yubordi. Gemini tahlili: {json.dumps(analysis, ensure_ascii=False)}]"

    history.append({"role": "user", "content": message + extra_context})

    system_prompt = """Sen media menejeri AI agentsan. O'zbek tilida javob berasan.

Quyidagi vazifalarni bajarasan:
- Kontent yozish (Instagram, Telegram uchun)
- Yangiliklar qidirib post tayyorlash
- Matnlarni tarjima qilish
- Postlarni hozir yoki keyinroq publish qilish
- Rejalashtirilgan postlarni boshqarish
- Trend mavzularni ko'rsatish

Har doim aniq va foydali bo'l. Post tayyorganda foydalanuvchiga ko'rsatib, tasdiqlashni so'ra."""

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            tools=TOOLS,
            messages=history
        )

        history.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            if len(history) > 30:
                conversation_history[user_id] = history[-30:]
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return "Javob yo'q"

        # Toollarni bajar
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = await run_tool(block.name, block.input, image_bytes)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result
                })

        history.append({"role": "user", "content": tool_results})


def clear_history(user_id: int):
    if user_id in conversation_history:
        del conversation_history[user_id]
