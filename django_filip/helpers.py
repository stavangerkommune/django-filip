import logging

logger = logging.getLogger(__name__)


def filip_check_ok(verbose=False):
    print('ok') if verbose else None
    return 'ok'


def build_url(base_url: str, relative_path: str = '') -> str | None:
    """
    Joins a base URL and a relative path into a clean absolute URL.

    - Always treats base as directory prefix (ends with exactly one '/')
    - Strips leading '/' from path → no double slashes
    - Returns None if base is empty or collapses to just '/'
    - Raises ValueError if path looks like absolute/protocol-relative URL


    Examples:

    | Call                                                      |   | Result URL                                      |
    |-----------------------------------------------------------|---|-------------------------------------------------|
    | `build_url("https://api.example.com/v1", "users")`        | → | `https://api.example.com/v1/users`              |
    | `build_url("https://api.example.com/v1/", "/users")`      | → | `https://api.example.com/v1/users`              |
    | `build_url("https://example.com")`                        | → | `https://example.com/`                          |
    | `build_url("https://example.com/api", "Proxy/v1")`        | → | `https://example.com/api/Proxy/v1`              |

    """

    # Security guard (prevents open-redirect / hijack)
    if '://' in relative_path or relative_path.startswith('//'):
        raise ValueError(f'Absolute/protocol-relative path not allowed: {relative_path!r}')

    base_url = f'{str(base_url).rstrip("/")}/'
    relative_path = str(relative_path).lstrip('/')

    if base_url == '/':
        return None

    return f'{base_url}{relative_path}'
