# app/models/orm.py
# 예시임.
from sqlalchemy.orm import Mapped, mapped_column, declarative_base
from sqlalchemy import String, Float, Integer

Base = declarative_base()

class Recipe(Base):
    __tablename__ = "recipe"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kcal: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    carbs_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    protein_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fat_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
