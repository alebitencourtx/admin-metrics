"""Validate reported identifiers without ever making requests to them."""
from urllib.parse import urlsplit


def endpoint_parts(value):
    if not isinstance(value, str) or not value or any(c.isspace() or ord(c) < 32 for c in value):
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme:
            if (parsed.scheme not in ('http', 'https') or not parsed.hostname
                    or parsed.username or parsed.password or parsed.port == 0):
                return None
        elif not value.startswith('/') or value.startswith('//'):
            return None
        return parsed
    except ValueError:
        return None
