def sanitize_filename(filename: str) -> str:
    """Entfernt ungültige Zeichen aus Dateinamen."""
    return "".join(c for c in filename if c.isalnum() or c in " ._-").rstrip()