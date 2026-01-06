from typing import Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field


class Job(BaseModel):
    id: str
    status: str
    progress: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime