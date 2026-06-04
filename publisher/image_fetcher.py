import aiohttp
import os

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "")

async def get_image_from_pexels(query: str) -> dict:
    """Pexels dan bepul rasm oladi"""
    if not PEXELS_API_KEY:
        return None
    
    try:
        headers = {"Authorization": PEXELS_API_KEY}
        url = f"https://api.pexels.com/v1/search?query={query}&per_page=1&orientation=square"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                
        if data.get("photos"):
            photo = data["photos"][0]
            return {
                "url": photo["src"]["large"],
                "photographer": photo["photographer"],
                "source": "Pexels"
            }
    except Exception as e:
        print(f"Pexels xato: {e}")
    return None


async def get_image_from_unsplash(query: str) -> dict:
    """Unsplash dan bepul rasm oladi"""
    if not UNSPLASH_ACCESS_KEY:
        return None
    
    try:
        url = f"https://api.unsplash.com/photos/random?query={query}&client_id={UNSPLASH_ACCESS_KEY}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                
        return {
            "url": data["urls"]["regular"],
            "photographer": data["user"]["name"],
            "source": "Unsplash"
        }
    except Exception as e:
        print(f"Unsplash xato: {e}")
    return None


async def get_image_bytes(image_url: str) -> bytes:
    """Rasm URL dan bytes oladi"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                return await resp.read()
    except Exception as e:
        print(f"Rasm yuklab olish xatosi: {e}")
        return None


async def find_image(query: str) -> dict:
    """Pexels yoki Unsplash dan rasm qidiradi"""
    # Avval Pexels
    image = await get_image_from_pexels(query)
    if image:
        return image
    
    # Keyin Unsplash
    image = await get_image_from_unsplash(query)
    if image:
        return image
    
    return None
