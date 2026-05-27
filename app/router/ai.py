import os
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from app.security import read_rate_limiter, write_rate_limiter

# We try importing google-genai. If the import or Client init fails due to missing keys,
# we gracefully handle it so that the application is resilient and runs offline.
# Define module-level names so static checkers never see them as unbound.
genai = None
types = None
HAS_GENAI = False
try:
    from google import genai as _genai
    from google.genai import types as _types
    genai = _genai
    types = _types
    HAS_GENAI = True
except Exception:
    genai = None
    types = None
    HAS_GENAI = False

router = APIRouter(prefix="/api/ai", tags=["ai"])



class AISubtaskSuggestions(BaseModel):
    subtasks: List[str] = Field(description="List of 3 to 5 actionable subtasks to accomplish the goal.")




def offline_subtasks_generate(title: str, category: str) -> AISubtaskSuggestions:
    """
    Supplies static task breakdowns mapped to keywords when the Gemini endpoint is offline.
    """
    title_lower = title.lower()
    
    if "groceries" in title_lower or "buy" in title_lower or "shopping" in title_lower or category == "shopping":
        items = [
            "Compile specific item list with quantities",
            "Verify budget and store availability",
            "Visit retail store or place online delivery order",
            "Unpack and organize items"
        ]
    elif "clean" in title_lower or "wash" in title_lower or "tidy" in title_lower:
        items = [
            "Gather cleaning supplies (detergents, cloths, vacuum)",
            "Declutter desks, tables, and floor space",
            "Sanitize surfaces and wipe dust",
            "Empty trash bins and store tools"
        ]
    elif "report" in title_lower or "write" in title_lower or "draft" in title_lower or "email" in title_lower or category == "work":
        items = [
            "Gather reference data and structural outline",
            "Draft main body segments",
            "Format layout, verify typography, and proofread spelling",
            "Send completed copy to target audience"
        ]
    elif "study" in title_lower or "learn" in title_lower or "read" in title_lower or "prepare" in title_lower:
        items = [
            "Determine specific topics to cover",
            "Collect textbooks, tutorials, or documentation",
            "Spend 45 minutes reading/practicing without distraction",
            "Write down short key-takeaway summary notes"
        ]
    else:
        items = [
            "Deconstruct final project requirements",
            "Identify prerequisites and setup local files",
            "Develop basic working prototype",
            "Verify outputs against targets"
        ]
        
    return AISubtaskSuggestions(subtasks=items)


# --- API CONTROLLERS ---

@router.get(
    "/config",
    dependencies=[Depends(read_rate_limiter)]
)
def get_ai_config() -> dict:
    """
    Returns whether the Gemini API key is configured on the backend.
    Used by the frontend to dynamically hide or show AI-powered options.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    return {"has_api_key": bool(api_key)}



@router.get(
    "/subtasks", 
    response_model=AISubtaskSuggestions, 
    dependencies=[Depends(read_rate_limiter)]
)
def suggest_subtasks(
    title: str = Query(..., min_length=3, description="The parent task title"),
    category: str = Query("other", description="Task category context"),
    description: Optional[str] = Query(None, description="Optional description context")
) -> AISubtaskSuggestions:
    """
    Generates 3-5 concrete action items (subtasks) tailored to the task description.
    Gracefully degrades to keyword-matching rule lists if keys are offline.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not HAS_GENAI or not api_key:
        return offline_subtasks_generate(title, category)
        
    try:
        assert genai is not None and types is not None
        client = genai.Client(api_key=api_key)
        
        prompt = f"Task title: '{title}'. Category: {category}. Description: '{description or ''}'."
        system_instructions = (
            "You are a productivity agent. For the provided task, return a JSON list of 3-5 "
            "short, actionable subtasks that are logical steps to complete the parent task. "
            "Do not include task numbering or formatting."
        )
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instructions,
                response_mime_type="application/json",
                response_schema=AISubtaskSuggestions,
            )
        )
        
        response_text = response.text
        if response_text is None:
            raise ValueError("Empty response from Gemini")
        return AISubtaskSuggestions.model_validate_json(response_text)
        
    except Exception as e:
        # safeguard execution
        return offline_subtasks_generate(title, category)
