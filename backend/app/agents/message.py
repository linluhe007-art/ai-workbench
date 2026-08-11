"""
AgentMessage — Agent 间通信消息定义。

支持三种通信方向：
- agent -> agent
- runtime -> agent
- agent -> runtime
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class AgentMessage:
    """
    Agent 间通信消息。

    字段：
    - id: 唯一消息 ID（自动生成）
    - sender: 发送方 ID
    - receiver: 接收方 ID
    - message_type: 消息类型 (data / request / response / error / broadcast)
    - content: 消息内容（dict）
    - created_at: 创建时间（自动生成 UTC）

    初始化时同时支持 message_type 和 msg_type（向后兼容别名）。
    """
    sender: str
    receiver: str
    content: dict = field(default_factory=dict)
    message_type: str = "data"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __init__(
        self,
        sender: str = "",
        receiver: str = "",
        content: dict | str | None = None,
        message_type: str | None = None,
        id: str | None = None,
        created_at: datetime | None = None,
        *,
        msg_type: str | None = None,
    ):
        self.sender = sender
        self.receiver = receiver
        self.content = content if content is not None else {}
        # message_type 优先；msg_type 为向后兼容别名
        self.message_type = message_type or msg_type or "data"
        self.id = id or str(uuid.uuid4())
        self.created_at = created_at or datetime.now(timezone.utc)

    @property
    def msg_type(self) -> str:
        """向后兼容属性别名"""
        return self.message_type

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sender": self.sender,
            "receiver": self.receiver,
            "message_type": self.message_type,
            "msg_type": self.message_type,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "timestamp": self.created_at.isoformat(),
        }