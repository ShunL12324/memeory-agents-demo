"""Utility functions for the memory agents demo project."""

import json
from typing import Any, Dict, List, Union


class JSONExtractionError(Exception):
    """Exception raised when JSON extraction fails."""
    pass


def extract_json_from_response(response: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Extract JSON from AI response text.
    
    This function attempts to parse JSON from various formats:
    1. Markdown code blocks (```json ... ```)
    2. Raw JSON strings
    
    Args:
        response: The AI response text containing JSON
        
    Returns:
        Parsed JSON object (dict or list)
        
    Raises:
        JSONExtractionError: If JSON cannot be extracted or parsed
    """
    if not response or not response.strip():
        raise JSONExtractionError("Empty or None response provided")
    
    response = response.strip()
    
    # Try to extract JSON from markdown code block first
    if "```json" in response:
        json_start = response.find("```json") + 7
        json_end = response.find("```", json_start)
        
        if json_end == -1:
            raise JSONExtractionError("Malformed JSON code block: missing closing ```")
        
        json_content = response[json_start:json_end].strip()
        
        if not json_content:
            raise JSONExtractionError("Empty JSON content in code block")
        
        try:
            return json.loads(json_content)
        except json.JSONDecodeError as e:
            raise JSONExtractionError(f"Invalid JSON in code block: {str(e)}")
    
    # Try to find JSON array or object in the response
    json_patterns = [
        (r'\[[\s\S]*\]', 'JSON array'),  # Find JSON arrays
        (r'\{[\s\S]*\}', 'JSON object')  # Find JSON objects
    ]
    
    import re
    for pattern, pattern_name in json_patterns:
        matches = re.findall(pattern, response)
        for match in matches:
            try:
                # Try to parse each potential JSON match
                parsed = json.loads(match.strip())
                return parsed
            except json.JSONDecodeError:
                continue
    
    # Try to parse the entire response as JSON (fallback)
    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        # If all else fails, provide detailed error info
        response_preview = response[:200] + "..." if len(response) > 200 else response
        raise JSONExtractionError(f"Could not extract valid JSON from response. Response preview: {response_preview}")


def validate_json_structure(data: Any, expected_type: type = None, required_fields: List[str] = None) -> None:
    """
    Validate JSON structure and required fields.
    
    Args:
        data: The parsed JSON data
        expected_type: Expected type (dict, list, etc.)
        required_fields: List of required field names (only for dict type)
        
    Raises:
        JSONExtractionError: If validation fails
    """
    if expected_type is not None and not isinstance(data, expected_type):
        raise JSONExtractionError(f"Expected {expected_type.__name__}, got {type(data).__name__}")
    
    if required_fields and isinstance(data, dict):
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise JSONExtractionError(f"Missing required fields: {', '.join(missing_fields)}")
    
    if required_fields and isinstance(data, list):
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                raise JSONExtractionError(f"List item {i} is not a dictionary")
            missing_fields = [field for field in required_fields if field not in item]
            if missing_fields:
                raise JSONExtractionError(f"List item {i} missing required fields: {', '.join(missing_fields)}")


def extract_and_validate_json(response: str, expected_type: type = None, required_fields: List[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Extract JSON from response and validate its structure.
    
    Args:
        response: The AI response text containing JSON
        expected_type: Expected type (dict, list, etc.)
        required_fields: List of required field names
        
    Returns:
        Validated JSON object
        
    Raises:
        JSONExtractionError: If extraction or validation fails
    """
    data = extract_json_from_response(response)
    validate_json_structure(data, expected_type, required_fields)
    return data