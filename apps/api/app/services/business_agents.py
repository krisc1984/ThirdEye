from __future__ import annotations

from app.schemas.business_agent import BusinessAgentConfig
from app.services.storage import JsonStorage

SETTINGS_NAMESPACE = "settings"
SETTINGS_RECORD_ID = "business-agents"


class BusinessAgentService:
    def __init__(self, storage: JsonStorage) -> None:
        self.storage = storage

    def list_agents(self) -> list[BusinessAgentConfig]:
        payload = self._load_or_create_settings()
        return [BusinessAgentConfig.model_validate(item) for item in payload["agents"]]

    def get_agent(self, agent_id: str) -> BusinessAgentConfig:
        for agent in self.list_agents():
            if agent.id == agent_id:
                return agent
        raise FileNotFoundError(agent_id)

    def save_agent(self, agent: BusinessAgentConfig) -> BusinessAgentConfig:
        current = self.list_agents()
        found = False
        next_agents: list[BusinessAgentConfig] = []
        for item in current:
            if item.id == agent.id:
                next_agents.append(agent)
                found = True
            else:
                next_agents.append(item)
        if not found:
            next_agents.insert(0, agent)
        self._save_agents(next_agents)
        return self.get_agent(agent.id)

    def activate_agent(self, agent_id: str) -> BusinessAgentConfig:
        current = self.list_agents()
        next_agents: list[BusinessAgentConfig] = []
        activated: BusinessAgentConfig | None = None
        for item in current:
            is_target = item.id == agent_id
            updated = item.model_copy(
                update={
                    "status": "active" if is_target else "draft",
                    "is_default": is_target,
                }
            )
            if is_target:
                activated = updated
            next_agents.append(updated)
        if activated is None:
            raise FileNotFoundError(agent_id)
        self._save_agents(next_agents)
        return activated

    def _load_or_create_settings(self) -> dict[str, list[dict[str, object]]]:
        try:
            payload = self.storage.load_json(SETTINGS_NAMESPACE, SETTINGS_RECORD_ID)
        except FileNotFoundError:
            payload = {"agents": [item.model_dump(mode="json") for item in self._default_agents()]}
            self.storage.save_json(SETTINGS_NAMESPACE, SETTINGS_RECORD_ID, payload)
        agents = payload.get("agents")
        if not isinstance(agents, list) or not agents:
            payload = {"agents": [item.model_dump(mode="json") for item in self._default_agents()]}
            self.storage.save_json(SETTINGS_NAMESPACE, SETTINGS_RECORD_ID, payload)
        return payload

    def _save_agents(self, agents: list[BusinessAgentConfig]) -> None:
        normalized = self._normalize_active_state(agents)
        payload = {"agents": [item.model_dump(mode="json") for item in normalized]}
        self.storage.save_json(SETTINGS_NAMESPACE, SETTINGS_RECORD_ID, payload)

    def _normalize_active_state(self, agents: list[BusinessAgentConfig]) -> list[BusinessAgentConfig]:
        if not agents:
            return self._default_agents()

        active_index = next((index for index, item in enumerate(agents) if item.is_default or item.status == "active"), 0)
        normalized: list[BusinessAgentConfig] = []
        for index, item in enumerate(agents):
            is_active = index == active_index
            normalized.append(
                item.model_copy(
                    update={
                        "status": "active" if is_active else "draft",
                        "is_default": is_active,
                    }
                )
            )
        return normalized

    def _default_agents(self) -> list[BusinessAgentConfig]:
        return [
            BusinessAgentConfig(
                id="code-review-agent",
                name="代码评审 Agent",
                description="面向代码改动、风险、回归与测试缺口的通用评审智能体。",
                category="engineering",
                system_prompt=(
                    "你是专业的代码评审智能体。优先识别高风险缺陷、行为回归、边界条件遗漏、测试缺口与设计偏差。"
                    "输出保持结构化、直接，并给出可执行的修正建议。"
                ),
                status="active",
                is_default=True,
            ),
            BusinessAgentConfig(
                id="requirement-review-agent",
                name="需求评审 Agent",
                description="面向需求说明、范围边界、验收条件与实现风险的评审智能体。",
                category="product",
                system_prompt=(
                    "你是专业的需求评审智能体。重点检查需求目标是否清晰、边界是否收敛、验收标准是否可测试、"
                    "以及潜在实现风险、依赖与歧义。"
                ),
            ),
            BusinessAgentConfig(
                id="test-review-agent",
                name="测试评审 Agent",
                description="面向测试方案、覆盖范围、质量门槛与验证路径的评审智能体。",
                category="quality",
                system_prompt=(
                    "你是专业的测试评审智能体。重点评估测试覆盖是否完整、关键路径是否覆盖、是否缺少失败场景、"
                    "回归风险和自动化建议。"
                ),
            ),
        ]

