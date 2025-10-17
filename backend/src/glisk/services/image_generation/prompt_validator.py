"""Prompt validation for image generation.

Validates text prompts before sending to Replicate API.
"""


def validate_prompt(prompt: str) -> str:
    """Validate prompt text for image generation.

    Args:
        prompt: Text prompt from author

    Returns:
        Validated prompt (unchanged if valid)

    Raises:
        ValueError: If prompt is empty, None, or exceeds 1000 characters
    """
    if not prompt:
        raise ValueError("Prompt cannot be empty or None")

    if not isinstance(prompt, str):
        raise ValueError(f"Prompt must be a string, got {type(prompt).__name__}")

    if len(prompt) > 1000:
        raise ValueError(f"Prompt exceeds maximum length of 1000 characters (got {len(prompt)})")

    return prompt
