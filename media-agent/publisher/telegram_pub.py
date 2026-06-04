import os
import aiohttp
from telegram import Bot
from telegram.constants import ParseMode

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID")

async def get_bot() -> Bot:
    return Bot(token=TELEGRAM_BOT_TOKEN)

async def post_text_to_channel(text: str) -> dict:
    """Telegram kanalga matn post qiladi"""
    try:
        bot = await get_bot()
        msg = await bot.send_message(
            chat_id=TELEGRAM_CHANNEL_ID,
            text=text,
            parse_mode=ParseMode.HTML
        )
        return {"success": True, "message_id": msg.message_id}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def post_photo_to_channel(image_url: str, caption: str) -> dict:
    """Telegram kanalga rasm bilan post qiladi"""
    try:
        bot = await get_bot()

        # URL orqali yuborish
        msg = await bot.send_photo(
            chat_id=TELEGRAM_CHANNEL_ID,
            photo=image_url,
            caption=caption,
            parse_mode=ParseMode.HTML
        )
        return {"success": True, "message_id": msg.message_id}
    except Exception as e:
        # Agar URL ishlamasa bytes orqali urinib ko'ramiz
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    image_bytes = await resp.read()
            
            bot = await get_bot()
            msg = await bot.send_photo(
                chat_id=TELEGRAM_CHANNEL_ID,
                photo=image_bytes,
                caption=caption,
                parse_mode=ParseMode.HTML
            )
            return {"success": True, "message_id": msg.message_id}
        except Exception as e2:
            return {"success": False, "error": str(e2)}


async def post_to_channel(post_data: dict, image_url: str = None) -> dict:
    """
    To'liq Telegram kanal posting funksiyasi
    post_data: {telegram_text, hashtags, title}
    """
    text = post_data.get("telegram_text", "")
    hashtags = " ".join(post_data.get("hashtags", []))
    if hashtags:
        text += f"\n\n{hashtags}"

    if image_url:
        return await post_photo_to_channel(image_url, text[:1024])  # Caption limit
    else:
        return await post_text_to_channel(text)


async def post_video_to_channel(video_bytes: bytes, caption: str) -> dict:
    """Telegram kanalga video post qiladi"""
    try:
        bot = await get_bot()
        msg = await bot.send_video(
            chat_id=TELEGRAM_CHANNEL_ID,
            video=video_bytes,
            caption=caption[:1024],
            parse_mode=ParseMode.HTML
        )
        return {"success": True, "message_id": msg.message_id}
    except Exception as e:
        return {"success": False, "error": str(e)}
