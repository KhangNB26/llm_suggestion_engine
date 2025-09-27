import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from src.schema import AISuggestionResponse, ValidationError

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.0-flash-lite-preview-02-05")

def llm(context: dict) -> AISuggestionResponse:
    """
    Generate AI suggestion and normalize directly into AISuggestionResponse.
    """
    prompt = f"""
    You are an AI Suggestion Engine.
    Based on the context below, return suggestions in strict JSON format.

    Target schema:
    {{
      "items": [
        {{
          "item_type": "if title in context contains 'Checklist' or similar, then 1 (checklist), else 0 (task)",
          "title": "string (concise, clear, if item_type==1, must contain 'checklist')",
          "parentTaskId": "set to null if scheduleEntries field in context is empty, otherwise, string (uuid) of task_id in context",
          "estimated_minutes": int (1-300),
          "deadline": "ISO8601 UTC Z format (yyyy-mm-ddTHH:MM:SSZ) and must before the effective_deadline in context",
          "confidence": float 0-1,
          "reason": "string (explanation of why this item is suggested based on the chronotype and every fields insist of time in context (remember to add time), if status == 1 then this is a continuous progress so consider adding "tiep tuc" or "hien co" based on it  ) or null (if freeSlots contains nothing or status == 2 in context)"
        }}
      ]
    }}

    Requirements:
    - Viet bang tieng Viet khong dau.
    - Giu dung schema tren.

    Context:  
    {json.dumps(context, ensure_ascii=False)}
    """

    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            response_mime_type="application/json"
        )
    )

    try:
        parsed = json.loads(response.text)
    except Exception:
        parsed = {"items": []}

    try:
        return AISuggestionResponse(**parsed)
    except ValidationError as e:
        print("Validation failed:", e)
        return AISuggestionResponse(items=[])
