def can_handle(prompt: str) -> bool:
    """Detecta si la orden es para abrir Steam."""
    text = prompt.lower()
    return "steam" in text or "abrir steam" in text

def handle(prompt: str) -> str:
    """Envía la acción de ejecución para Steam."""
    return "ACTION:LAUNCH_APP:steam"