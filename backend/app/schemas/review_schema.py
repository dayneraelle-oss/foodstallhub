from typing import List, Optional

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    order_id: str
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=2000)


class ReviewOut(BaseModel):
    review_id: str
    order_id: str
    user_id: int
    stall_id: int
    rating: int
    comment: Optional[str] = None
    created_at: str


class ReviewListOut(BaseModel):
    stall_id: int
    average_rating: Optional[float] = None
    total: int
    reviews: List[ReviewOut]