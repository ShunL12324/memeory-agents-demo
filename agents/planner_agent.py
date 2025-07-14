"""Planner agent for creating character creation plans."""

from typing import Dict, Any, List, TypedDict
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

import logger
from .base_agent import BaseAgent
from prompts.planner_prompts import PLANNER_SYSTEM_PROMPT, PLANNER_USER_PROMPT
from utils import extract_and_validate_json, JSONExtractionError
from models import MainWorkflowStatus, MainWorkflowState


class PlannerAgent(BaseAgent):
    """Planning agent that creates high-level phases for character creation"""

    def __init__(self):
        super().__init__("planner")

    def execute(self, state: MainWorkflowState) -> MainWorkflowState:
        """Execute planning logic and return updated state"""

        logger.get_logger()._write_log(
            "INFO",
            "planner_agent",
            f"开始制定计划: {state['origin_user_request']}",
        )

        messages = [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(
                content=PLANNER_USER_PROMPT.format(
                    origin_user_request=state["origin_user_request"]
                )
            ),
        ]

        response = self._call_llm(messages)

        try:
            phases = extract_and_validate_json(
                self._extract_text_content(response),
                expected_type=list,
                required_fields=["phase_id", "phase_name", "phase_description"],
            )

            logger.get_logger()._write_log(
                "INFO",
                "planner_agent",
                f"制定了 {len(phases)} 个阶段的计划",
            )

            # Return updated state matching AgentState structure
            return {
                "origin_user_request": state["origin_user_request"],
                "plan_list": phases,
                "current_plan_index": 0,
                "status": MainWorkflowStatus.PLANNING_COMPLETED,
                "messages": [response],
            }

        except Exception as e:
            logger.get_logger()._write_log(
                "ERROR", "planner_agent", f"计划制定失败: {str(e)}"
            )
            return {
                "origin_user_request": state["origin_user_request"],
                "plan_list": [],
                "current_plan_index": 0,
                "status": MainWorkflowStatus.ERROR,
                "messages": [response],
            }
