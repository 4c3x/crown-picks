"""
Simplified App for Render Free Tier
====================================
Just serves pre-computed predictions from CSV files.
No API calls, no timeouts, instant responses!

Run local_scan.py on your machine to generate predictions.
"""

from flask import Flask, render_template, jsonify, send_from_directory
import csv
from pathlib import Path

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/api/daily-picks')
def get_daily_picks():
    """Serve pre-computed predictions from CSV (instant response)."""
    csv_file = Path(__file__).parent / "output" / "daily_picks.csv"
    
    if not csv_file.exists():
        return jsonify({
            "message": "No picks available yet. Run local_scan.py to generate predictions.",
            "picks": []
        })
    
    picks = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        picks = list(reader)
    
    return jsonify({
        "picks": picks,
        "count": len(picks)
    })

@app.route('/api/team-picks')
def get_team_picks():
    """Serve team predictions from CSV."""
    csv_file = Path(__file__).parent / "output" / "team_predictions.csv"
    
    if not csv_file.exists():
        return jsonify({"picks": []})
    
    picks = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("result") == "":  # Only pending predictions
                picks.append(row)
    
    return jsonify({"picks": picks[:5]})  # Top 5

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
