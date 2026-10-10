import logging

import httpx

log = logging.getLogger(__name__)


class ProviderError(Exception):
    def __init__(self, message, status=502):
        super().__init__(message)
        self.message = message
        self.status = status


_client = httpx.Client(
    timeout=httpx.Timeout(20.0, connect=5.0),
    transport=httpx.HTTPTransport(retries=2),
    headers={"User-Agent": "climafeet-truck-routing/1.0"},
)


def get_json(url, params, provider):
    try:
        resp = _client.get(url, params=params)
    except httpx.HTTPError as exc:
        log.warning("%s request failed: %s", provider, exc)
        raise ProviderError(f"{provider} is unreachable right now, try again shortly.") from exc
    if resp.status_code >= 400:
        return resp, None
    return resp, resp.json()
