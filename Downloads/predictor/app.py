"""
👑 CROWN PICKS - Elite Basketball Predictor v7
================================================
PHILOSOPHY CHANGE: Quality over quantity.

Scans ALL basketball games worldwide for a given day.
Returns ONLY 2 games with the highest probability (minimum 80%).

If nothing meets the threshold → NO PICKS. We don't force bad bets.
"""

from flask import Flask, render_template, request, jsonify, Response, send_from_directory
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys
import logging
import json
import csv
import threading

sys.path.insert(0, str(Path(__file__).parent))

from basketball.api_client import basketball_api
from basketball.predictor import basketball_predictor
from basketball.prediction_tracker import prediction_tracker
from basketball.scan_manager import scan_manager

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route('/')
def index():
    """Home page."""
    return render_template('index.html')


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files (PWA manifest, service worker, icons)."""
    return send_from_directory('static', filename)


@app.route('/api/daily-picks-stream')
def get_daily_picks_stream():
    """
    DEPRECATED: This endpoint is disabled. Use /api/scan/start instead for background scans.
    """
    return jsonify({
        "error": "SSE streaming is disabled. Use /api/scan/start for background scans that persist even when browser closes.",
        "migration": {
            "old_endpoint": "/api/daily-picks-stream",
            "new_endpoint": "/api/scan/start",
            "method": "POST",
            "body": {"type": "total", "date": "YYYY-MM-DD"}
        }
    }), 410  # 410 Gone


@app.route('/api/results')
def get_results():
    """Get all prediction results with statistics."""
    try:
        import csv
        from pathlib import Path
        
        csv_path = Path('output/basketball_predictions.csv')
        
        if not csv_path.exists():
            return jsonify({
                "overall": {"total": 0, "wins": 0, "losses": 0, "accuracy": 0, "pending": 0},
                "crown_stats": {"total": 0, "wins": 0, "losses": 0, "accuracy": 0},
                "all_predictions": []
            })
        
        # Read CSV
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Filter to TOTAL POINTS predictions
        total_preds = [r for r in rows if 'TOTAL POINTS' in r.get('market', '')]
        completed = [r for r in total_preds if r.get('result')]
        pending = [r for r in total_preds if not r.get('result')]
        
        # Crown picks stats
        crown_preds = [r for r in completed if r.get('is_crown', '').lower() == 'true']
        crown_wins = sum(1 for r in crown_preds if 'WIN' in r['result'])
        
        # Calculate overall stats
        wins = sum(1 for r in completed if 'WIN' in r['result'])
        losses = len(completed) - wins
        accuracy = (wins / len(completed) * 100) if completed else 0
        
        crown_accuracy = (crown_wins / len(crown_preds) * 100) if crown_preds else 0
        
        # By prediction type
        over_preds = [r for r in completed if r['prediction'] == 'OVER']
        under_preds = [r for r in completed if r['prediction'] == 'UNDER']
        
        over_wins = sum(1 for r in over_preds if 'WIN' in r['result'])
        under_wins = sum(1 for r in under_preds if 'WIN' in r['result'])
        
        # All predictions with full details
        all_predictions = []
        for r in total_preds:
            all_predictions.append({
                'fixture': r.get('fixture', ''),
                'game_date': r.get('game_date', ''),
                'prediction': r.get('prediction', ''),
                'line': r.get('line', ''),
                'confidence_tier': r.get('confidence_tier', ''),
                'confidence': r.get('confidence', ''),
                'expected_total': r.get('expected_total', ''),
                'home_score': r.get('home_score', ''),
                'away_score': r.get('away_score', ''),
                'final_total': r.get('final_total', ''),
                'result': r.get('result', 'PENDING'),
                'margin': r.get('margin', ''),
                'is_crown': r.get('is_crown', 'False').lower() == 'true'
            })
        
        # Reverse so newest first
        all_predictions.reverse()
        
        return jsonify({
            'overall': {
                'total': len(completed),
                'wins': wins,
                'losses': losses,
                'accuracy': accuracy,
                'pending': len(pending)
            },
            'crown_stats': {
                'total': len(crown_preds),
                'wins': crown_wins,
                'losses': len(crown_preds) - crown_wins,
                'accuracy': crown_accuracy
            },
            'by_type': {
                'over': {
                    'wins': over_wins,
                    'total': len(over_preds),
                    'accuracy': (over_wins / len(over_preds) * 100) if over_preds else 0
                },
                'under': {
                    'wins': under_wins,
                    'total': len(under_preds),
                    'accuracy': (under_wins / len(under_preds) * 100) if under_preds else 0
                }
            },
            'all_predictions': all_predictions
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/update-results', methods=['POST'])
def update_results():
    """Manually trigger results update."""
    try:
        updated_count = prediction_tracker.update_results(basketball_api)
        # Also update team predictions
        updated_team = update_team_predictions_results()
        stats = prediction_tracker.get_stats()
        return jsonify({
            "success": True,
            "message": f"Updated {updated_count} total game(s), {updated_team} team prediction(s)",
            "updated_count": updated_count + updated_team,
            "stats": stats
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ============================================================
# NEW MARKET: TEAM POINTS (Home/Away Over/Under)
# ============================================================

TEAM_PREDICTIONS_CSV = Path(__file__).parent / "output" / "team_predictions.csv"

def ensure_team_csv():
    """Ensure team predictions CSV exists with headers."""
    if not TEAM_PREDICTIONS_CSV.exists():
        TEAM_PREDICTIONS_CSV.parent.mkdir(parents=True, exist_ok=True)
        with open(TEAM_PREDICTIONS_CSV, 'w', newline='', encoding='utf-8') as f:
            f.write("prediction_date,game_date,game_id,fixture,team_name,team_type,market,prediction,line,expected,our_probability,confidence,confidence_tier,is_crown,final_score,result,margin,updated_date,bookmaker_odds,bookmaker\n")

def log_team_prediction(pred_data):
    """Log a team prediction to CSV with validation."""
    ensure_team_csv()
    
    # Validate and normalize data
    confidence = pred_data.get('confidence', '')
    confidence_tier = pred_data.get('confidence_tier', '')
    
    # Skip corrupted entries
    if 'SKIP' in str(confidence_tier):
        return
    
    # Normalize confidence to HIGH/MEDIUM/LOW if it's a number
    if isinstance(confidence, (int, float)):
        if confidence >= 85:
            confidence = 'HIGH'
        elif confidence >= 70:
            confidence = 'MEDIUM'
        else:
            confidence = 'LOW'
    
    # Normalize market to "Team Points"
    market = "Team Points"
    
    with open(TEAM_PREDICTIONS_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            pred_data.get('prediction_date', ''),
            pred_data.get('game_date', ''),
            pred_data.get('game_id', ''),
            pred_data.get('fixture', ''),
            pred_data.get('team_name', ''),
            pred_data.get('team_type', ''),
            market,
            pred_data.get('prediction', ''),
            pred_data.get('line', ''),
            pred_data.get('expected', ''),
            pred_data.get('our_probability', ''),
            confidence,
            pred_data.get('confidence_tier', 'MEDIUM'),
            pred_data.get('is_crown', False),
            '',  # final_score
            '',  # result
            '',  # margin
            '',  # updated_date
            pred_data.get('bookmaker_odds', ''),  # bookmaker_odds
            pred_data.get('bookmaker', '')  # bookmaker
        ])

def update_team_predictions_results():
    """Update team prediction results from completed games."""
    if not TEAM_PREDICTIONS_CSV.exists():
        return 0
    
    updated = 0
    rows = []
    
    with open(TEAM_PREDICTIONS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip if already has result (check both formats)
            result = row.get('result', '')
            if result and ('WIN' in result or 'LOSS' in result):
                rows.append(row)
                continue
            
            # Try to get game result
            try:
                game_id = row.get('game_id', '')
                # Skip RECOVERED or PENDING entries - they're already complete or don't have valid IDs
                if not game_id or game_id in ['RECOVERED', 'PENDING', '']:
                    rows.append(row)
                    continue
                
                # Fetch game data - BYPASS CACHE to get fresh status
                response = basketball_api.request("games", {"id": game_id}, cache_hours=0)
                if not response or not response.get("response"):
                    rows.append(row)
                    continue
                
                game = response["response"][0]
                status = game.get("status", {}).get("short", "")
                
                if status not in ["FT", "AOT"]:  # Not finished
                    rows.append(row)
                    continue
                
                scores = game.get("scores", {})
                home_score = scores.get("home", {}).get("total")
                away_score = scores.get("away", {}).get("total")
                
                if home_score is None or away_score is None:
                    rows.append(row)
                    continue
                
                # Determine which score to use
                team_type = row.get('team_type', '')
                if team_type == 'HOME':
                    final_score = float(home_score)
                else:
                    final_score = float(away_score)
                
                line = float(row.get('line', 0))
                prediction = row.get('prediction', '')
                
                # Calculate result
                if prediction == 'OVER':
                    won = final_score > line
                else:  # UNDER
                    won = final_score < line
                
                margin = final_score - line
                
                row['final_score'] = final_score
                row['result'] = '✅ WIN' if won else '❌ LOSS'
                row['margin'] = f"{margin:+.1f}"
                row['updated_date'] = datetime.now(timezone.utc).isoformat()
                updated += 1
                
            except Exception as e:
                pass
            
            rows.append(row)
    
    # Write back - always write to ensure consistent state
    with open(TEAM_PREDICTIONS_CSV, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['prediction_date', 'game_date', 'game_id', 'fixture', 'team_name', 'team_type', 
                     'market', 'prediction', 'line', 'expected', 'our_probability', 'confidence', 
                     'confidence_tier', 'is_crown', 'final_score', 'result', 'margin', 'updated_date']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    return updated


@app.route('/api/team-picks-stream')
def get_team_picks_stream():
    """
    DEPRECATED: This endpoint is disabled. Use /api/scan/start instead for background scans.
    """
    return jsonify({
        "error": "SSE streaming is disabled. Use /api/scan/start for background scans that persist even when browser closes.",
        "migration": {
            "old_endpoint": "/api/team-picks-stream",
            "new_endpoint": "/api/scan/start",
            "method": "POST",
            "body": {"type": "team", "date": "YYYY-MM-DD"}
        }
    }), 410  # 410 Gone



def get_team_prediction_stats():
    """Get accuracy stats for team predictions."""
    if not TEAM_PREDICTIONS_CSV.exists():
        return {"total": 0, "wins": 0, "losses": 0, "accuracy": 0}
    
    stats = {"total": 0, "wins": 0, "losses": 0, "pending": 0, "home_wins": 0, "home_total": 0, "away_wins": 0, "away_total": 0}
    
    with open(TEAM_PREDICTIONS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            result = row.get('result', '')
            team_type = row.get('team_type', '')
            
            if result == '✅ WIN':
                stats["wins"] += 1
                stats["total"] += 1
                if team_type == 'HOME':
                    stats["home_wins"] += 1
                    stats["home_total"] += 1
                else:
                    stats["away_wins"] += 1
                    stats["away_total"] += 1
            elif result == '❌ LOSS':
                stats["losses"] += 1
                stats["total"] += 1
                if team_type == 'HOME':
                    stats["home_total"] += 1
                else:
                    stats["away_total"] += 1
            else:
                stats["pending"] += 1
    
    stats["accuracy"] = (stats["wins"] / stats["total"] * 100) if stats["total"] > 0 else 0
    stats["home_accuracy"] = (stats["home_wins"] / stats["home_total"] * 100) if stats["home_total"] > 0 else 0
    stats["away_accuracy"] = (stats["away_wins"] / stats["away_total"] * 100) if stats["away_total"] > 0 else 0
    
    return stats


@app.route('/api/team-results')
def get_team_results():
    """Get team prediction results and stats."""
    try:
        stats = get_team_prediction_stats()
        
        predictions = []
        if TEAM_PREDICTIONS_CSV.exists():
            with open(TEAM_PREDICTIONS_CSV, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    predictions.append(row)
        
        predictions.reverse()  # Newest first
        
        return jsonify({
            "stats": stats,
            "predictions": predictions[:50]  # Last 50
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================================================================
# BACKGROUND SCAN ENDPOINTS (Persist even when browser closes)
# =========================================================================

@app.route('/api/scan/start', methods=['POST'])
def start_background_scan():
    """Start a background scan that persists even if browser closes."""
    try:
        data = request.get_json() or {}
        scan_type = data.get('type', 'total')  # 'total' or 'team'
        selected_date = data.get('date', datetime.now(timezone.utc).strftime('%Y-%m-%d'))
        
        # Start the appropriate scan type
        if scan_type == 'team':
            scan_id = scan_manager.start_scan('team', selected_date, run_team_scan_background, selected_date)
        else:
            scan_id = scan_manager.start_scan('total', selected_date, run_total_scan_background, selected_date)
        
        return jsonify({
            'success': True,
            'scan_id': scan_id,
            'message': f'Background scan started for {selected_date}'
        })
    except Exception as e:
        logger.error(f"Error starting scan: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/scan/status/<scan_id>')
def get_scan_status(scan_id):
    """Get status of a background scan."""
    status = scan_manager.get_scan_status(scan_id)
    if not status:
        return jsonify({'error': 'Scan not found'}), 404
    return jsonify(status)


@app.route('/api/scan/list')
def list_scans():
    """List all scans."""
    scans = scan_manager.get_all_scans()
    return jsonify({'scans': scans})


@app.route('/api/scan/delete/<scan_id>', methods=['DELETE'])
def delete_scan(scan_id):
    """Delete a scan."""
    success = scan_manager.delete_scan(scan_id)
    if success:
        return jsonify({'success': True})
    return jsonify({'error': 'Scan not found'}), 404


def run_total_scan_background(selected_date, progress_callback=None):
    """Run total points scan in background (simplified version)."""
    try:
        if progress_callback:
            progress_callback(0, 0, None, f"🔄 Starting scan for {selected_date}...")
        
        # Update previous predictions
        updated_count = prediction_tracker.update_results(basketball_api)
        if progress_callback and updated_count > 0:
            progress_callback(0, 0, None, f"✅ Updated {updated_count} previous predictions")
        
        current_time = datetime.now(timezone.utc)
        
        # Fetch all games
        if progress_callback:
            progress_callback(0, 0, None, f"🌍 Fetching all basketball games for {selected_date}...")
        
        response = basketball_api.request("games", {"date": selected_date}, cache_hours=1)
        
        if not response or not response.get("response"):
            return {
                "success": True,
                "date": selected_date,
                "crown_picks": [],
                "runner_ups": [],
                "stats": {"games_scanned": 0, "valid_predictions": 0}
            }
        
        raw_games = response["response"]
        scan_date_obj = datetime.strptime(selected_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        is_future = scan_date_obj.date() >= current_time.date()
        
        # Filter games
        all_games = []
        for game in raw_games:
            try:
                game_status = game.get("status", {}).get("short", "")
                if is_future and game_status != "NS":
                    continue
                    
                league_id = game.get("league", {}).get("id", 0)
                league_name = game.get("league", {}).get("name", "")
                country = game.get("country", {}).get("name", "")
                
                year = scan_date_obj.year
                month = scan_date_obj.month
                season = game.get("league", {}).get("season", "")
                if not season:
                    season = f"{year-1}-{year}" if month <= 6 else f"{year}-{year+1}"
                
                all_games.append({
                    "game": game,
                    "league_id": league_id,
                    "league_name": league_name,
                    "country": country,
                    "season": str(season)
                })
            except:
                continue
        
        total_games = len(all_games)
        if progress_callback:
            progress_callback(0, total_games, None, f"📊 Found {total_games} eligible games")
        
        # Analyze each game
        all_predictions = []
        
        for idx, game_data in enumerate(all_games):
            try:
                game = game_data["game"]
                home_team = game["teams"]["home"]
                away_team = game["teams"]["away"]
                fixture = f"{home_team['name']} vs {away_team['name']}"
                
                if progress_callback:
                    progress_callback(
                        idx + 1, 
                        total_games,
                        {'fixture': fixture, 'league': game_data['league_name']},
                        f"[{idx+1}/{total_games}] {fixture}"
                    )
                
                # Get prediction (use existing predictor logic)
                league_id = game_data["league_id"]
                season = game_data["season"]
                
                home_stats = basketball_api.get_team_statistics(home_team["id"], league_id, season) or {}
                away_stats = basketball_api.get_team_statistics(away_team["id"], league_id, season) or {}
                home_recent = basketball_api.get_team_games(home_team["id"], season, last=10) or []
                away_recent = basketball_api.get_team_games(away_team["id"], season, last=10) or []
                h2h = basketball_api.get_head_to_head(home_team["id"], away_team["id"], last=10) or []
                odds = basketball_api.get_odds(game["id"]) or {}
                
                game_date = datetime.fromisoformat(game["date"].replace("Z", "+00:00"))
                
                game_info = {
                    "home_name": home_team["name"],
                    "away_name": away_team["name"],
                    "home_id": home_team["id"],
                    "away_id": away_team["id"],
                    "game_date": game_date,
                    "league_id": league_id,
                }
                
                # Get total line from odds
                if odds.get("totals"):
                    for line_str in odds["totals"].keys():
                        try:
                            line_val = float(line_str.replace("Over ", "").replace("Under ", ""))
                            game_info["total_line"] = line_val
                            break
                        except:
                            pass
                
                prediction = basketball_predictor.predict_game(
                    game_info, home_stats, away_stats, home_recent, away_recent, h2h
                )
                
                if prediction and prediction.get("probability", 0) >= 0.80:
                    prediction["game_id"] = game["id"]
                    prediction["fixture"] = fixture
                    prediction["league"] = game_data["league_name"]
                    prediction["country"] = game_data["country"]
                    prediction["odds_data"] = odds
                    all_predictions.append(prediction)
                    
            except Exception as e:
                logger.error(f"Error analyzing game: {e}")
                continue
        
        # Sort by probability and get top 2
        all_predictions.sort(key=lambda x: x.get("probability", 0), reverse=True)
        crown_picks = all_predictions[:2]
        runner_ups = all_predictions[2:5] if len(all_predictions) > 2 else []
        
        # Log predictions
        for pred in crown_picks:
            prediction_tracker.log_prediction(pred, is_crown=True)
        
        if progress_callback:
            progress_callback(total_games, total_games, None, f"✅ Scan complete! Found {len(crown_picks)} crown picks")
        
        return {
            "success": True,
            "date": selected_date,
            "crown_picks": crown_picks,
            "runner_ups": runner_ups,
            "stats": {
                "games_scanned": total_games,
                "valid_predictions": len(all_predictions),
                "crown_picks": len(crown_picks)
            }
        }
        
    except Exception as e:
        logger.error(f"Background scan error: {e}", exc_info=True)
        raise


def run_team_scan_background(selected_date, progress_callback=None):
    """Run team points scan in background (simplified version)."""
    # Similar to run_total_scan_background but for team predictions
    # For now, return placeholder - implement similar logic
    if progress_callback:
        progress_callback(0, 0, None, "Team scan not yet implemented for background mode")
    
    return {
        "success": True,
        "date": selected_date,
        "team_picks": [],
        "stats": {"games_scanned": 0, "team_predictions": 0}
    }


if __name__ == '__main__':
    import socket
    
    # Get local IP address
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = "localhost"
    
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║           👑 CROWN PICKS - Elite Basketball Predictor v7 👑          ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  All leagues. All games. Top 2 picks. Min 80% probability.           ║
║                                                                      ║
║  🌐 Server Access:                                                   ║
║     • Local:   http://localhost:5000                                ║
║     • Network: http://{}:5000                               ║
║                                                                      ║
║  📱 Android App: See ANDROID_INSTALL.md for mobile setup             ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
    """.format(local_ip))
    
    app.run(host='0.0.0.0', debug=True, port=5000)
