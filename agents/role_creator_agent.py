"""Role creator agent for generating character assets."""

from typing import Dict, Any, List, TypedDict
from langchain_core.messages import HumanMessage, SystemMessage
from .base_agent import BaseAgent
from prompts.executor_prompts import EXECUTOR_SYSTEM_PROMPT, EXECUTOR_TASK_PROMPT
from utils import extract_and_validate_json, JSONExtractionError


class RoleCreatorAgent(BaseAgent):
    """Role creator agent that executes individual subtasks with context from previous subtasks"""
    
    def __init__(self):
        super().__init__("role_creator")
        
    def execute_subtask(self, subtask: Dict[str, Any], phase: Dict[str, Any], 
                       previous_results: List[Dict[str, Any]] = None, 
                       context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a specific subtask with context from previous subtasks"""
        task_id = subtask.get("task_id", "unknown")
        task_name = subtask.get("task_name", "unknown task")
        phase_id = phase.get("phase_id", "unknown")
        dependencies = subtask.get("task_dependencies", [])
        
        # Get info about completed dependencies
        dependencies_info = f"Dependencies {dependencies} have been completed" if dependencies else "No dependencies"
        
        # Format previous results for context
        previous_results_str = ""
        if previous_results:
            previous_results_str = "\n".join([
                f"- {result.get('description', 'No description')}: {result.get('assets_url', 'No URL')}"
                for result in previous_results[-3:]  # Only show last 3 results for context
            ])
        else:
            previous_results_str = "No previous results in this phase"
        
        messages = [
            SystemMessage(content=EXECUTOR_SYSTEM_PROMPT),
            HumanMessage(content=EXECUTOR_TASK_PROMPT.format(
                task_name=task_name,
                task_id=task_id,
                phase_id=phase_id,
                context=context or {},
                dependencies_info=dependencies_info,
                previous_results=previous_results_str
            ))
        ]
        
        response = self._call_llm(messages)
        
        try:
            # Extract and validate JSON using utils
            result = extract_and_validate_json(
                response, 
                expected_type=dict,
                required_fields=["description", "assets_url"]
            )
            
            # Add agent metadata
            result["agent"] = self.name
            result["task_id"] = task_id
            result["phase_id"] = phase_id
            result["status"] = "completed"
            return result
            
        except JSONExtractionError as e:
            raise ValueError(f"Failed to extract valid result from LLM response: {str(e)}")
    
    def _get_asset_extension(self, task_name: str) -> str:
        """Get appropriate file extension based on task name"""
        task_name_lower = task_name.lower()
        
        if any(word in task_name_lower for word in ["concept", "art", "sketch", "design"]):
            return ".png"
        elif any(word in task_name_lower for word in ["model", "3d", "mesh"]):
            return ".fbx"
        elif any(word in task_name_lower for word in ["texture", "material"]):
            return ".jpg"
        elif any(word in task_name_lower for word in ["animation", "rig"]):
            return ".anim"
        elif any(word in task_name_lower for word in ["sound", "audio", "voice"]):
            return ".wav"
        elif any(word in task_name_lower for word in ["script", "code"]):
            return ".cs"
        else:
            return ".asset"
    
    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute role creator logic and return updated state"""
        # This agent is typically called by the supervisor, so it doesn't need to modify state directly
        # The execute method is here for consistency with the BaseAgent interface
        return state
    
    # Keep the old method for backward compatibility
    def create_asset(self, task: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Legacy method - calls execute_subtask for backward compatibility"""
        # Convert old format to new format
        phase = {"phase_id": "LEGACY", "phase_name": "Legacy Phase"}
        return self.execute_subtask(task, phase, None, context)