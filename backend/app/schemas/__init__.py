from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=255)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SkillOut(BaseModel):
    id: int
    name: str          # normalized
    display_name: str
    category: Optional[str] = None

    class Config:
        from_attributes = True


class ExtractedSkill(BaseModel):
    display_name: str
    category: Optional[str] = None  # language|framework|db|cloud|tool|other


class ResumeExtractResponse(BaseModel):
    resume_text_preview: str       # первые 500 символов для отладки
    skills: List[ExtractedSkill]   # КАНДИДАТЫ — пользователь редактирует на фронте


class SkillsSaveRequest(BaseModel):
    skills: List[ExtractedSkill] = Field(min_length=0, max_length=200)
