"""Role creator agent for generating character assets."""

from typing import Dict, Any, List, TypedDict
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

import logger
from .base_agent import BaseAgent
from prompts.role_creator_prompts import ROLE_CREATOR_SYSTEM_PROMPT
from utils import extract_and_validate_json, JSONExtractionError
from datetime import datetime
from models import SupervisorWorkflowState, SupervisorWorkflowStatus
from tools import file_tools


class RoleCreatorAgent(BaseAgent):
    """Role creator agent that executes individual subtasks with context from previous subtasks"""

    def __init__(self):
        super().__init__("role_creator")

    def execute(self, state: SupervisorWorkflowState) -> SupervisorWorkflowState:
        logger.get_logger()._write_log(
            "INFO", "role_creator", "Start role creator work"
        )

        history_messages = state.get("messages", [])
        if len(history_messages) == 0:
            return SupervisorWorkflowState(status=SupervisorWorkflowStatus.ERROR)

        context = "\n".join([m.pretty_repr() for m in history_messages])
        system_msg = SystemMessage(
            content=ROLE_CREATOR_SYSTEM_PROMPT.format(context=context)
        )

        messages = [system_msg] + [HumanMessage(content="Start process")]

        response = self._call_llm(messages)

        logger.get_logger()._write_log(
            "INFO",
            "role_creator",
            "[THINKING]\n" + self._extract_reasoning_content(response),
        )
        logger.get_logger()._write_log(
            "INFO", "role_creator", "[CONTENT]\n" + self._extract_text_content(response)
        )

        return SupervisorWorkflowState(
            status=SupervisorWorkflowStatus.TASK_COMPLETED, messages=[response]
        )
