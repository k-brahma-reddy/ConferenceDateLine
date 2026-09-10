"""
Data loader for reading conference deadlines from CSV files.
Supports local files and OneDrive URLs.
"""
import csv
import os
from io import StringIO
from typing import List, Optional
from urllib.request import urlopen

from models import Deadline, parse_date, Conference


class DataLoader:
    """Load conference deadline data from CSV sources."""

    def __init__(self, data_path: str = None):
        """
        Initialize the data loader.
        
        Args:
            data_path: Path to CSV file (local) or URL (OneDrive)
        """
        if data_path is None:
            # Default to data/conferences.csv in the project root
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.data_path = os.path.join(base_dir, "data", "conferences.csv")
        else:
            self.data_path = data_path

    def _get_csv_content(self) -> str:
        """Get CSV content from local file or URL."""
        if self.data_path.startswith(("http://", "https://")):
            # Load from URL (OneDrive or other)
            with urlopen(self.data_path) as response:
                return response.read().decode('utf-8')
        else:
            # Load from local file
            with open(self.data_path, 'r', encoding='utf-8') as f:
                return f.read()

    def load_deadlines(self) -> List[Deadline]:
        """Load all deadlines from the CSV source."""
        deadlines = []
        content = self._get_csv_content()
        
        reader = csv.DictReader(StringIO(content))
        for row in reader:
            deadline = Deadline(
                conference_name=row.get('conference_name', '').strip(),
                track_name=row.get('track_name', '').strip(),
                workshop_name=row.get('workshop_name', '').strip() or None,
                paper_submission_date=parse_date(row.get('paper_submission_date')),
                abstract_deadline=parse_date(row.get('abstract_deadline')),
                intimation_date=parse_date(row.get('intimation_date')),
            )
            if deadline.conference_name and deadline.paper_submission_date:
                deadlines.append(deadline)
        
        return deadlines

    def get_conferences(self) -> List[Conference]:
        """Get unique conferences with their tracks."""
        deadlines = self.load_deadlines()
        
        conferences_dict = {}
        for d in deadlines:
            if d.conference_name not in conferences_dict:
                conferences_dict[d.conference_name] = set()
            if d.track_name:
                conferences_dict[d.conference_name].add(d.track_name)
        
        return [
            Conference(name=name, tracks=sorted(list(tracks)))
            for name, tracks in sorted(conferences_dict.items())
        ]

    def get_deadlines_for_timeline(self) -> List[dict]:
        """Get deadlines formatted for timeline display."""
        deadlines = self.load_deadlines()
        return [d.to_dict() for d in deadlines]

    def add_workshop(self, conference_name: str, track_name: str, 
                     workshop_name: str, paper_submission_date: str,
                     abstract_deadline: Optional[str], intimation_date: str) -> Deadline:
        """
        Add a new workshop entry to the CSV file.
        
        Returns the created Deadline object.
        """
        new_deadline = Deadline(
            conference_name=conference_name,
            track_name=track_name,
            workshop_name=workshop_name,
            paper_submission_date=parse_date(paper_submission_date),
            abstract_deadline=parse_date(abstract_deadline) if abstract_deadline else None,
            intimation_date=parse_date(intimation_date),
        )
        
        # Append to CSV file
        file_exists = os.path.exists(self.data_path)
        with open(self.data_path, 'a', newline='', encoding='utf-8') as f:
            fieldnames = ['conference_name', 'track_name', 'workshop_name', 
                         'paper_submission_date', 'abstract_deadline', 'intimation_date']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow({
                'conference_name': new_deadline.conference_name,
                'track_name': new_deadline.track_name,
                'workshop_name': new_deadline.workshop_name or '',
                'paper_submission_date': new_deadline.paper_submission_date.isoformat(),
                'abstract_deadline': new_deadline.abstract_deadline.isoformat() if new_deadline.abstract_deadline else '',
                'intimation_date': new_deadline.intimation_date.isoformat(),
            })
        
        return new_deadline
    
    def add_conference(self, name: str, year: str = None) -> Conference:
        """
        Add a new conference entry to the CSV file.
        
        Returns the created Conference object.
        """
        # Conference entries are just placeholders - they get populated when tracks/workshops are added
        # For now, we just ensure the conference name exists in the system
        return Conference(name=name, tracks=[])


if __name__ == "__main__":
    # Test the loader
    loader = DataLoader()
    print("Conferences:", loader.get_conferences())
    print("Deadlines:", loader.get_deadlines_for_timeline())