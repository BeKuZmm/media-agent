import json
import os
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger

# Rejalashtirilgan postlar (xotirada saqlanadi)
scheduled_posts = {}
scheduler = AsyncIOScheduler()

def start_scheduler():
    """Schedulerni ishga tushiradi"""
    if not scheduler.running:
        scheduler.start()

def stop_scheduler():
    scheduler.shutdown()

async def schedule_post(post_data: dict, publish_time: datetime, publish_func) -> str:
    """Postni ma'lum vaqtga rejalashtiradi"""
    job_id = f"post_{int(publish_time.timestamp())}"

    scheduler.add_job(
        publish_func,
        trigger=DateTrigger(run_date=publish_time),
        args=[post_data],
        id=job_id,
        replace_existing=True
    )

    scheduled_posts[job_id] = {
        "post_data": post_data,
        "publish_time": publish_time.isoformat(),
        "status": "scheduled"
    }

    return job_id


async def schedule_daily(post_func, hour: int = 9, minute: int = 0, topic: str = None) -> str:
    """Har kuni ma'lum vaqtda post qiladi"""
    job_id = f"daily_{hour}_{minute}"

    scheduler.add_job(
        post_func,
        trigger=CronTrigger(hour=hour, minute=minute),
        args=[topic] if topic else [],
        id=job_id,
        replace_existing=True
    )

    return job_id


def get_scheduled_posts() -> list:
    """Rejalashtirilgan postlar ro'yxati"""
    result = []
    for job_id, data in scheduled_posts.items():
        job = scheduler.get_job(job_id)
        result.append({
            "id": job_id,
            "title": data["post_data"].get("title", "Nomsiz"),
            "time": data["publish_time"],
            "status": "active" if job else "completed"
        })
    return result


def cancel_post(job_id: str) -> bool:
    """Rejalashtirilgan postni bekor qiladi"""
    try:
        scheduler.remove_job(job_id)
        if job_id in scheduled_posts:
            scheduled_posts[job_id]["status"] = "cancelled"
        return True
    except:
        return False


def parse_time_from_text(text: str) -> datetime:
    """
    Matndan vaqtni aniqlaydi
    Misol: 'ertaga soat 10:00', '3 soatdan keyin', 'bugun 15:30'
    """
    now = datetime.now()
    text = text.lower().strip()

    # Sodda parsing
    if "ertaga" in text or "tomorrow" in text:
        base = now + timedelta(days=1)
    elif "bugun" in text or "today" in text:
        base = now
    else:
        base = now + timedelta(hours=1)

    # Vaqt qidirish
    import re
    time_match = re.search(r'(\d{1,2}):(\d{2})', text)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2))
        base = base.replace(hour=hour, minute=minute, second=0)
    
    # "N soatdan keyin"
    hours_match = re.search(r'(\d+)\s*soat', text)
    if hours_match:
        base = now + timedelta(hours=int(hours_match.group(1)))

    # "N daqiqadan keyin"
    mins_match = re.search(r'(\d+)\s*daqiqa', text)
    if mins_match:
        base = now + timedelta(minutes=int(mins_match.group(1)))

    return base
