import os
import asyncio
from instagrapi import Client
from instagrapi.exceptions import LoginRequired
import tempfile
import aiohttp

# Instagram client (global, bir marta login)
_ig_client = None

def get_instagram_client() -> Client:
    """Instagram clientini qaytaradi (lazy init)"""
    global _ig_client
    if _ig_client is None:
        _ig_client = Client()
        username = os.environ.get("INSTAGRAM_USERNAME")
        password = os.environ.get("INSTAGRAM_PASSWORD")
        
        if not username or not password:
            raise ValueError("INSTAGRAM_USERNAME va INSTAGRAM_PASSWORD kerak!")
        
        # Session fayli bor bo'lsa ishlatamiz (qayta login qilmaslik uchun)
        session_file = "/tmp/ig_session.json"
        try:
            _ig_client.load_settings(session_file)
            _ig_client.login(username, password)
            _ig_client.dump_settings(session_file)
        except:
            _ig_client.login(username, password)
            _ig_client.dump_settings(session_file)
    
    return _ig_client


async def post_photo_to_instagram(image_bytes: bytes, caption: str) -> dict:
    """Instagram ga rasm post qiladi"""
    try:
        cl = get_instagram_client()
        
        # Rasmni vaqtinchalik faylga saqlash
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name
        
        # Post qilish (blokirovka qilmaslik uchun thread da)
        loop = asyncio.get_event_loop()
        media = await loop.run_in_executor(
            None,
            lambda: cl.photo_upload(tmp_path, caption)
        )
        
        # Vaqtinchalik faylni o'chirish
        os.unlink(tmp_path)
        
        return {
            "success": True,
            "media_id": str(media.id),
            "url": f"https://www.instagram.com/p/{media.code}/"
        }
        
    except LoginRequired:
        global _ig_client
        _ig_client = None  # Qayta login uchun reset
        return {"success": False, "error": "Instagram login xatosi. Qayta urinib ko'ring."}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def post_to_instagram(post_data: dict, image_url: str = None) -> dict:
    """
    To'liq Instagram posting funksiyasi
    post_data: {instagram_text, hashtags, title}
    image_url: rasm havolasi (ixtiyoriy)
    """
    # Captionni tayyorlash
    caption = post_data.get("instagram_text", "")
    hashtags = " ".join(post_data.get("hashtags", []))
    if hashtags:
        caption += f"\n\n{hashtags}"
    
    # Rasm olish
    image_bytes = None
    if image_url:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                image_bytes = await resp.read()
    
    if not image_bytes:
        return {"success": False, "error": "Rasm topilmadi. Instagram post uchun rasm kerak."}
    
    return await post_photo_to_instagram(image_bytes, caption)
