import os
import base64
import aiohttp
import google.generativeai as genai
import tempfile

# Gemini sozlash
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

def get_vision_model():
    return genai.GenerativeModel("gemini-1.5-pro")

def get_flash_model():
    return genai.GenerativeModel("gemini-1.5-flash")


async def analyze_image_from_bytes(image_bytes: bytes, content_type: str = "image/jpeg", question: str = None) -> str:
    """Telegram dan kelgan rasmni Gemini bilan tahlil qiladi"""
    try:
        model = get_vision_model()

        prompt = question or """Bu rasmni tahlil qil va media kontent uchun tavsiya ber:
1. Rasmda nima bor? (batafsil)
2. Kayfiyat, rang sxemasi
3. Instagram post matni yoz (emoji bilan)
4. Telegram post matni yoz
5. 5 ta hashtag tavsiya qil

O'zbek tilida javob ber."""

        image_part = {
            "mime_type": content_type,
            "data": base64.b64encode(image_bytes).decode("utf-8")
        }

        response = model.generate_content([prompt, image_part])
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
    """Video tahlil qiladi (Gemini File API orqali)"""
    try:
        # Vaqtinchalik faylga saqlash
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(video_bytes)
            tmp_path = tmp.name

        # Gemini File API ga yuklash
        print("Video yuklanmoqda...")
        video_file = genai.upload_file(tmp_path, mime_type="video/mp4")

        # Fayl tayyor bo'lishini kutish
        import time
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = genai.get_file(video_file.name)

        os.unlink(tmp_path)

        if video_file.state.name == "FAILED":
            return "Video qayta ishlanmadi"

        prompt = question or """Bu videoni tahlil qil:
1. Videoda nima bo'lyapti?
2. Asosiy mavzu va kalit fikrlar
3. Instagram Reels uchun caption yoz
4. Telegram post matni yoz
5. 5 ta hashtag

O'zbek tilida javob ber."""

        model = get_vision_model()
        response = model.generate_content([prompt, video_file])

        # Faylni o'chirish
        genai.delete_file(video_file.name)

        return response.text

    except Exception as e:
        return f"Video tahlil xatosi: {e}"


async def generate_image_description(topic: str) -> str:
    """Mavzu uchun rasm tavsifi yaratadi (Unsplash/Pexels qidiruvi uchun)"""
    try:
        model = get_flash_model()
        response = model.generate_content(
            f"'{topic}' mavzusi uchun Unsplash/Pexels da qidirish uchun eng yaxshi inglizcha 3 ta kalit so'z ber. Faqat kalit so'zlar, vergul bilan ajrat."
        )
        return response.text.strip()
    except Exception as e:
        return topic


async def suggest_image_for_topic(topic: str) -> str:
    """Mavzu uchun qanday rasm kerakligini tavsiya qiladi"""
    return await generate_image_description(topic)


async def create_post_from_image_analysis(image_bytes: bytes, content_type: str = "image/jpeg") -> dict:
    """Rasmni tahlil qilib, to'liq post tayyorlaydi"""
    try:
        model = get_vision_model()

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

        image_part = {
            "mime_type": content_type,
            "data": base64.b64encode(image_bytes).decode("utf-8")
        }

        response = model.generate_content([prompt, image_part])
        text = response.text.strip().replace("```json", "").replace("```", "").strip()

        import json
        return json.loads(text)

    except Exception as e:
        return {
            "instagram_text": f"Tahlil xatosi: {e}",
            "telegram_text": f"Tahlil xatosi: {e}",
            "hashtags": [],
            "title": "Rasm post",
            "image_description": ""
        }
