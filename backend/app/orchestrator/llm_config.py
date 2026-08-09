"""
LLM 配置加载
从 config/llm.yaml 读取 Provider 配置。
支持运行时切换 Provider。
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from app.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "llm.yaml"


@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: str = "mock"
    model: str = "mock-llm-v1"
    temperature: float = 0.7
    max_tokens: int = 4096
    api_base: str = ""
    api_key: str = ""
    extra: dict = field(default_factory=dict)


def load_llm_config(config_path: str | Path | None = None) -> LLMConfig:
    """
    加载 LLM 配置
    优先级：环境变量 > yaml 配置文件 > 默认值
    """
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    raw: dict = {}

    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
                raw = data.get("llm", {})
            logger.info("LLM config loaded", path=str(path), provider=raw.get("provider", "mock"))
        except Exception as e:  # noqa: BLE001 — config failure falls back to default
            logger.warning("Failed to load LLM config", error=str(e))

    # 从环境变量读取 API key
    api_key_env = raw.get("api_key_env", "")
    api_key = os.environ.get(api_key_env, "") if api_key_env else ""

    # 环境变量覆盖
    provider = os.environ.get("LLM_PROVIDER", raw.get("provider", "mock"))
    model = os.environ.get("LLM_MODEL", raw.get("model", "mock-llm-v1"))

    return LLMConfig(
        provider=provider,
        model=model,
        temperature=float(raw.get("temperature", 0.7)),
        max_tokens=int(raw.get("max_tokens", 4096)),
        api_base=raw.get("api_base", ""),
        api_key=api_key,
        extra=raw.get("extra", {}),
    )


def create_llm_provider(config: LLMConfig | None = None):
    """
    根据配置创建 LLM Provider 实例
    当前只有 Mock，Phase 3 接入真实 Provider。
    """
    if config is None:
        config = load_llm_config()

    if config.provider == "mock":
        from app.orchestrator.llm_provider import MockLLMProvider
        return MockLLMProvider(default_model=config.model)
    else:
        logger.warning("Unknown LLM provider, falling back to mock", provider=config.provider)
        from app.orchestrator.llm_provider import MockLLMProvider
        return MockLLMProvider(default_model="mock-llm-v1")