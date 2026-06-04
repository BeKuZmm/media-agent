import os
import logging
from telegram import Update, BotCommand
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)
from orchestrator import process_message, clear_history
from agents.scheduler import start_scheduler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Salom! Men media menejeri AI agentman.\n\n"
        "🎯 Nima qila olaman:\n"
        "✍️ Kontent yozish (Instagram, Telegram)\n"
        "📰 Yangiliklar qidirib post tayyorlash\n"
        "🌍 Matnlarni tarjima qilish\n"
        "📅 Postlarni rejalashtirish\n"
        "🖼 Rasmlarni tahlil qilish\n"
        "📤 Kanalga avtomatik post qilish\n\n"
        "💬 Menga shunchaki yozing:\n"
        "• \"Sun'iy intellekt haqida post yoz\"\n"
        "• \"Bugungi texnologiya yangiliklar\"\n"
        "• \"Ertaga soat 10 da post qil\"\n"
        "• \"Trend mavzular ko'rsat\"\n\n"
        "/help — qo'llanma\n"
        "/clear — suhbat tarixini tozalash\n"
        "/scheduled — rejalashtirilgan postlar"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Qo'llanma:\n\n"
        "📝 Kontent yozish:\n"
        "\"[mavzu] haqida post yoz\"\n"
        "\"[mavzu] bo'yicha yangilik topib post qil\"\n\n"
        "🌍 Tarjima:\n"
        "\"Bu matnni rus tiliga tarjima qil: [matn]\"\n\n"
        "📅 Rejalashtirish:\n"
        "\"[mavzu] haqida ertaga soat 10 da post qil\"\n"
        "\"2 soatdan keyin post qil\"\n\n"
        "📤 Publish:\n"
        "\"Hozir post qil\" — so'nggi tayyorlangan post e'lon qilinadi\n\n"
        "🖼 Rasm tahlil:\n"
        "Rasm yuboring + savol/izoh\n\n"
        "📊 Boshqa:\n"
        "/scheduled — rejalashtirilgan postlar\n"
        "/clear — tarixni tozalash"
    )


async def scheduled_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents.scheduler import get_scheduled_posts
    posts = get_scheduled_posts()
    if not posts:
        await update.message.reply_text("📅 Rejalashtirilgan postlar yo'q")
        return

    text = "📅 Rejalashtirilgan postlar:\n\n"
    for p in posts:
        text += f"🔹 {p['title']}\n⏰ {p['time']}\n🆔 {p['id']}\n\n"
    await update.message.reply_text(text)


async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_history(update.effective_user.id)
    await update.message.reply_text("🗑 Suhbat tarixi tozalandi!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Matn xabarlarni qayta ishlaydi"""
    user_id = update.effective_user.id
    text = update.message.text

    thinking = await update.message.reply_text("⏳ Ishlamoqda...")

    try:
        response = await process_message(user_id, text)
        # Telegram 4096 belgidan uzun xabar qabul qilmaydi
        if len(response) > 4096:
            for i in range(0, len(response), 4096):
                await update.message.reply_text(response[i:i+4096])
            await thinking.delete()
        else:
            await thinking.edit_text(response)
    except Exception as e:
        logger.error(f"Xato: {e}", exc_info=True)
        await thinking.edit_text(f"❌ Xato yuz berdi: {str(e)[:200]}")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rasm xabarlarni qayta ishlaydi"""
    user_id = update.effective_user.id

    thinking = await update.message.reply_text("🖼 Rasm tahlil qilinmoqda...")

    try:
        # Eng katta rasmni olish
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()

        caption = update.message.caption or "Bu rasm haqida post yoz"
        response = await process_message(user_id, caption, image_bytes=bytes(image_bytes))
        await thinking.edit_text(response)
    except Exception as e:
        logger.error(f"Rasm xatosi: {e}", exc_info=True)
        await thinking.edit_text(f"❌ Rasm qayta ishlanmadi: {str(e)[:200]}")


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Video xabarlarni qayta ishlaydi (Gemini bilan)"""
    user_id = update.effective_user.id

    thinking = await update.message.reply_text("🎬 Video tahlil qilinmoqda... (biroz vaqt oladi)")

    try:
        video = update.message.video or update.message.document
        file = await context.bot.get_file(video.file_id)
        video_bytes = await file.download_as_bytearray()

        from agents.analyst import analyze_video_from_bytes
        caption = update.message.caption or "Bu video haqida post yoz"

        # Video tahlil
        analysis = await analyze_video_from_bytes(bytes(video_bytes), caption)
        response = await process_message(user_id, f"Video tahlili:\n{analysis}\n\nSo'rov: {caption}")
        await thinking.edit_text(response)
    except Exception as e:
        logger.error(f"Video xatosi: {e}", exc_info=True)
        await thinking.edit_text(f"❌ Video qayta ishlanmadi: {str(e)[:200]}")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hujjat/fayl xabarlarni qayta ishlaydi"""
    user_id = update.effective_user.id
    doc = update.message.document

    thinking = await update.message.reply_text("📂 Fayl o'qilmoqda...")

    try:
        file = await context.bot.get_file(doc.file_id)
        file_bytes = await file.download_as_bytearray()

        # Rasm fayl bo'lsa
        if doc.mime_type and doc.mime_type.startswith("image/"):
            caption = update.message.caption or "Bu rasm haqida post yoz"
            response = await process_message(user_id, caption, image_bytes=bytes(file_bytes))
        else:
            # Matnli fayl
            file_content = file_bytes.decode("utf-8", errors="ignore")
            message = update.message.caption or "Bu faylni tahlil qil"
            response = await process_message(user_id, f"{message}\n\nFayl mazmuni:\n{file_content[:3000]}")

        await thinking.edit_text(response)
    except Exception as e:
        logger.error(f"Fayl xatosi: {e}", exc_info=True)
        await thinking.edit_text(f"❌ Fayl qayta ishlanmadi: {str(e)[:200]}")


async def post_init(application):
    """Bot ishga tushganda chaqiriladi"""
    start_scheduler()
    await application.bot.set_my_commands([
        BotCommand("start", "Botni boshlash"),
        BotCommand("help", "Qo'llanma"),
        BotCommand("scheduled", "Rejalashtirilgan postlar"),
        BotCommand("clear", "Tarixni tozalash"),
    ])
    logger.info("✅ Bot ishga tushdi!")


def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("scheduled", scheduled_cmd))
    app.add_handler(CommandHandler("clear", clear_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    logger.info("Bot polling boshlanmoqda...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
