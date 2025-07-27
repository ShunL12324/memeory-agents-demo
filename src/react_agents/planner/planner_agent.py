"""Planner agent for creating character creation plans."""

from src.models import MainGraphState
from src.prompts.planner_prompts import PLANNER_SYSTEM_PROMPT
from src.react_agents.base_react_agent import BaseReactAgent
from src.react_agents.planner.tools import PLANNER_TOOLS


class PlannerAgent(BaseReactAgent):
    """Planning agent that creates high-level phases for character creation"""

    def __init__(self):
        super().__init__("planner", PLANNER_SYSTEM_PROMPT, PLANNER_TOOLS)

    def _get_state_schema(self):
        return MainGraphState
