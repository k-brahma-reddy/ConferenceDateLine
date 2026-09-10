"""
Flask API for conference deadline tracking.
"""
import os
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from data_loader import DataLoader

# Get the absolute path to the frontend directory
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))

app = Flask(__name__, static_folder=frontend_dir, static_url_path='')
CORS(app)

# Initialize data loader - can be configured via environment variable
DATA_PATH = os.environ.get('CONFERENCE_DATA_PATH', None)
loader = DataLoader(DATA_PATH)


@app.route('/')
def index():
    """Serve the frontend index.html."""
    return send_from_directory(frontend_dir, 'index.html')


@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files from the frontend directory."""
    return send_from_directory(frontend_dir, filename)


@app.route('/api/conferences', methods=['GET'])
def get_conferences():
    """Get list of all conferences with their tracks."""
    conferences = loader.get_conferences()
    return jsonify([c.to_dict() for c in conferences])


@app.route('/api/deadlines', methods=['GET'])
def get_deadlines():
    """Get all deadlines for timeline display."""
    deadlines = loader.get_deadlines_for_timeline()
    return jsonify(deadlines)


@app.route('/api/conferences/<conference_name>/tracks', methods=['GET'])
def get_tracks(conference_name):
    """Get tracks for a specific conference."""
    conferences = loader.get_conferences()
    for conf in conferences:
        if conf.name == conference_name:
            return jsonify(conf.tracks)
    return jsonify({"error": "Conference not found"}), 404


@app.route('/api/workshops', methods=['POST'])
def add_workshop():
    """Add a new workshop entry."""
    data = request.json
    
    required_fields = ['conference_name', 'paper_submission_date', 'intimation_date']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    try:
        deadline = loader.add_workshop(
            conference_name=data['conference_name'],
            track_name=data.get('track_name', ''),
            workshop_name=data.get('workshop_name', ''),
            paper_submission_date=data['paper_submission_date'],
            abstract_deadline=data.get('abstract_deadline'),
            intimation_date=data['intimation_date'],
        )
        return jsonify(deadline.to_dict()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/conferences', methods=['POST'])
def add_conference():
    """Add a new conference entry."""
    data = request.json
    
    if 'name' not in data:
        return jsonify({"error": "Missing required field: name"}), 400
    
    try:
        conference = loader.add_conference(
            name=data['name'],
            year=data.get('year')
        )
        return jsonify(conference.to_dict()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)