"""Personal Agent Roles - Phase 5.5"""
from dataclasses import dataclass, field
from enum import Enum

class AgentRole(str, Enum):
    RESEARCH = "research"
    CODING = "coding"
    WRITER = "writer"
    ANALYST = "analyst"

@dataclass
class RoleConfig:
    role: AgentRole = AgentRole.RESEARCH
    name: str = ""
    description: str = ""
    capabilities: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    base_score: float = 50.0
    metadata: dict = field(default_factory=dict)

PREDEFINED_ROLES = {
    AgentRole.RESEARCH: RoleConfig(role=AgentRole.RESEARCH, name="Research Agent", description="Gathers information and performs deep research", capabilities=["research","search","knowledge"], tools=["memory_search","web_search"], base_score=60.0),
    AgentRole.CODING: RoleConfig(role=AgentRole.CODING, name="Coding Agent", description="Writes, refactors, and debugs code", capabilities=["coding","code","debug","refactor"], tools=["code_executor","file_viewer"], base_score=55.0),
    AgentRole.WRITER: RoleConfig(role=AgentRole.WRITER, name="Writer Agent", description="Creates content, reports, articles", capabilities=["writing","content","document"], tools=["artifact_extractor"], base_score=50.0),
    AgentRole.ANALYST: RoleConfig(role=AgentRole.ANALYST, name="Analyst Agent", description="Analyzes data and provides recommendations", capabilities=["analysis","evaluation","comparison"], tools=["memory_search","evaluator"], base_score=55.0),
}

def get_role_config(role_name: str):
    for role in AgentRole:
        if role.value == role_name:
            return PREDEFINED_ROLES.get(role)
    return None

def get_all_roles():
    return list(PREDEFINED_ROLES.values())
