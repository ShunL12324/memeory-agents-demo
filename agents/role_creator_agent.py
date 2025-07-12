"""Role creator agent for generating character assets."""

from typing import Dict, Any, List, TypedDict
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from .base_agent import BaseAgent
from prompts.executor_prompts import EXECUTOR_SYSTEM_PROMPT, EXECUTOR_TASK_PROMPT
from utils import extract_and_validate_json, JSONExtractionError
from datetime import datetime


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
        status = state.get("status", "")
        
        try:
            if status == "ready_for_phase_processing":
                # Process current phase
                phases = state.get("phases", [])
                current_phase_index = state.get("current_phase_index", 0)
                
                if current_phase_index >= len(phases):
                    # All phases completed
                    return {
                        "origin_user_request": state.get("origin_user_request", ""),
                        "planning_results": state.get("planning_results", ""),
                        "status": "workflow_completed",
                        "phases": phases,
                        "current_phase_index": current_phase_index,
                        "messages": [AIMessage(content="All phases completed successfully!")]
                    }
                
                current_phase = phases[current_phase_index]
                phase_name = current_phase.get("phase_name", f"Phase {current_phase_index + 1}")
                
                # Break down phase into subtasks
                subtasks = self._break_down_phase(current_phase, state.get("origin_user_request", ""))
                
                # Execute all subtasks in this phase
                phase_results = []
                for i, subtask in enumerate(subtasks):
                    try:
                        result = self.execute_subtask(subtask, current_phase, phase_results, {
                            "character_request": state.get("origin_user_request", ""),
                            "phase_number": current_phase_index + 1,
                            "subtask_number": i + 1,
                            "total_subtasks": len(subtasks)
                        })
                        phase_results.append(result)
                    except Exception as e:
                        # Continue with next subtask even if one fails
                        error_result = {
                            "task_id": subtask.get("task_id", f"task_{i+1}"),
                            "phase_id": current_phase.get("phase_id", ""),
                            "agent": self.name,
                            "description": f"Error executing subtask: {str(e)}",
                            "assets_url": "",
                            "status": "error"
                        }
                        phase_results.append(error_result)
                
                # Create phase completion message
                phase_message = AIMessage(
                    content=f"Completed phase '{phase_name}' with {len(phase_results)} subtasks",
                    additional_kwargs={
                        "agent": "role_creator",
                        "role": "phase_execution",
                        "phase_id": current_phase.get("phase_id", ""),
                        "phase_name": phase_name,
                        "subtasks_completed": len(phase_results),
                        "phase_results": phase_results,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
                return {
                    "origin_user_request": state.get("origin_user_request", ""),
                    "planning_results": state.get("planning_results", ""),
                    "status": "phase_completed",
                    "phases": phases,
                    "current_phase_index": current_phase_index,
                    "messages": [phase_message]
                }
                
            else:
                # Unknown status, return error
                error_message = AIMessage(
                    content=f"Unknown role creator status: {status}",
                    additional_kwargs={
                        "agent": "role_creator",
                        "role": "error",
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
                return {
                    "origin_user_request": state.get("origin_user_request", ""),
                    "planning_results": state.get("planning_results", ""),
                    "status": "error",
                    "phases": state.get("phases", []),
                    "current_phase_index": state.get("current_phase_index", 0),
                    "messages": [error_message]
                }
                
        except Exception as e:
            error_message = AIMessage(
                content=f"Role creator execution failed: {str(e)}",
                additional_kwargs={
                    "agent": "role_creator",
                    "role": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            return {
                "origin_user_request": state.get("origin_user_request", ""),
                "planning_results": state.get("planning_results", ""),
                "status": "error",
                "phases": state.get("phases", []),
                "current_phase_index": state.get("current_phase_index", 0),
                "messages": [error_message]
            }
    
    def _break_down_phase(self, phase: Dict[str, Any], character_request: str) -> List[Dict[str, Any]]:
        """Break down a phase into subtasks"""
        phase_name = phase.get("phase_name", "")
        phase_description = phase.get("phase_description", "")
        estimated_subtasks = phase.get("estimated_subtasks", 3)
        
        # Simple task breakdown based on phase name
        if "concept" in phase_name.lower():
            subtasks = [
                {
                    "task_id": f"{phase.get('phase_id', 'phase')}_001",
                    "task_name": f"Create concept art for {character_request}",
                    "phase_id": phase.get("phase_id", ""),
                    "task_dependencies": [],
                    "generated_assets_info": {"s3_url": "", "description": ""}
                }
            ]
        elif "3d" in phase_name.lower() or "model" in phase_name.lower():
            subtasks = [
                {
                    "task_id": f"{phase.get('phase_id', 'phase')}_002",
                    "task_name": f"Create 3D model for {character_request}",
                    "phase_id": phase.get("phase_id", ""),
                    "task_dependencies": [],
                    "generated_assets_info": {"s3_url": "", "description": ""}
                }
            ]
        elif "texture" in phase_name.lower():
            subtasks = [
                {
                    "task_id": f"{phase.get('phase_id', 'phase')}_003",
                    "task_name": f"Create textures for {character_request}",
                    "phase_id": phase.get("phase_id", ""),
                    "task_dependencies": [],
                    "generated_assets_info": {"s3_url": "", "description": ""}
                }
            ]
        elif "animation" in phase_name.lower() or "rig" in phase_name.lower():
            subtasks = [
                {
                    "task_id": f"{phase.get('phase_id', 'phase')}_004",
                    "task_name": f"Create rigging and animations for {character_request}",
                    "phase_id": phase.get("phase_id", ""),
                    "task_dependencies": [],
                    "generated_assets_info": {"s3_url": "", "description": ""}
                }
            ]
        elif "story" in phase_name.lower() or "lore" in phase_name.lower():
            subtasks = [
                {
                    "task_id": f"{phase.get('phase_id', 'phase')}_005",
                    "task_name": f"Create backstory and lore for {character_request}",
                    "phase_id": phase.get("phase_id", ""),
                    "task_dependencies": [],
                    "generated_assets_info": {"s3_url": "", "description": ""}
                }
            ]
        else:
            # Generic subtask
            subtasks = [
                {
                    "task_id": f"{phase.get('phase_id', 'phase')}_generic",
                    "task_name": f"Process phase: {phase_name}",
                    "phase_id": phase.get("phase_id", ""),
                    "task_dependencies": [],
                    "generated_assets_info": {"s3_url": "", "description": ""}
                }
            ]
        
        return subtasks
    
    # Keep the old method for backward compatibility
    def create_asset(self, task: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Legacy method - calls execute_subtask for backward compatibility"""
        # Convert old format to new format
        phase = {"phase_id": "LEGACY", "phase_name": "Legacy Phase"}
        return self.execute_subtask(task, phase, None, context)