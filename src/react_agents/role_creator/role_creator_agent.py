"""Role creator agent for generating character assets."""

from src.models import SupervisorSubGraphState
from src.prompts.role_creator_prompts import ROLE_CREATOR_SYSTEM_PROMPT
from src.react_agents.base_react_agent import BaseReactAgent
from src.react_agents.role_creator.tools import ROLE_CREATOR_TOOLS


class RoleCreatorAgent(BaseReactAgent):
    """Role creator agent that executes individual subtasks with context from previous subtasks"""

    def __init__(self):
        super().__init__(
            "role_creator",
            ROLE_CREATOR_SYSTEM_PROMPT,
            ROLE_CREATOR_TOOLS,
        )

    def _get_state_schema(self):
        return SupervisorSubGraphState
