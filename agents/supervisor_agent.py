"""Supervisor agent for coordinating and monitoring other agents."""

from typing import Dict, Any, List, TypedDict
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
import json
from datetime import datetime
from .base_agent import BaseAgent
from prompts.supervisor_prompts import SUPERVISOR_SYSTEM_PROMPT, SUPERVISOR_PHASE_BREAKDOWN_PROMPT, SUPERVISOR_PROGRESS_PROMPT
from utils import extract_and_validate_json, JSONExtractionError
from simple_file_tools import format_ai_history_context_from_messages


class SupervisorAgent(BaseAgent):
    """Supervisor agent that breaks down phases into subtasks and coordinates execution"""
    
    def __init__(self):
        # Initialize without LangChain tools (using simple file tools instead)
        super().__init__("supervisor")
        self.active_plans = {}
        self.agents = {}
        self.todo_file = "todo.json"
        self.current_phase_index = 0
        self.current_subtask_index = 0
        self.execution_history = []
        
    def register_agent(self, agent):
        """Register an agent with the supervisor"""
        self.agents[agent.name] = agent
        
    def break_down_phase(self, phase: Dict[str, Any], character_request: str, ai_history_context: str = "") -> List[Dict[str, Any]]:
        """Break down a high-level phase into detailed subtasks"""
        if not ai_history_context:
            ai_history_context = "No previous AI interactions in this session."
            
        messages = [
            SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT.format(ai_history_context=ai_history_context)),
            HumanMessage(content=SUPERVISOR_PHASE_BREAKDOWN_PROMPT.format(
                phase_id=phase.get("phase_id", ""),
                phase_name=phase.get("phase_name", ""),
                phase_description=phase.get("phase_description", ""),
                estimated_subtasks=phase.get("estimated_subtasks", 3),
                character_request=character_request
            ))
        ]
        
        response = self._call_llm(messages)
        
        try:
            # Extract and validate JSON using utils
            subtasks = extract_and_validate_json(
                response, 
                expected_type=list,
                required_fields=["task_id", "task_name", "phase_id"]
            )
            
            return subtasks
            
        except JSONExtractionError as e:
            raise ValueError(f"Failed to extract valid subtasks from LLM response: {str(e)}")
    
    def start_hierarchical_execution(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Start the hierarchical execution of phases and subtasks"""
        plan_id = f"plan_{len(self.active_plans) + 1}"
        
        # Reset execution state
        self.current_phase_index = 0
        self.current_subtask_index = 0
        self.execution_history = []
        
        # Create execution plan
        execution_plan = {
            **plan,
            "plan_id": plan_id,
            "phases": plan.get("phases", []),
            "current_phase_index": 0,
            "current_subtask_index": 0,
            "current_subtasks": [],
            "status": "in_progress",
            "execution_history": []
        }
        
        self.active_plans[plan_id] = execution_plan
        return execution_plan
    
    def get_next_action(self, plan_id: str) -> Dict[str, Any]:
        """Get the next action in the hierarchical execution"""
        if plan_id not in self.active_plans:
            return {"action": "error", "message": "Plan not found"}
        
        plan = self.active_plans[plan_id]
        phases = plan.get("phases", [])
        
        # Check if all phases are completed
        if plan["current_phase_index"] >= len(phases):
            plan["status"] = "completed"
            return {"action": "complete", "message": "All phases completed"}
        
        current_phase = phases[plan["current_phase_index"]]
        current_subtasks = plan.get("current_subtasks", [])
        
        # If no subtasks for current phase, break down the phase
        if not current_subtasks:
            character_request = plan.get("task", "")
            subtasks = self.break_down_phase(current_phase, character_request, "No previous AI interactions available in this context.")
            plan["current_subtasks"] = subtasks
            plan["current_subtask_index"] = 0
            
            # Update todo file with new subtasks
            self.manage_todo_file(subtasks)
            
            return {
                "action": "phase_broken_down",
                "phase": current_phase,
                "subtasks": subtasks,
                "message": f"Phase {current_phase.get('phase_name', '')} broken down into {len(subtasks)} subtasks"
            }
        
        # Check if current phase is completed
        if plan["current_subtask_index"] >= len(current_subtasks):
            # Move to next phase
            plan["current_phase_index"] += 1
            plan["current_subtasks"] = []
            plan["current_subtask_index"] = 0
            
            # Check if all phases are completed
            if plan["current_phase_index"] >= len(phases):
                plan["status"] = "completed"
                return {"action": "complete", "message": "All phases completed"}
            else:
                return {"action": "phase_completed", "message": f"Phase {current_phase.get('phase_name', '')} completed, moving to next phase"}
        
        # Get next subtask to execute
        next_subtask = current_subtasks[plan["current_subtask_index"]]
        
        return {
            "action": "execute_subtask",
            "subtask": next_subtask,
            "phase": current_phase,
            "subtask_number": plan["current_subtask_index"] + 1,
            "total_subtasks": len(current_subtasks),
            "phase_number": plan["current_phase_index"] + 1,
            "total_phases": len(phases)
        }
    
    def record_subtask_completion(self, plan_id: str, subtask_result: Dict[str, Any]) -> Dict[str, Any]:
        """Record the completion of a subtask and update progress"""
        if plan_id not in self.active_plans:
            return {"error": "Plan not found"}
        
        plan = self.active_plans[plan_id]
        
        # Record the execution result
        plan["execution_history"].append({
            "phase_index": plan["current_phase_index"],
            "subtask_index": plan["current_subtask_index"],
            "subtask_result": subtask_result,
            "timestamp": datetime.now().isoformat()
        })
        
        # Update subtask status in current_subtasks
        current_subtasks = plan.get("current_subtasks", [])
        if plan["current_subtask_index"] < len(current_subtasks):
            current_subtask = current_subtasks[plan["current_subtask_index"]]
            current_subtask["status"] = "completed"
            current_subtask["generated_assets_info"] = {
                "s3_url": subtask_result.get("assets_url", ""),
                "description": subtask_result.get("description", "")
            }
            
            # Update todo file
            self.update_task_in_todo(current_subtask.get("task_id", ""), subtask_result)
        
        # Move to next subtask
        plan["current_subtask_index"] += 1
        
        return {"status": "recorded", "message": "Subtask completion recorded"}
    
    def evaluate_progress(self, plan_id: str, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate the progress and decide the next action"""
        if plan_id not in self.active_plans:
            return {"action": "error", "message": "Plan not found"}
        
        plan = self.active_plans[plan_id]
        phases = plan.get("phases", [])
        current_phase = phases[plan["current_phase_index"]] if plan["current_phase_index"] < len(phases) else None
        current_subtasks = plan.get("current_subtasks", [])
        
        if not current_phase:
            return {"action": "complete", "message": "All phases completed"}
        
        current_subtask_desc = ""
        if plan["current_subtask_index"] < len(current_subtasks):
            current_subtask = current_subtasks[plan["current_subtask_index"]]
            current_subtask_desc = current_subtask.get("task_name", "")
        
        messages = [
            SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
            HumanMessage(content=SUPERVISOR_PROGRESS_PROMPT.format(
                current_phase=current_phase.get("phase_name", ""),
                current_subtask=plan["current_subtask_index"] + 1,
                total_subtasks=len(current_subtasks),
                subtask_description=current_subtask_desc,
                execution_result=str(execution_result)
            ))
        ]
        
        response = self._call_llm(messages)
        
        # For now, return a simple evaluation
        return {
            "evaluation": response,
            "recommendation": "continue" if "continue" in response.lower() else "review"
        }
    
    def assign_task(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Assign a plan to appropriate agents for execution"""
        plan_id = f"plan_{len(self.active_plans) + 1}"
        
        # For the new hierarchical workflow, we start the hierarchical execution
        return self.start_hierarchical_execution(plan)
        
    def monitor_progress(self, plan_id: str, step_result: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy method - use record_subtask_completion for new hierarchical workflow"""
        return self.record_subtask_completion(plan_id, step_result)
    
    def manage_todo_file(self, tasks: list) -> str:
        """Create or update todo.json file with tasks"""
        from simple_file_tools import simple_read_file, simple_write_file
        
        # Check if todo.json exists
        file_content = simple_read_file(self.todo_file)
        
        if "Error: File not found" in file_content:
            # Create new todo.json file
            todo_data = {
                "project_name": "Game Character Creation",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "tasks": tasks
            }
            
            json_content = json.dumps(todo_data, indent=2, ensure_ascii=False)
            result = simple_write_file(self.todo_file, json_content)
            return f"Created todo.json with {len(tasks)} tasks. {result}"
        else:
            # File exists, update with new tasks
            try:
                # Extract content
                if "Content:\n" in file_content:
                    current_content = file_content.split("Content:\n", 1)[1]
                else:
                    current_content = file_content
                
                # Parse existing JSON
                todo_data = json.loads(current_content)
                
                # Update tasks (replace existing tasks with new ones)
                todo_data["tasks"] = tasks
                todo_data["updated_at"] = datetime.now().isoformat()
                
                # Write back to file
                json_content = json.dumps(todo_data, indent=2, ensure_ascii=False)
                result = simple_write_file(self.todo_file, json_content)
                return f"Updated todo.json with {len(tasks)} tasks. {result}"
                
            except json.JSONDecodeError:
                # If JSON is corrupted, recreate the file
                todo_data = {
                    "project_name": "Game Character Creation",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "tasks": tasks
                }
                
                json_content = json.dumps(todo_data, indent=2, ensure_ascii=False)
                result = simple_write_file(self.todo_file, json_content)
                return f"Recreated todo.json with {len(tasks)} tasks. {result}"
    
    def update_task_in_todo(self, task_id: str, assets_info: dict) -> str:
        """Update a specific task in todo.json with completion info"""
        from simple_file_tools import simple_read_file, simple_write_file
        
        file_content = simple_read_file(self.todo_file)
        
        if "Error: File not found" in file_content:
            return "Error: todo.json not found"
        
        try:
            # Extract content
            if "Content:\n" in file_content:
                content = file_content.split("Content:\n", 1)[1]
            else:
                content = file_content
            
            # Parse JSON
            todo_data = json.loads(content)
            
            # Find and update the specific task
            tasks = todo_data.get("tasks", [])
            task_updated = False
            
            for task in tasks:
                if task.get("task_id") == task_id:
                    # Update task status and asset info
                    task["status"] = "completed"
                    task["generated_assets_info"]["s3_url"] = assets_info.get("assets_url", "")
                    task["generated_assets_info"]["description"] = assets_info.get("description", "")
                    task_updated = True
                    break
            
            if task_updated:
                # Update timestamp
                todo_data["updated_at"] = datetime.now().isoformat()
                
                # Write back to file
                json_content = json.dumps(todo_data, indent=2, ensure_ascii=False)
                result = simple_write_file(self.todo_file, json_content)
                return f"Updated task {task_id} in todo.json. {result}"
            else:
                return f"Error: Task {task_id} not found in todo.json"
                
        except json.JSONDecodeError:
            return f"Error: Could not parse todo.json"
    
    def initialize_phases_in_todo(self, phases: List[Dict[str, Any]]) -> str:
        """Initialize todo.json with phases but empty tasks arrays"""
        from simple_file_tools import simple_write_file
        
        # Create todo.json structure with phases but empty tasks
        todo_data = {
            "project_name": "Game Character Creation",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "phases": []
        }
        
        # Add each phase with empty tasks array
        for phase in phases:
            phase_data = {
                "phase_id": phase.get("phase_id", ""),
                "phase_name": phase.get("phase_name", ""),
                "phase_description": phase.get("phase_description", ""),
                "phase_dependencies": phase.get("phase_dependencies", []),
                "estimated_subtasks": phase.get("estimated_subtasks", 3),
                "status": "pending",
                "tasks": []
            }
            todo_data["phases"].append(phase_data)
        
        # Write to file
        json_content = json.dumps(todo_data, indent=2, ensure_ascii=False)
        result = simple_write_file(self.todo_file, json_content)
        
        return f"Initialized todo.json with {len(phases)} phases. {result}"
    
    def process_phase_completely(self, phase: Dict[str, Any], character_request: str, phase_number: int) -> List[Dict[str, Any]]:
        """Process a phase completely by breaking it down into subtasks and executing them one by one"""
        from simple_file_tools import simple_read_file, simple_write_file
        
        phase_id = phase.get("phase_id", "")
        phase_name = phase.get("phase_name", "")
        
        
        # Step 1: Break down the phase into subtasks
        subtasks = self.break_down_phase(phase, character_request, "No previous AI interactions available in this context.")
        
        # Step 2: Update the phase in todo.json with the subtasks
        self._update_phase_in_todo(phase_id, subtasks, "in_progress")
        
        # Step 3: Execute each subtask one by one
        completed_results = []
        role_creator = self.agents.get("role_creator")
        
        if not role_creator:
            return []
        
        for i, subtask in enumerate(subtasks):
            subtask_number = i + 1
            task_id = subtask.get("task_id", "")
            task_name = subtask.get("task_name", "")
            
            
            # Execute the subtask with context from previous results
            context = {
                "character_request": character_request,
                "phase_number": phase_number,
                "subtask_number": subtask_number,
                "total_subtasks": len(subtasks)
            }
            
            try:
                # Execute the subtask
                result = role_creator.execute_subtask(subtask, phase, completed_results, context)
                completed_results.append(result)
                
                # Update the specific task in todo.json
                self._update_task_in_phase(phase_id, task_id, result)
                
                
            except Exception as e:
                # Continue with next subtask even if one fails
                error_result = {
                    "task_id": task_id,
                    "phase_id": phase_id,
                    "agent": "role_creator",
                    "description": f"Error executing task: {str(e)}",
                    "assets_url": "",
                    "status": "error"
                }
                completed_results.append(error_result)
                self._update_task_in_phase(phase_id, task_id, error_result)
        
        # Step 4: Mark the phase as completed
        self._update_phase_in_todo(phase_id, subtasks, "completed")
        
        return completed_results
    
    def _update_phase_in_todo(self, phase_id: str, subtasks: List[Dict[str, Any]], status: str) -> str:
        """Update a specific phase in todo.json with subtasks and status"""
        from simple_file_tools import simple_read_file, simple_write_file
        
        file_content = simple_read_file(self.todo_file)
        
        if "Error: File not found" in file_content:
            return "Error: todo.json not found"
        
        try:
            # Extract content
            if "Content:\n" in file_content:
                content = file_content.split("Content:\n", 1)[1]
            else:
                content = file_content
            
            # Parse JSON
            todo_data = json.loads(content)
            
            # Find and update the specific phase
            phases = todo_data.get("phases", [])
            phase_updated = False
            
            for phase in phases:
                if phase.get("phase_id") == phase_id:
                    # Update phase status and tasks
                    phase["status"] = status
                    phase["tasks"] = subtasks
                    phase_updated = True
                    break
            
            if phase_updated:
                # Update timestamp
                todo_data["updated_at"] = datetime.now().isoformat()
                
                # Write back to file
                json_content = json.dumps(todo_data, indent=2, ensure_ascii=False)
                result = simple_write_file(self.todo_file, json_content)
                return f"Updated phase {phase_id} with {len(subtasks)} tasks and status {status}. {result}"
            else:
                return f"Error: Phase {phase_id} not found in todo.json"
                
        except json.JSONDecodeError:
            return f"Error: Could not parse todo.json"
    
    def _update_task_in_phase(self, phase_id: str, task_id: str, result: Dict[str, Any]) -> str:
        """Update a specific task within a phase in todo.json"""
        from simple_file_tools import simple_read_file, simple_write_file
        
        file_content = simple_read_file(self.todo_file)
        
        if "Error: File not found" in file_content:
            return "Error: todo.json not found"
        
        try:
            # Extract content
            if "Content:\n" in file_content:
                content = file_content.split("Content:\n", 1)[1]
            else:
                content = file_content
            
            # Parse JSON
            todo_data = json.loads(content)
            
            # Find the phase and update the specific task
            phases = todo_data.get("phases", [])
            task_updated = False
            
            for phase in phases:
                if phase.get("phase_id") == phase_id:
                    tasks = phase.get("tasks", [])
                    for task in tasks:
                        if task.get("task_id") == task_id:
                            # Update task status and asset info
                            task["status"] = result.get("status", "completed")
                            if "generated_assets_info" not in task:
                                task["generated_assets_info"] = {}
                            task["generated_assets_info"]["s3_url"] = result.get("assets_url", "")
                            task["generated_assets_info"]["description"] = result.get("description", "")
                            task_updated = True
                            break
                    if task_updated:
                        break
            
            if task_updated:
                # Update timestamp
                todo_data["updated_at"] = datetime.now().isoformat()
                
                # Write back to file
                json_content = json.dumps(todo_data, indent=2, ensure_ascii=False)
                write_result = simple_write_file(self.todo_file, json_content)
                return f"Updated task {task_id} in phase {phase_id}. {write_result}"
            else:
                return f"Error: Task {task_id} not found in phase {phase_id}"
                
        except json.JSONDecodeError:
            return f"Error: Could not parse todo.json"
    
    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute supervision logic and return updated state"""
        if state["workflow_data"].get("status") == "planned":
            phases = state["workflow_data"]["phases"]
            ai_history_context = format_ai_history_context_from_messages(state.get("messages", []))
            
            messages = [
                SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT.format(ai_history_context=ai_history_context)),
                HumanMessage(content=f"""Initializing workflow with {len(phases)} phases for character: {state["character_request"]}
                
Phases: {json.dumps(phases, indent=2)}
                
Please review and initialize the workflow.""")
            ]
            
            response = self._call_llm(messages)
            todo_result = self.initialize_phases_in_todo(phases)
            
            init_message = AIMessage(
                content=response,
                additional_kwargs={
                    "agent": "supervisor",
                    "role": "initialization",
                    "action": "initialize_todo",
                    "timestamp": datetime.now().isoformat()
                }
            )
            state["messages"] = [init_message]
            
            state["workflow_data"]["status"] = "ready_for_phase_processing"
            
        elif state["workflow_data"].get("status") == "ready_for_phase_processing":
            phases = state["workflow_data"]["phases"]
            current_index = state["workflow_data"]["current_phase_index"]
            if current_index < len(phases):
                current_phase = phases[current_index]
                phase_num = current_index + 1
                total_phases = len(phases)
                
                ai_history_context = format_ai_history_context_from_messages(state.get("messages", []))
                
                messages = [
                    SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT.format(ai_history_context=ai_history_context)),
                    HumanMessage(content=f"""Processing Phase {phase_num} of {total_phases}:
                    
Phase: {current_phase.get('phase_name', '')}
Description: {current_phase.get('phase_description', '')}
Character: {state["character_request"]}
                    
Please break down this phase and execute all subtasks.""")
                ]
                
                response = self._call_llm(messages)
                phase_results = self.process_phase_completely(current_phase, state["character_request"], phase_num)
                
                phase_message = AIMessage(
                    content=response,
                    additional_kwargs={
                        "agent": "supervisor",
                        "role": "phase_processing",
                        "phase_id": current_phase.get("phase_id", ""),
                        "phase_results": phase_results,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                state["messages"] = [phase_message]
                
                if "task_results" not in state["workflow_data"]:
                    state["workflow_data"]["task_results"] = []
                state["workflow_data"]["task_results"].extend(phase_results)
                
                state["workflow_data"]["current_phase_index"] += 1
                
                if state["workflow_data"]["current_phase_index"] >= len(phases):
                    state["workflow_data"]["status"] = "completed"
                    state["messages"] = [HumanMessage(content="All phases completed!")]
                else:
                    state["workflow_data"]["status"] = "ready_for_phase_processing"
            else:
                state["workflow_data"]["status"] = "completed"
        
        return state
