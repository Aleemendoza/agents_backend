"""Sample agent used to validate runtime behavior."""


def run(input_data: dict, context: dict) -> dict:
    """Echo incoming message and include optional contextual metadata."""

    _ = context
    message = input_data.get("message", "")
    return {"response": f"Echo: {message}"}
