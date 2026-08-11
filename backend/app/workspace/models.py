"""
WorkspaceItem — 共享工作空间数据模型。

每个 WorkspaceItem 代表一个 Agent 在任务执行过程中产生的中间产物。
例如：研究结果、分析报告、草稿文本、图片方案等。
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class WorkspaceItem:
    """
    工作空间条目。

    字段：
    - id: 唯一标识（自动生成 UUID）
    - name: 条目名称
    - type: 条目类型（text / dict / list / image_url / file_path ...）
    - content: 条目内容（任意类型）
    - owner: 创建者 Agent ID
    - metadata: 附加元数据
    - created_at: 创建时间（自动生成 UTC）
    """
    name: str
    type: str
    content: Any
    owner: str
    metadata: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "content": self.content,
            "owner": self.owner,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }