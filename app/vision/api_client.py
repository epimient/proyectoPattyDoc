import json
import urllib.error
import urllib.request


class ApiError(RuntimeError):
    pass


class ApiClient:
    """Cliente HTTP mínimo (stdlib) para el backend FastAPI."""

    def __init__(self, base_url: str, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, payload: dict | None = None):
        url = self.base_url + path
        data = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise ApiError(f"{method} {path} -> HTTP {e.code}: {e.read().decode()}") from e
        except urllib.error.URLError as e:
            raise ApiError(f"No se pudo conectar con {url}: {e.reason}") from e

    def start_session(self, plan: dict) -> dict:
        return self._request("POST", "/api/session/start", {"plan": plan})

    def get_session(self, session_id: str) -> dict:
        return self._request("GET", f"/api/session/{session_id}")

    def send_observation(self, session_id: str, obs: dict) -> dict:
        return self._request("POST", f"/api/session/{session_id}/observation", obs)

    def complete_session(self, session_id: str) -> dict:
        return self._request("POST", f"/api/session/{session_id}/complete")
