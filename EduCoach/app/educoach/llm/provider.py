from collections.abc import Callable
from dataclasses import dataclass, field
import json
from urllib.error import URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class LLMRequest:
    system_prompt: str
    user_message: str
    memory_context: str = ""


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class LLMProvider:
    def health(self) -> bool:
        raise NotImplementedError

    def generate(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError


class OllamaProviderError(RuntimeError):
    pass


class OllamaProvider(LLMProvider):
    def __init__(self, model: str, base_url: str = "http://127.0.0.1:11434") -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")

    def generate(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.memory_context + "\n" + request.user_message},
            ],
        }
        http_request = Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(http_request, timeout=120) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise OllamaProviderError("Ollama provider çağrısı başarısız oldu") from error

        text = body.get("message", {}).get("content")
        if not isinstance(text, str) or not text.strip():
            raise OllamaProviderError("Ollama geçerli bir cevap döndürmedi")
        return LLMResponse(text=text, model=self.model)

    def health(self) -> bool:
        try:
            with urlopen(f"{self.base_url}/api/tags", timeout=3) as response:
                body = json.loads(response.read().decode("utf-8"))
            return any(item.get("name") == self.model for item in body.get("models", []))
        except (OSError, URLError, TimeoutError, json.JSONDecodeError):
            return False


@dataclass
class FakeLLMProvider(LLMProvider):
    responder: Callable[[LLMRequest], str] | None = None
    model: str = "fake"
    requests: list[LLMRequest] = field(default_factory=list)

    def health(self) -> bool:
        return True

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        text = self.responder(request) if self.responder else request.user_message
        return LLMResponse(text=text, model=self.model)
