"""Resolve only explicitly named, contained local artifacts."""
from pathlib import Path, PureWindowsPath
from urllib.parse import unquote


def contained_path(root, relative):
    decoded = str(relative)
    for _ in range(3):
        updated = unquote(decoded)
        if updated == decoded:
            break
        decoded = updated
    normalized = decoded.replace('\\', '/')
    if not normalized or '\x00' in normalized or ':' in normalized or PureWindowsPath(decoded).drive or normalized.startswith('/'):
        raise ValueError('An artifact must use a relative path')
    if any(part in ('..', '') for part in normalized.split('/')):
        raise ValueError('Invalid artifact path')
    base = Path(root).resolve()
    candidate = (base / normalized).resolve()
    if not candidate.is_relative_to(base):
        raise ValueError('Artifact escapes its storage directory')
    return candidate
