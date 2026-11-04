"""Task and Annotation data models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class Annotation:
    entry: datetime
    description: str


@dataclass
class Task:
    id: int
    uuid: str
    description: str
    status: str
    entry: datetime
    project: Optional[str] = None
    due: Optional[datetime] = None
    priority: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    annotations: list[Annotation] = field(default_factory=list)
    urgency: float = 0.0

    @property
    def is_overdue(self) -> bool:
        return self.due is not None and self.due.date() < date.today()

    @property
    def is_due_today(self) -> bool:
        return self.due is not None and self.due.date() == date.today()

    @property
    def top_project(self) -> str:
        """First component of a dotted project name, or empty string."""
        return self.project.split(".")[0] if self.project else ""
