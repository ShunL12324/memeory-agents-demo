"""Planner agent for creating character creation plans."""

from typing import Dict, Any, List, TypedDict
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from .base_agent import BaseAgent
from prompts.planner_prompts import PLANNER_SYSTEM_PROMPT, PLANNER_USER_PROMPT
from utils import extract_and_validate_json, JSONExtractionError
from simple_file_tools import format_ai_history_context_from_messages
import json
from datetime import datetime


class PlannerAgent(BaseAgent):
    """Planning agent that creates high-level phases for character creation"""
    
    def __init__(self):
        super().__init__("planner")
        
    def create_phases(self, task: str, context: str = "") -> Dict[str, Any]:
        """Create high-level phases for the given character creation task"""
        messages = [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=PLANNER_USER_PROMPT.format(task=task, context=context))
        ]
        
        response = self._call_llm(messages)
        
        try:
            # Extract and validate JSON using utils
            phases = extract_and_validate_json(
                response, 
                expected_type=list,
                required_fields=["phase_id", "phase_name", "phase_description"]
            )
            
            # Wrap in plan structure
            plan = {
                "task": task,
                "phases": phases,
                "agent": self.name,
                "status": "planned"
            }
            return plan
            
        except JSONExtractionError as e:
            raise ValueError(f"Failed to extract valid phases from LLM response: {str(e)}")
    
    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute planning logic and return updated state"""
        ai_history_context = format_ai_history_context_from_messages(state.get("messages", []))
        
        messages = [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT.format(ai_history_context=ai_history_context)),
            HumanMessage(content=PLANNER_USER_PROMPT.format(
                task=state["character_request"], 
                context=json.dumps(state.get("workflow_data", {}))
            ))
        ]
        
        response = self._call_llm(messages)
        
        phases = extract_and_validate_json(
            response, 
            expected_type=list,
            required_fields=["phase_id", "phase_name", "phase_description"]
        )
        
        plan_message = AIMessage(
            content=response,
            additional_kwargs={
                "agent": "planner",
                "role": "planning",
                "structured_data": phases,
                "timestamp": datetime.now().isoformat()
            }
        )
        state["messages"] = [plan_message]
        
        state["workflow_data"]["phases"] = phases
        state["workflow_data"]["current_phase_index"] = 0
        state["workflow_data"]["status"] = "planned"
        
        state["messages"] = [HumanMessage(content=f"Plan created with {len(phases)} phases")]
        
        return state
    
    # Legacy method for backward compatibility
    def create_plan(self, task: str, context: str = "") -> Dict[str, Any]:
        """Legacy method - calls create_phases for backward compatibility"""
        return self.create_phases(task, context)