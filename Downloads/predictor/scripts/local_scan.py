"""
Local Scan Script - Run this on your machine daily
===================================================
Generates predictions and saves them to CSV files.
Then commit and push the CSV files - Render will serve them.

NO API CALLS ON RENDER = NO TIMEOUTS!
"""

from datetime import datetime, timezone
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from basketball.api_client import basketball_api
from basketball.predictor import basketball_predictor
from basketball.prediction_tracker import prediction_tracker
import csv

def scan_and_save():
    """Scan games locally and save to CSV."""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    print(f"🔍 Scanning basketball games for {today}... - local_scan.py:25")
    print("This may take a few minutes due to API rate limits... - local_scan.py:26")
    
    # Get all games
    games = basketball_api.get_games(date=today)
    if not games:
        print("❌ No games found for today - local_scan.py:31")
        return
    
    print(f"📊 Found {len(games)} games. Analyzing... - local_scan.py:34")
    
    # Total points predictions
    total_predictions = []
    for game in games:
        try:
            prediction = basketball_predictor.predict_total_points(game)
            if prediction and prediction.get("probability", 0) >= 0.80:
                total_predictions.append(prediction)
                print(f"✓ {prediction['fixture']}: {prediction['prediction']} ({prediction['probability']:.1%}) - local_scan.py:43")
        except Exception as e:
            print(f"✗ Error: {e} - local_scan.py:45")
            continue
    
    # Sort and take top 2
    total_predictions.sort(key=lambda x: x.get("probability", 0), reverse=True)
    top_2 = total_predictions[:2]
    
    # Save to CSV  
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    
    csv_file = output_dir / "daily_picks.csv"
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        if top_2:
            writer = csv.DictWriter(f, fieldnames=top_2[0].keys())
            writer.writeheader()
            writer.writerows(top_2)
    
    print(f"\n✅ Saved {len(top_2)} predictions to {csv_file} - local_scan.py:64")
    print("\n📤 Now run: - local_scan.py:65")
    print("git add output/daily_picks.csv - local_scan.py:66")
    print("git commit m 'Update daily picks' - local_scan.py:67")
    print("git push origin main - local_scan.py:68")
    print("\nRender will autodeploy the new picks! - local_scan.py:69")

if __name__ == "__main__":
    scan_and_save()
