"""Simple file operations without LangChain complexity."""

from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


def simple_read_file(file_path: str) -> str:
    """Simple file read operation."""
    try:
        path = Path(file_path)
        if not path.exists():
            return "Error: File not found"
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return f"Content:\n{content}"
    except Exception as e:
        return f"Error: {str(e)}"


def simple_write_file(file_path: str, content: str) -> str:
    """Simple file write operation."""
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to {file_path}"
    except Exception as e:
        return f"Error: {str(e)}"


def simple_edit_file(file_path: str, old_text: str, new_text: str) -> str:
    """Simple file edit operation."""
    try:
        path = Path(file_path)
        if not path.exists():
            return "Error: File not found"
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if old_text not in content:
            return "Error: Text to replace not found"
        
        new_content = content.replace(old_text, new_text)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        count = content.count(old_text)
        return f"Successfully replaced {count} occurrence(s)"
    except Exception as e:
        return f"Error: {str(e)}"


def format_ai_history_context_from_messages(messages: List) -> str:
    """
    Format AI history from LangChain messages into a readable context string.
    
    Args:
        messages: List of LangChain messages (HumanMessage, AIMessage, etc.)
    
    Returns:
        Formatted string for injection into prompts
    """
    if not messages:
        return "No previous AI interactions in this session."
    
    formatted_context = []
    formatted_context.append("### Previous AI Interactions:\n")
    
    ai_messages = [msg for msg in messages if hasattr(msg, 'additional_kwargs') and msg.additional_kwargs]
    
    if not ai_messages:
        return "No previous AI interactions in this session."
    
    for i, message in enumerate(ai_messages, 1):
        kwargs = message.additional_kwargs
        agent = kwargs.get("agent", "unknown")
        role = kwargs.get("role", "unknown")
        content = message.content[:300] + "..." if len(message.content) > 300 else message.content
        timestamp = kwargs.get("timestamp", "")
        
        formatted_context.append(f"**Interaction {i} - {agent.title()} ({role})**")
        if timestamp:
            formatted_context.append(f"Time: {timestamp}")
        formatted_context.append(f"Response: {content}")
        formatted_context.append("")  # Empty line for readability
    
    return "\n".join(formatted_context)


def format_ai_history_context(ai_history: List[Dict[str, Any]]) -> str:
    """
    Format AI history into a readable context string for injection into prompts.
    
    Args:
        ai_history: List of AI interaction records with format:
            [
                {
                    "agent": "planner|supervisor|executor",
                    "role": "planning|initialization|phase_processing|execution", 
                    "response": "raw AI response text",
                    "timestamp": "ISO timestamp",
                    # other context-specific fields
                }
            ]
    
    Returns:
        Formatted string for injection into prompts
    """
    if not ai_history:
        return "No previous AI interactions in this session."
    
    formatted_context = []
    formatted_context.append("### Previous AI Interactions:\n")
    
    for i, interaction in enumerate(ai_history, 1):
        agent = interaction.get("agent", "unknown")
        role = interaction.get("role", "unknown")
        response = interaction.get("response", "")
        timestamp = interaction.get("timestamp", "")
        
        # Parse timestamp if available
        time_str = ""
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = f" at {dt.strftime('%H:%M:%S')}"
            except:
                time_str = f" at {timestamp}"
        
        formatted_context.append(f"**{i}. {agent.capitalize()} Agent - {role.capitalize()}{time_str}:**")
        
        # Truncate long responses for readability
        if len(response) > 800:
            truncated_response = response[:800] + "... [truncated]"
        else:
            truncated_response = response
        
        formatted_context.append(f"```")
        formatted_context.append(truncated_response)
        formatted_context.append(f"```\n")
        
        # Add any additional context fields
        for key, value in interaction.items():
            if key not in ["agent", "role", "response", "timestamp"] and value:
                formatted_context.append(f"- {key}: {value}")
        
        formatted_context.append("")  # Empty line between interactions
    
    return "\n".join(formatted_context)