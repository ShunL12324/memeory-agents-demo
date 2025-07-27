"""Base agent class for all agents in the multi-agent system."""

from langchain_aws import ChatBedrockConverse
from langchain_core.tools import BaseTool
from langgraph.prebuilt import create_react_agent

from config import get_bedrock_config


class BaseReactAgent:
    """Base class for all React agents in the multi-agent system."""

    def __init__(self, name: str, prompt: str, tools: list[BaseTool]):
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

        self.react_agent = create_react_agent(
            model=self.llm,
            prompt=prompt,
            tools=self.tools,
            state_schema=self._get_state_schema(),
        )

    def _get_state_schema(self):
        raise NotImplementedError(
            "Subclasses must implement _get_state_schema to define their state schema."
        )
