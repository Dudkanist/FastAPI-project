from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # Связь: один пользователь может иметь много последовательностей
    sequences = relationship("Sequence", back_populates="owner")

class Sequence(Base):
    __tablename__ = "sequences"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    raw_sequence = Column(String, nullable=False)  # Сама строка ATGC...
    molecule_type = Column(String)  # DNA, RNA или Protein
    created_at = Column(DateTime, default=datetime.utcnow)
    
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="sequences")
    
    # Связь: одна последовательность — один результат анализа
    analysis = relationship("AnalysisResult", back_populates="sequence", uselist=False)

class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    sequence_id = Column(Integer, ForeignKey("sequences.id"))
    gc_content = Column(Float)
    melting_temp = Column(Float)
    molecular_weight = Column(Float)
    
    sequence = relationship("Sequence", back_populates="analysis")
