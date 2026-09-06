"""Automation Trigger - Phase 5.6"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class TriggerType(str, Enum):
    SCHEDULE = "schedule"
    EVENT = "event"
    MANUAL = "manual"
    WEBHOOK = "webhook"


@dataclass
class Trigger:
    trigger_type: TriggerType = TriggerType.MANUAL
    cron_expression: str = ""
    event_name: str = ""
    webhook_url: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "trigger_type": self.trigger_type.value,
            "cron_expression": self.cron_expression,
            "event_name": self.event_name,
            "webhook_url": self.webhook_url,
            "metadata": self.metadata,
        }

    @classmethod
    def schedule(cls, cron: str) -> "Trigger":
        return cls(trigger_type=TriggerType.SCHEDULE, cron_expression=cron)

    @classmethod
    def on_event(cls, event_name: str) -> "Trigger":
        return cls(trigger_type=TriggerType.EVENT, event_name=event_name)

    @classmethod
    def manual(cls) -> "Trigger":
        return cls(trigger_type=TriggerType.MANUAL)


def parse_cron(cron: str) -> dict:
    """Parse a 5-field cron expression into components."""
    parts = cron.strip().split()
    if len(parts) != 5:
        return {"error": "Invalid cron: need 5 fields"}
    return {
        "minute": parts[0], "hour": parts[1],
        "day_of_month": parts[2], "month": parts[3],
        "day_of_week": parts[4],
    }


def cron_matches(cron: str, dt: datetime | None = None) -> bool:
    """Check if a cron expression matches the given datetime."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    parsed = parse_cron(cron)
    if "error" in parsed:
        return False

    def field_matches(pattern: str, value: int) -> bool:
        if pattern == "*":
            return True
        for part in pattern.split(","):
            if "-" in part:
                lo, hi = part.split("-")
                if int(lo) <= value <= int(hi):
                    return True
            elif "/" in part:
                base, step = part.split("/")
                step = int(step)
                if base == "*":
                    if value % step == 0:
                        return True
                else:
                    lo = int(base)
                    if value >= lo and (value - lo) % step == 0:
                        return True
            else:
                if int(part) == value:
                    return True
        return False

    return (
        field_matches(parsed["minute"], dt.minute)
        and field_matches(parsed["hour"], dt.hour)
        and field_matches(parsed["day_of_month"], dt.day)
        and field_matches(parsed["month"], dt.month)
        and field_matches(parsed["day_of_week"], dt.weekday())
    )
