"""LLM API endpoints (Phase Beta-LLM)."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.llm.errors import LLMError
from app.llm.events import publish_llm_event
from app.llm.factory import get_llm_config_info, get_llm_provider
from app.utils.errors import AppError, ErrorCode
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/llm", tags=["llm"])


class LLMTestRequest(BaseModel):
    prompt: str = Field(default="请回复：连接成功", min_length=1)
    model: str | None = None
    temperature: float = 0.2
    max_tokens: int = 4000


@router.get("/config")
async def llm_config():
    """Return non-sensitive LLM configuration and provider availability."""
    return {
        "success": True,
        **get_llm_config_info(),
    }


@router.post("/test")
async def llm_test(req: LLMTestRequest):
    """Test the configured LLM provider with a single prompt."""
    publish_llm_event("llm_test_started", {"model": req.model or "default"})
    provider = get_llm_provider()
    try:
        response = await provider.generate(
            [{"role": "user", "content": req.prompt}],
            model=req.model,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )
    except LLMError:
        publish_llm_event("llm_test_failed", {"provider": provider.get_model_name()})
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected LLM test error")
        publish_llm_event("llm_test_failed", {"provider": provider.get_model_name()})
        raise AppError(
            message="Internal LLM test error",
            error_code=ErrorCode.INTERNAL_ERROR,
            status_code=500,
        ) from exc

    publish_llm_event("llm_test_completed", {
        "model": response.model,
        "latency_ms": response.latency_ms,
    })
    return {
        "success": True,
        "content": response.content,
        "model": response.model,
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "latency_ms": response.latency_ms,
        "finish_reason": response.finish_reason,
    }
