from fastapi import HTTPException

def load_prompt_template(path: str) -> str:
    """
    Load a prompt template from a file path.
    
    Args:
        path (str): Path to the prompt template file
        
    Returns:
        str: The content of the prompt template file
        
    Raises:
        HTTPException: If the file is not found
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail=f"Prompt template not found at path: {path}"
        ) 