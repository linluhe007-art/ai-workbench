


from typing import Any

from openai import AsyncOpenAI

from app.orchestrator.llm_provider import (
    LLMMessage,
    LLMProvider,
    LLMResponse,
    LLMRole,
    LLMTool,
)


class DeepSeekProvider(LLMProvider):
    """
    DeepSeek LLM Provider
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        default_model: str = "deepseek-chat",
    ):
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )

        self.default_model = default_model

    async def chat(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[LLMTool] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:

        response = await self.client.chat.completions.create(
            model=model or self.default_model,
            messages=[
                {
                    "role": msg.role.value,
                    "content": msg.content,
                }
                for msg in messages
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            tools=[
                tool.to_dict()
                for tool in tools
            ] if tools else None,
        )

        choice = response.choices[0]

        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            tokens_used=response.usage.total_tokens
            if response.usage
            else 0,
            finish_reason=choice.finish_reason,
            metadata={
                "provider": "deepseek",
            },
        )

    def get_model_name(self) -> str:
        return self.default_model

    def is_available(self) -> bool:
        return True

