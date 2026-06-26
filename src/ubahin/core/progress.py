from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ProgressInfo:
    percentage: float = 0.0
    current_file: str = ""
    current_page: int = 0
    total_pages: int = 0
    current_item: int = 0
    total_items: int = 0
    message: str = ""
    estimated_remaining_seconds: float | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "percentage": self.percentage,
            "current_file": self.current_file,
            "current_page": self.current_page,
            "total_pages": self.total_pages,
            "current_item": self.current_item,
            "total_items": self.total_items,
            "message": self.message,
            "estimated_remaining_seconds": self.estimated_remaining_seconds,
        }
