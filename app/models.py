"""Describe how a fictional funding opportunity is stored in the database."""

from datetime import date

from sqlalchemy import JSON, Date, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Grant(Base):
    """One stored grant, including hard eligibility limits and AI relevance topics."""
    __tablename__ = "grants"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    countries: Mapped[list[str]] = mapped_column(JSON)
    company_sizes: Mapped[list[str]] = mapped_column(JSON)
    industries: Mapped[list[str]] = mapped_column(JSON)
    project_types: Mapped[list[str]] = mapped_column(JSON)
    minimum_funding: Mapped[int] = mapped_column(Integer)
    maximum_funding: Mapped[int] = mapped_column(Integer)
    deadline: Mapped[date] = mapped_column(Date)
    source_url: Mapped[str] = mapped_column(String(500))
