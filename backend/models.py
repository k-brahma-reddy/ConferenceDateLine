"""
Data models for conference deadline tracking.
"""
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class Deadline:
    """Represents a deadline entry for a conference track or workshop."""
    conference_name: str
    track_name: str
    workshop_name: Optional[str]
    paper_submission_date: date
    abstract_deadline: Optional[date]
    intimation_date: date

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "conference_name": self.conference_name,
            "track_name": self.track_name,
            "workshop_name": self.workshop_name,
            "paper_submission_date": self.paper_submission_date.isoformat() if self.paper_submission_date else None,
            "abstract_deadline": self.abstract_deadline.isoformat() if self.abstract_deadline else None,
            "intimation_date": self.intimation_date.isoformat() if self.intimation_date else None,
        }

    @property
    def display_name(self) -> str:
        """Get a display name for this deadline entry."""
        parts = [self.conference_name]
        if self.track_name:
            parts.append(self.track_name)
        if self.workshop_name:
            parts.append(self.workshop_name)
        return " - ".join(parts)


@dataclass
class Conference:
    """Represents a conference with its tracks."""
    name: str
    tracks: list  # List of track names

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "tracks": self.tracks
        }


def parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse a date string in YYYY-MM-DD format."""
    if not date_str or date_str.strip() == "":
        return None
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None