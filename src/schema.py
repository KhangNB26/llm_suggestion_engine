from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, constr, confloat, ValidationError

# =====================
# Pydantic schema
# =====================

ISO_Z_PATTERN = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"

class AISuggestionItem(BaseModel):
    item_type: int = Field(..., description="0 = task, 1 = checklist")
    title: str = Field(..., min_length=1)
    parentTaskId: Optional[UUID] = None
    estimated_minutes: int = Field(..., ge=1, le=300)
    deadline: constr(pattern=ISO_Z_PATTERN)
    confidence: confloat(ge=0.0, le=1.0)
    reason: Optional[str] = None


class AISuggestionResponse(BaseModel):
    items: List[AISuggestionItem] = Field(default_factory=list)

