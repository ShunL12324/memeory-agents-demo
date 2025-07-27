"""Logging system for multi-agent workflow."""

import json
from datetime import datetime
from pathlib import Path

from typing_extensions import Any, Dict, Optional


class WorkflowLogger:
    """Logger for multi-agent workflow execution"""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)

        # Create log files with timestamp
        self.log_file = self.logs_dir / f"workflow_{self.session_id}.log"

        # Clean up old log files, keep only 3 most recent
        self._cleanup_old_logs()

        # Initialize log data
        self.log_data = {
            "session_id": self.session_id,
            "start_time": datetime.now().isoformat(),
            "workflow_steps": [],
            "agent_interactions": [],
            "tool_calls": [],
            "errors": [],
            "final_status": None,
        }

        # Write initial log entry
        self._write_log(
            "INFO",
            "workflow",
            "Workflow logging started",
            {
                "session_id": self.session_id,
                "log_file": str(self.log_file),
            },
        )

    def _write_log(
        self,
        level: str,
        component: str,
        message: Any,
        data: Optional[Dict[str, Any]] = None,
    ):
        """Write a log entry to text, JSON, and markdown logs"""
        timestamp = datetime.now().isoformat()

        # Convert message to string safely
        message_str = str(message) if message is not None else ""

        # Text log entry
        log_entry = f"[{timestamp}] [{level}] [{component}] {message_str}"
        if data:
            log_entry += f" | Data: {json.dumps(data, ensure_ascii=False)}"

        # Write to text log with error handling
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
        except (OSError, IOError) as e:
            print(f"Warning: Failed to write to log file {self.log_file}: {e}")

        # Print to console
        print(log_entry)

        # Add to JSON log data
        json_entry = {
            "timestamp": timestamp,
            "level": level,
            "component": component,
            "message": message_str,
            "data": data or {},
        }

        # Categorize the entry
        if component.endswith("_agent"):
            self.log_data["agent_interactions"].append(json_entry)
        elif "tool" in component.lower():
            self.log_data["tool_calls"].append(json_entry)
        elif level == "ERROR":
            self.log_data["errors"].append(json_entry)
        else:
            self.log_data["workflow_steps"].append(json_entry)

    def _cleanup_old_logs(self):
        """Keep only the 3 most recent log files"""
        log_files = list(self.logs_dir.glob("workflow_*.log"))
        if len(log_files) > 3:
            # Sort by modification time, newest first
            log_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            # Remove old files beyond the 3 most recent
            for old_file in log_files[3:]:
                try:
                    old_file.unlink()
                except OSError:
                    pass  # Ignore errors if file can't be deleted

    def log_workflow_start(
        self, character_request: Any, context: Optional[Dict[str, Any]] = None
    ):
        """Log workflow start"""
        self._write_log(
            "INFO",
            "workflow",
            "Character creation workflow started",
            {"character_request": character_request, "context": context or {}},
        )

    def log_workflow_end(
        self, status: str, final_state: Optional[Dict[str, Any]] = None
    ):
        """Log workflow completion"""
        self.log_data["final_status"] = status
        self.log_data["end_time"] = datetime.now().isoformat()

        self._write_log(
            "INFO",
            "workflow",
            f"Workflow completed with status: {status}",
            {"final_state": final_state or {}},
        )

    def log_agent_response(
        self,
        agent_name: str,
        action: str,
        input_data: Dict[str, Any],
        response: Any,
        processing_time: Any = None,
    ):
        """Log agent response"""
        # Convert response to string safely
        response_str = str(response) if response is not None else ""

        self._write_log(
            "INFO",
            f"{agent_name}_agent",
            f"Agent action: {action}",
            {
                "input": input_data,
                "response": response_str,  # Keep full response for thinking content
                "response_length": len(response_str),
                "processing_time_seconds": processing_time,
            },
        )

    def log_tool_call(
        self,
        agent_name: str,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_output: Any,
        success: bool = True,
    ):
        """Log tool call"""
        level = "INFO" if success else "ERROR"
        # Convert tool_output to string safely and truncate if needed
        tool_output_str = str(tool_output) if tool_output is not None else ""
        truncated_output = (
            tool_output_str[:300] + "..."
            if len(tool_output_str) > 300
            else tool_output_str
        )

        self._write_log(
            level,
            f"tool_{tool_name}",
            f"Tool called by {agent_name}",
            {
                "tool_input": tool_input,
                "tool_output": truncated_output,
                "success": success,
                "agent": agent_name,
            },
        )

    def log_state_transition(
        self, from_node: str, to_node: str, state_data: Dict[str, Any]
    ):
        """Log state transition between nodes"""
        self._write_log(
            "INFO",
            "workflow",
            f"State transition: {from_node} -> {to_node}",
            {
                "from_node": from_node,
                "to_node": to_node,
                "current_task_index": state_data.get("current_task_index"),
                "status": state_data.get("status"),
                "task_count": len(state_data.get("task_results", [])),
            },
        )

    def log_task_completion(
        self, task_id: str, task_name: str, asset_info: Dict[str, Any]
    ):
        """Log task completion"""
        self._write_log(
            "INFO",
            "task",
            f"Task completed: {task_id}",
            {"task_id": task_id, "task_name": task_name, "asset_info": asset_info},
        )

    def log_error(
        self,
        component: str,
        error_message: Any,
        error_data: Optional[Dict[str, Any]] = None,
    ):
        """Log error"""
        self._write_log("ERROR", component, error_message, error_data or {})

    def error(self, error_message: Any, error_data: Optional[Dict[str, Any]] = None):
        """Alias for log_error with default component"""
        self.log_error("system", error_message, error_data)

    def log_plan_creation(self, plan: Dict[str, Any]):
        """Log plan creation"""
        tasks = plan.get("tasks", [])
        self._write_log(
            "INFO",
            "planner_agent",
            f"Plan created with {len(tasks)} tasks",
            {
                "task_count": len(tasks),
                "task_list": [
                    {"task_id": t.get("task_id"), "task_name": t.get("task_name")}
                    for t in tasks
                ],
            },
        )

    def log_todo_file_operation(self, operation: str, file_path: str, result: str):
        """Log todo file operations"""
        self._write_log(
            "INFO",
            "supervisor_agent",
            f"Todo file {operation}",
            {"operation": operation, "file_path": file_path, "result": result},
        )

    def get_log_summary(self) -> Dict[str, Any]:
        """Get a summary of the current log"""
        return {
            "session_id": self.session_id,
            "workflow_steps_count": len(self.log_data["workflow_steps"]),
            "agent_interactions_count": len(self.log_data["agent_interactions"]),
            "tool_calls_count": len(self.log_data["tool_calls"]),
            "errors_count": len(self.log_data["errors"]),
            "final_status": self.log_data["final_status"],
            "log_file": str(self.log_file),
        }


# Global logger instance
_current_logger: Optional[WorkflowLogger] = None


def get_logger(session_id: Any = None) -> WorkflowLogger:
    """Get or create workflow logger"""
    global _current_logger
    if _current_logger is None or (
        session_id and _current_logger.session_id != session_id
    ):
        _current_logger = WorkflowLogger(session_id)
    return _current_logger


def log_agent_response(
    agent_name: str,
    action: str,
    input_data: Dict[str, Any],
    response: Any,
    processing_time: Any = None,
):
    """Convenience function to log agent response"""
    get_logger().log_agent_response(
        agent_name, action, input_data, response, processing_time
    )


def log_tool_call(
    agent_name: str,
    tool_name: str,
    tool_input: Dict[str, Any],
    tool_output: Any,
    success: bool = True,
):
    """Convenience function to log tool call"""
    get_logger().log_tool_call(agent_name, tool_name, tool_input, tool_output, success)


def log_error(
    component: str, error_message: Any, error_data: Optional[Dict[str, Any]] = None
):
    """Convenience function to log error"""
    get_logger().log_error(component, error_message, error_data)
