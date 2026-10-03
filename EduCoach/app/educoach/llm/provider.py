from collections.abc import Callable
from dataclasses import dataclass, field


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
    def generate(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError


@dataclass
class FakeLLMProvider(LLMProvider):
    responder: Callable[[LLMRequest], str] | None = None
    model: str = "fake"
    requests: list[LLMRequest] = field(default_factory=list)

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        text = self.responder(request) if self.responder else request.user_message
        return LLMResponse(text=text, model=self.model)
