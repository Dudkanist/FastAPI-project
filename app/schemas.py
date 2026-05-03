from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# --- Схемы для Пользователя ---


class UserBase(BaseModel):
    email: str


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    # Позволяет Pydantic читать данные прямо из объектов SQLAlchemy
    model_config = ConfigDict(from_attributes=True)


# --- Схемы для Результатов Анализа ---


class AnalysisResultBase(BaseModel):
    gc_content: float
    melting_temp: float
    molecular_weight: float
    model_config = ConfigDict(from_attributes=True)


# --- Схемы для Последовательностей ---


class SequenceBase(BaseModel):
    name: str
    description: Optional[str] = None
    # Регулярка для валидации: только нуклеотиды ATGC (регистронезависимо)
    raw_sequence: str = Field(..., pattern=r"^[ATGCatgc\s]+$")
    molecule_type: str = "DNA"


class SequenceCreate(SequenceBase):
    pass


class SequenceResponse(SequenceBase):
    id: int
    owner_id: int
    created_at: datetime
    # Если анализ уже проведен, мы можем включить его в ответ
    analysis: Optional[AnalysisResultBase] = None

    model_config = ConfigDict(from_attributes=True)
