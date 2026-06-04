
import os
import base64
import aiohttp
import tempfile
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

async def analyze_image_from_bytes(image_bytes: bytes, content_type: str = "image/jpeg", question: str = None) -> str:
    """Telegram dan kelgan rasmni Gemini bilan tahlil qiladi"""
    try:
        prompt = question or """Bu rasmni tahlil qil va media kontent uchun tavsiya ber:
1. Rasmda nima bor? (batafsil)
2. Kayfiyat, rang sxemasi
3. Instagram post matni yoz (emoji bilan)
4. Telegram post matni yoz
5. 5 ta hashtag tavsiya qil

O'zbek tilida javob ber."""

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=content_type),
                prompt
            ]
        )
        return response.text

    except Exception as e:
        return f"Rasm tahlil xatosi: {e}"


async def analyze_image_from_url(image_url: str, question: str = None) -> str:
    """URL orqali rasm tahlil qiladi"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                image_bytes = await resp.read()
                content_type = resp.content_type or "image/jpeg"
        return await analyze_image_from_bytes(image_bytes, content_type, question)
    except Exception as e:
        return f"Rasm tahlil xatosi: {e}"


async def analyze_video_from_bytes(video_bytes: bytes, question: str = None) -> str:
    """Video tahlil qiladi"""
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(video_bytes)
            tmp_path = tmp.name

        print("Video yuklanmoqda...")
        uploaded = client.files.upload(file=tmp_path, config={"mime_type": "video/mp4"})

        import time
        while uploaded.state.name == "PROCESSING":
            time.sleep(2)
            uploaded = client.files.get(name=uploaded.name)

        os.unlink(tmp_path)

        if uploaded.state.name == "FAILED":
            return "Video qayta ishlanmadi"

        prompt = question or """Bu videoni tahlil qil:
1. Videoda nima bo'lyapti?
2. Asosiy mavzu va kalit fikrlar
3. Instagram Reels uchun caption yoz
4. Telegram post matni yoz
5. 5 ta hashtag

O'zbek tilida javob ber."""

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[uploaded, prompt]
        )
        client.files.delete(name=uploaded.name)
        return response.text

    except Exception as e:
        return f"Video tahlil xatosi: {e}"


async def suggest_image_for_topic(topic: str) -> str:
    """Mavzu uchun rasm qidiruv so'zi"""
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"'{topic}' mavzusi uchun Pexels da qidirish uchun eng yaxshi inglizcha 3 ta kalit so'z ber. Faqat kalit so'zlar, vergul bilan ajrat."
        )
        return response.text.strip()
    except Exception as e:
        return topic


async def create_post_from_image_analysis(image_bytes: bytes, content_type: str = "image/jpeg") -> dict:
    """Rasmni tahlil qilib, to'liq post tayyorlaydi"""
    try:
        prompt = """Bu rasmni tahlil qilib, media post tayyorla.
JSON formatda javob ber:
{
  "instagram_text": "Instagram post matni (emoji bilan, 150-300 so'z)",
  "telegram_text": "Telegram post matni (batafsil, 200-400 so'z)",
  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"],
  "title": "Qisqa sarlavha (50 belgi)",
  "image_description": "Rasm tavsifi"
}

Faqat JSON, boshqa hech narsa yozma. O'zbek tilida."""

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=content_type),
                prompt
            ]
        )

        import json
        text = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(text)

    except Exception as e:
        return {
            "instagram_text": f"Tahlil xatosi: {e}",
            "telegram_text": f"Tahlil xatosi: {e}",
            "hashtags": [],
            "title": "Rasm post",
            "image_description": ""
        }
