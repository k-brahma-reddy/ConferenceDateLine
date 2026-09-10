# Conference Deadline Tracker

A web-based interface for tracking conference deadlines, tracks, and workshops with visual timeline display.

## Features

- View deadlines for multiple conferences and their tracks
- Add workshops with paper submission and notification dates
- Visual timeline showing:
  - Paper submission date (start - green marker)
  - Abstract deadline (yellow marker, if applicable)
  - Notification/intimation date (end - red marker)
- Filter by conference
- Data source: CSV file (local or OneDrive URL)
- Future-ready for web scraping integration

## Project Structure

```
researchDashboard/
├── backend/                 # Python Flask server
│   ├── app.py              # Main Flask application
│   ├── models.py           # Data models
│   ├── data_loader.py      # CSV/OneDrive data loading
│   ├── scraper.py          # Placeholder for future scraper
│   └── requirements.txt    # Python dependencies
├── frontend/               # Web interface
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── data/
│   └── conferences.csv     # Conference deadline data
└── README.md
```

## Setup Instructions

### Backend Setup

1. Install Python 3.8+ and pip

2. Navigate to the backend directory:
```bash
cd researchDashboard/backend
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the Flask server:
```bash
python app.py
```

The API will be available at `http://localhost:5000`

### Frontend Setup

The frontend is served by the Flask backend. Once the backend is running, open:
```
http://localhost:5000
```

### Data Configuration

By default, the system reads from `data/conferences.csv`. To use a different data source:

1. Set the `CONFERENCE_DATA_PATH` environment variable:
```bash
# Local file
export CONFERENCE_DATA_PATH=/path/to/your/conferences.csv

# OneDrive URL
export CONFERENCE_DATA_PATH=https://your-onedrive-link-to-csv
```

2. Restart the Flask server

### CSV Format

```csv
conference_name,track_name,workshop_name,paper_submission_date,abstract_deadline,intimation_date
ICSE 2025,Main Track,,2024-10-15,2024-10-08,2025-02-15
ICSE 2025,,Workshop on AI,2024-12-01,2024-11-20,2025-03-15
```

- `conference_name`: Name of the conference
- `track_name`: Track name (optional)
- `workshop_name`: Workshop name (optional)
- `paper_submission_date`: Paper submission deadline (YYYY-MM-DD)
- `abstract_deadline`: Abstract deadline (optional, YYYY-MM-DD)
- `intimation_date`: Notification date (YYYY-MM-DD)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/conferences` | GET | List all conferences with tracks |
| `/api/deadlines` | GET | Get all deadlines for timeline |
| `/api/conferences/{name}/tracks` | GET | Get tracks for a conference |
| `/api/workshops` | POST | Add a new workshop |
| `/api/health` | GET | Health check |

## Future Development

The `scraper.py` module is ready for implementation to automatically scrape conference websites. Planned features:
- Web scraping for conference deadline extraction
- Scheduled updates
- Multi-source data aggregation

## License

MIT License