def can_handle(prompt: str) -> bool:
    """Detecta si la orden es para abrir Visual Studio Code."""
    text = prompt.lower()
    return "visual studio" in text or "vs code" in text or "abrir code" in text

def handle(prompt: str) -> str:
    """Envía la acción de ejecución para VS Code."""
    return "ACTION:LAUNCH_APP:code"
