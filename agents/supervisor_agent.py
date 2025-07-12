"""Supervisor agent for coordinating and monitoring other agents."""

from typing import Dict, Any

import logger
from tools import file_tools
from models import SubWorkflowStatus
from .base_agent import BaseAgent
from prompts.supervisor_prompts import SUPERVISOR_SYSTEM_PROMPT
from models import SupervisorSubGraphState
from datetime import datetime
from langchain_core.messages import AIMessage, ToolMessage


class SupervisorAgent(BaseAgent):
    """Supervisor agent that coordinates workflow execution"""

    def __init__(self):
        super().__init__("supervisor", tools=file_tools)
        self.agents = {}

    def register_agent(self, agent):
        """Register an agent with the supervisor"""
        self.agents[agent.name] = agent

    def execute(self, state: SupervisorSubGraphState) -> SupervisorSubGraphState:
        """Execute supervision logic and return updated state"""
        logger.get_logger()._write_log("INFO", "supervisor_agent", f"Execute the supervisor agent")
        history_messages = state.get("messages", [])
        logger.get_logger()._write_log("INFO", "supervisor_agent", f"History messages: {history_messages[1:]}")
        supervisor_system = AIMessage(
            content=SUPERVISOR_SYSTEM_PROMPT.format(messages_context=history_messages),
            role="supervisor",
            agent="supervisor",
            timestamp=datetime.now().isoformat()
        )
        messages = [supervisor_system] + [history_messages[0]]

        logger.get_logger()._write_log("INFO", "supervisor_agent", f"Messages: {messages}")

        response = self._call_llm(messages)

        logger.get_logger()._write_log("INFO", "supervisor_agent", f"Response: {response}")

        if response.tool_calls and len(response.tool_calls) > 0 :
            return SupervisorSubGraphState(
                status=SubWorkflowStatus.TOOL_CALLING,
                messages=[response]
            )
        else:
            return SupervisorSubGraphState(
                status=SubWorkflowStatus.TASK_PROCESSING,
                messages=[response]
            )

