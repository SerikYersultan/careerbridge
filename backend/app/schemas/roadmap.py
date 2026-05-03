from typing import List, Optional, Literal
from pydantic import BaseModel


class GapItem(BaseModel):
    name: str
    category: str
    frequency: int
    coverage: float
    weight: float


class GapResponse(BaseModel):
    target_role: str
    jobs_analyzed: int
    have: List[GapItem]
    missing: List[GapItem]
    market_top: List[GapItem]


class RoadmapNode(BaseModel):
    id: str
    title: str
    skill: str
    level: Literal["beginner", "intermediate", "advanced"]
    estimated_hours: int
    resource_url: Optional[str] = None
    resource_title: Optional[str] = None
    description: Optional[str] = None


class RoadmapEdge(BaseModel):
    from_: str
    to: str

    class Config:
        fields = {"from_": "from"}
        populate_by_name = True


class RoadmapResponse(BaseModel):
    target_role: str
    nodes: List[RoadmapNode]
    edges: List[dict]
