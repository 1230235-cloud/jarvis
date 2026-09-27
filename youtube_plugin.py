import requests
import re

def can_handle(prompt: str) -> bool:
    """Determina si este plugin debe encargarse de la petición."""
    return "youtube" in prompt.lower() or "reproduce" in prompt.lower()

def handle(prompt: str) -> str:
    """Ejecuta la lógica de búsqueda del primer video en YouTube."""
    text_lower = prompt.lower()
    query = re.sub(r'\b(busca|pon|en|youtube|reproduce|quiero|escuchar|musica|video|por|favor|de|la|el|los|las)\b', '', text_lower).strip()
    query = " ".join(query.split()) or text_lower.replace("youtube", "").strip()
    
    try:
        search_url = f"https://www.youtube.com/results?search_query={requests.utils.quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(search_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            video_ids = re.findall(r'\"videoId\":\"([a-zA-Z0-9_-]{11})\"', response.text)
            if video_ids:
                first_video_id = video_ids[0]
                return f"ACTION:YOUTUBE_PLAY:https://www.youtube.com/watch?v={first_video_id}"
        return f"ACTION:YOUTUBE_PLAY:https://www.youtube.com/results?search_query={requests.utils.quote(query)}"
    except Exception:
        return f"ACTION:YOUTUBE_PLAY:https://www.youtube.com/results?search_query={requests.utils.quote(query)}"