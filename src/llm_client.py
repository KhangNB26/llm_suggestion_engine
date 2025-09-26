import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from src.schema import AISuggestionResponse, ValidationError

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.0-flash")

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
          "item_type": 0 or 1,
          "title": "string",
          "parentTaskId": "uuid or null",
          "estimated_minutes": int (1-300),
          "deadline": "ISO8601 UTC Z format (yyyy-mm-ddTHH:MM:SSZ)",
          "confidence": float 0-1,
          "reason": "string or null"
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
