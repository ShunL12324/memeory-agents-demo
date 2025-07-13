"""Base agent class for all agents in the multi-agent system."""

from datetime import datetime
import json
import pprint
from typing import Dict, Any, List, Optional, TypedDict
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    AIMessage,
    BaseMessage,
    AnyMessage,
    ToolMessage,
)
from langchain_aws import ChatBedrockConverse
from config import get_bedrock_config


class BaseAgent:
    """Base class for all agents"""

    def __init__(self, name: str, tools: Optional[List] = None):
        self.name = name
        self.tools = tools

        # Use unified Bedrock configuration for all agents
        config = get_bedrock_config()

        # Configure Bedrock with thinking support
        self.llm = ChatBedrockConverse(
            model=config["model_id"],
            max_tokens=config["model_kwargs"]["max_tokens"],
            temperature=config["model_kwargs"]["temperature"],
            region_name=config["region_name"],
            aws_access_key_id=config["aws_access_key_id"],
            aws_secret_access_key=config["aws_secret_access_key"],
            additional_model_request_fields=config.get("thinking_params", {}),
        )

        # Bind tools to LLM if provided
        if tools:
            try:
                self.llm_with_tools = self.llm.bind_tools(tools)
            except Exception as e:
                print(f"Warning: Failed to bind tools for {name}: {e}")
                self.llm_with_tools = self.llm
                self.tools = None  # Disable tools if binding fails
        else:
            self.llm_with_tools = self.llm

    def _call_llm(self, messages: List) -> AIMessage:
        """Call the LLM with messages and return complete response"""
        llm_to_use = self.llm_with_tools if self.tools else self.llm
        return llm_to_use.invoke(messages)

    def _extract_reasoning_content(self, response: AIMessage) -> str:
        """Extract reasoning content from AI response"""
        try:
            response_content = response.content
            if isinstance(response_content, list):
                reasoning_parts = []
                for part in response_content:
                    if part.get("type") == "reasoning_content":
                        reasoning_data = part.get("reasoning_content", {})
                        if isinstance(reasoning_data, dict):
                            reasoning_parts.append(reasoning_data.get("text", ""))
                        else:
                            reasoning_parts.append(str(reasoning_data))
                return "\n".join(reasoning_parts) if reasoning_parts else ""
            else:
                return ""
        except Exception as e:
            return ""

    def _extract_text_content(self, response: AIMessage) -> str:
        """Extract text content from AI response (for backward compatibility)"""
        try:
            response_content = response.content

            if isinstance(response_content, list):
                # Extract text content from thinking response format
                text_parts = [
                    part.get("text", "")
                    for part in response_content
                    if part.get("type") == "text"
                ]
                return "\n".join(text_parts) if text_parts else str(response_content)
            else:
                return response_content
        except Exception as e:
            return ""

    def _format_messages_to_dict(self, messages: AnyMessage) -> List[Dict]:
        result = []
        try:
            for msg in messages:
                role = "assistant"
                if isinstance(msg, AIMessage):
                    role = "assistant"
                elif isinstance(msg, HumanMessage):
                    role = "user"
                elif isinstance(msg, ToolMessage):
                    role = "assistant"
                elif isinstance(msg, SystemMessage):
                    role = "system"
                result.append(
                    {
                        "role": role,
                        "content": (
                            msg.content
                            if self._extract_text_content(msg)
                            else isinstance(msg.content, List)
                        ),
                    }
                )
        except Exception as e:
            print(e)
        return result

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent logic and return updated state. To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement the execute method")
