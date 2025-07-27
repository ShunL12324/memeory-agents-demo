"""Supervisor agent for coordinating and monitoring other agents."""

from src.models import SupervisorSubGraphState
from src.prompts.supervisor_prompts import SUPERVISOR_SYSTEM_PROMPT
from src.react_agents.base_react_agent import BaseReactAgent

from .tools import SUPERVISOR_TOOLS


class SupervisorAgent(BaseReactAgent):
    """Supervisor agent that coordinates workflow execution"""

    def __init__(self):
        super().__init__(
            "supervisor", prompt=SUPERVISOR_SYSTEM_PROMPT, tools=SUPERVISOR_TOOLS
        )

    def _get_state_schema(self):
        return SupervisorSubGraphState
