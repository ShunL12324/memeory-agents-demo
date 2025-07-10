"""Base agent class for all agents in the multi-agent system."""

from typing import Dict, Any, List, Optional, TypedDict
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_aws import ChatBedrockConverse
from config import get_bedrock_config


class BaseAgent:
    """Base class for all agents"""
    
    def __init__(self, name: str, tools: Optional[List] = None):
        self.name = name
        self.tools = tools
        
        # Get Bedrock configuration for this agent
        config = get_bedrock_config(name)
        
        # Configure Bedrock with thinking support
        self.llm = ChatBedrockConverse(
            model=config["model_id"],
            max_tokens=config["model_kwargs"]["max_tokens"],
            temperature=config["model_kwargs"]["temperature"],
            region_name=config["region_name"],
            aws_access_key_id=config["aws_access_key_id"],
            aws_secret_access_key=config["aws_secret_access_key"],
            additional_model_request_fields=config.get("thinking_params", {})
        )
        
        # Bind tools to LLM if provided
        if tools:
            self.llm_with_tools = self.llm.bind_tools(tools)
        else:
            self.llm_with_tools = self.llm
        
    def _call_llm(self, messages: List) -> str:
        """Call the LLM with messages"""
        llm_to_use = self.llm_with_tools if self.tools else self.llm
        response = llm_to_use.invoke(messages)
        
        # Handle different response formats (with/without thinking)
        response_content = response.content
        
        if isinstance(response_content, list):
            # Extract text content from thinking response format
            text_parts = [part.get('text', '') for part in response_content if part.get('type') == 'text']
            return '\n'.join(text_parts) if text_parts else str(response_content)
        else:
            return response_content
    
    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent logic and return updated state. To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement the execute method")