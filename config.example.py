"""Example configuration file - copy to config_local.py and update with your credentials."""

import os
from typing import Dict, Any

# Bedrock configuration
BEDROCK_CONFIG = {
    "model_id": "us.anthropic.claude-sonnet-4-20250514-v1:0",
    "region_name": "us-east-1", 
    "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID", "YOUR_ACCESS_KEY_HERE"),
    "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY", "YOUR_SECRET_KEY_HERE"),
    "request_timeout": 3600,
    "model_kwargs": {
        "max_tokens": 16384,
        "temperature": 1,
        "thinking": {
            "type": "enabled", 
            "budget_tokens": 10000
        }
    }
}

# Agent-specific configurations
AGENT_CONFIGS = {
    "planner": {
        "temperature": 0.7,  # More creative for planning
        "max_tokens": 8192
    },
    "supervisor": {
        "temperature": 0.3,  # More deterministic for coordination
        "max_tokens": 16384
    },
    "executor": {
        "temperature": 0.1,  # Very deterministic for execution
        "max_tokens": 8192
    }
}

def get_bedrock_config(agent_name: str = None) -> Dict[str, Any]:
    """Get Bedrock configuration for a specific agent."""
    config = BEDROCK_CONFIG.copy()
    
    if agent_name and agent_name in AGENT_CONFIGS:
        # Override with agent-specific settings
        agent_config = AGENT_CONFIGS[agent_name]
        config["model_kwargs"].update({
            k: v for k, v in agent_config.items() 
            if k in ["temperature", "max_tokens"]
        })
    
    return config