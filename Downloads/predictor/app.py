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

sys.path.insert(0, str(Path(__file__).parent))

from basketball.api_client import basketball_api
from basketball.predictor import basketball_predictor
from basketball.prediction_tracker import prediction_tracker

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
    STREAMING ENDPOINT v7: Scan ALL basketball games worldwide.
    No league restrictions. Returns only 2 elite picks (min 80% probability).
    """
    selected_date = request.args.get('date', datetime.now(timezone.utc).strftime('%Y-%m-%d'))
    
    def generate():
        try:
            def send_event(event_type, data):
                return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
            
            # Update previous predictions
            yield send_event("log", {"message": "🔄 Checking previous predictions...", "type": "info"})
            updated_count = prediction_tracker.update_results(basketball_api)
            if updated_count > 0:
                yield send_event("log", {"message": f"✅ Updated {updated_count} previous predictions", "type": "success"})
            
            current_time = datetime.now(timezone.utc)
            
            # Parse selected date
            try:
                scan_date = datetime.strptime(selected_date, '%Y-%m-%d')
            except:
                scan_date = datetime.now()
            
            year = scan_date.year
            month = scan_date.month
            
            # ============================================================
            # STEP 1: FETCH ALL BASKETBALL GAMES WORLDWIDE (single API call)
            # ============================================================
            yield send_event("phase", {"phase": "fetching", "message": "Fetching ALL basketball games worldwide..."})
            yield send_event("log", {"message": f"🌍 Scanning ALL basketball games for {selected_date}...", "type": "info"})
            
            response = basketball_api.request("games", {"date": selected_date}, cache_hours=1)
            
            if not response or not response.get("response"):
                yield send_event("log", {"message": f"⚠️ No games found for {selected_date}", "type": "warning"})
                yield send_event("complete", {
                    "success": True, "date": selected_date,
                    "crown_picks": [], "runner_ups": [],
                    "stats": {"games_scanned": 0, "valid_predictions": 0, "previous_updated": updated_count}
                })
                return
            
            raw_games = response["response"]
            
            # Filter: Only not-started games (or all for past dates for backtesting)
            scan_date_obj = datetime.strptime(selected_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            is_future = scan_date_obj.date() >= current_time.date()
            
            all_games = []
            leagues_found = set()
            
            for game in raw_games:
                try:
                    league_name = game.get("league", {}).get("name", "")
                    league_id = game.get("league", {}).get("id", 0)
                    country = game.get("country", {}).get("name", "")
                    
                    game_status = game.get("status", {}).get("short", "")
                    
                    if is_future:
                        if game_status != "NS":
                            continue
                        game_time = datetime.fromisoformat(game["date"].replace("Z", "+00:00"))
                        if game_time <= current_time + timedelta(minutes=30):
                            continue
                    else:
                        # Past date - include all for backtesting
                        pass
                    
                    # Determine season dynamically from the game data
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
                    leagues_found.add(f"{league_name} ({country})")
                    
                except Exception:
                    continue
            
            total_games = len(all_games)
            yield send_event("log", {"message": f"📊 Found {len(raw_games)} total games, {total_games} eligible", "type": "info"})
            yield send_event("log", {"message": f"🏀 Leagues: {', '.join(sorted(leagues_found))}", "type": "dim"})
            yield send_event("total", {"total": total_games})
            
            if total_games == 0:
                yield send_event("log", {"message": f"⚠️ No eligible games for {selected_date}", "type": "warning"})
                yield send_event("complete", {
                    "success": True, "date": selected_date,
                    "crown_picks": [], "runner_ups": [],
                    "stats": {"games_scanned": 0, "valid_predictions": 0, "previous_updated": updated_count}
                })
                return
            
            # ============================================================
            # STEP 2: ANALYZE EVERY GAME
            # ============================================================
            yield send_event("phase", {"phase": "analyzing", "message": "Deep analysis on every game..."})
            yield send_event("log", {"message": "🔬 Running deep analysis (stats, form, H2H, odds)...", "type": "info"})
            
            all_predictions = []
            
            for idx, game_data in enumerate(all_games):
                try:
                    game = game_data["game"]
                    league_id = game_data["league_id"]
                    season = game_data["season"]
                    
                    home_team = game["teams"]["home"]
                    away_team = game["teams"]["away"]
                    fixture = f"{home_team['name']} vs {away_team['name']}"
                    
                    progress = int((idx + 1) / total_games * 100)
                    yield send_event("progress", {
                        "current": idx + 1, "total": total_games,
                        "percent": progress, "fixture": fixture,
                        "league": game_data["league_name"]
                    })
                    yield send_event("log", {"message": f"   [{idx+1}/{total_games}] {fixture} ({game_data['league_name']})", "type": "dim"})
                    
                    game_date = datetime.fromisoformat(game["date"].replace("Z", "+00:00"))
                    
                    # Fetch all data for this game
                    home_stats = basketball_api.get_team_statistics(home_team["id"], league_id, season) or {}
                    away_stats = basketball_api.get_team_statistics(away_team["id"], league_id, season) or {}
                    home_recent = basketball_api.get_team_games(home_team["id"], season, last=10) or []
                    away_recent = basketball_api.get_team_games(away_team["id"], season, last=10) or []
                    h2h = basketball_api.get_head_to_head(home_team["id"], away_team["id"], last=10) or []
                    odds = basketball_api.get_odds(game["id"]) or {}
                    
                    # Build game info
                    game_info = {
                        "home_name": home_team["name"],
                        "away_name": away_team["name"],
                        "home_id": home_team["id"],
                        "away_id": away_team["id"],
                        "game_date": game_date,
                        "league_id": league_id,
                    }
                    
                    # Add total line from odds
                    if odds.get("totals"):
                        for line_str, odds_list in odds["totals"].items():
                            if "Over" in line_str or "Under" in line_str:
                                try:
                                    line_val = float(line_str.replace("Over ", "").replace("Under ", ""))
                                    game_info["total_line"] = line_val
                                    break
                                except:
                                    pass
                    
                    # Run predictions
                    predictions = basketball_predictor.analyze_game(
                        home_stats=home_stats,
                        away_stats=away_stats,
                        home_recent=home_recent,
                        away_recent=away_recent,
                        h2h=h2h,
                        league_id=league_id,
                        game_info=game_info
                    )
                    
                    # ====== QUALITY GATES (v7.1) ======
                    # 1. REQUIRE ODDS - If bookmakers don't care, neither should we
                    has_market_line = bool(game_info.get("total_line", 0))
                    if not has_market_line:
                        yield send_event("log", {"message": f"   ↳ SKIP: No betting line available", "type": "dim"})
                        continue
                    
                    # 2. REQUIRE MINIMUM DATA - At least 5 games per team
                    min_games_required = 5
                    if len(home_recent) < min_games_required or len(away_recent) < min_games_required:
                        yield send_event("log", {"message": f"   ↳ SKIP: Insufficient data ({len(home_recent)}/{len(away_recent)} games)", "type": "dim"})
                        continue
                    
                    # Get TOTAL POINTS prediction only
                    total_pred = next((p for p in predictions if "TOTAL" in p.market and "POINTS" in p.market), None)
                    
                    if total_pred and "⛔ SKIP" not in total_pred.confidence_tier:
                        all_predictions.append({
                            "game_id": game["id"],
                            "fixture": fixture,
                            "home": home_team["name"],
                            "away": away_team["name"],
                            "time": game["date"],
                            "league": game_data["league_name"],
                            "prediction": total_pred.prediction,
                            "line": total_pred.line,
                            "expected": total_pred.expected_total,
                            "edge": abs(total_pred.expected_total - total_pred.line) if total_pred.expected_total else 0,
                            "probability": total_pred.our_probability,
                            "confidence_score": total_pred.confidence_score,
                            "confidence_tier": total_pred.confidence_tier,
                            "key_factors": total_pred.key_factors[:3],
                            "warnings": total_pred.warnings,
                            "data_quality": {
                                "home_games": len(home_recent),
                                "away_games": len(away_recent),
                                "h2h_games": len(h2h),
                                "has_odds": True  # Always true now since we require it
                            }
                        })
                        
                except Exception as e:
                    yield send_event("log", {"message": f"   ↳ Error: {str(e)}", "type": "error"})
                    continue
            
            yield send_event("log", {"message": f"✅ Generated {len(all_predictions)} valid predictions", "type": "success"})
            
            # ============================================================
            # STEP 3: FILTER & RANK - Only 80%+ probability, top 2
            # ============================================================
            yield send_event("phase", {"phase": "ranking", "message": "Filtering elite picks (80%+ probability)..."})
            
            # Sort by probability (highest first)
            all_predictions.sort(key=lambda p: p["probability"], reverse=True)
            
            # Filter to 80%+ probability only
            elite_predictions = [p for p in all_predictions if p["probability"] >= 0.80]
            
            yield send_event("log", {"message": f"🎯 {len(elite_predictions)} games meet 80%+ probability threshold", "type": "info"})
            
            # STEP 4: Pick the best games
            if len(elite_predictions) >= 2:
                # Ideal: 2 crown picks from 80%+ pool
                crown_picks = elite_predictions[:2]
                runner_ups = elite_predictions[2:4] if len(elite_predictions) > 2 else []
                threshold_met = True
            else:
                # Fallback: nothing hit 80%, show top 3 best available
                yield send_event("log", {"message": "⚠️ No games hit 80% — showing top 3 highest probability instead", "type": "warning"})
                crown_picks = all_predictions[:3]
                runner_ups = []
                threshold_met = False
            
            if len(crown_picks) == 0:
                yield send_event("log", {"message": "⚠️ No predictions could be generated today.", "type": "warning"})
                yield send_event("complete", {
                    "success": True, "date": selected_date,
                    "crown_picks": [], "runner_ups": [],
                    "stats": {"games_scanned": total_games, "valid_predictions": len(all_predictions), "elite_predictions": 0, "previous_updated": updated_count},
                    "accuracy": prediction_tracker.get_stats()
                })
                return
            
            for i, pick in enumerate(crown_picks):
                pick["rank"] = i + 1
                pick["is_crown"] = True
                pick["threshold_met"] = threshold_met
                label = "👑" if threshold_met else "🔶"
                yield send_event("log", {"message": f"{label} Pick #{i+1}: {pick['fixture']} ({pick['league']}) - {pick['prediction']} {pick['line']} @ {pick['probability']:.1%}", "type": "success"})
            
            for i, pick in enumerate(runner_ups):
                pick["rank"] = len(crown_picks) + i + 1
                pick["is_crown"] = False
                pick["threshold_met"] = True
            
            # Log to CSV
            yield send_event("log", {"message": "💾 Saving predictions to tracker...", "type": "info"})
            for pick in crown_picks + runner_ups:
                prediction_tracker.log_prediction(
                    game_id=pick["game_id"],
                    game_date=pick["time"],
                    fixture=pick["fixture"],
                    home_team=pick["home"],
                    away_team=pick["away"],
                    predictions=[{
                        "market": "TOTAL POINTS",
                        "prediction": pick["prediction"],
                        "line": pick["line"],
                        "expected": pick["expected"],
                        "our_probability": f"{pick['probability']:.1%}",
                        "confidence_score": pick["confidence_score"],
                        "confidence_tier": pick["confidence_tier"],
                        "key_factors": pick["key_factors"],
                        "warnings": pick["warnings"]
                    }],
                    is_crown=pick["is_crown"]
                )
            
            stats = prediction_tracker.get_stats()
            
            msg = "✅ Complete! Your Crown Picks are ready." if threshold_met else "✅ Complete! Showing best available (none hit 80%)."
            yield send_event("log", {"message": msg, "type": "success"})
            yield send_event("complete", {
                "success": True,
                "date": selected_date,
                "crown_picks": crown_picks,
                "runner_ups": runner_ups,
                "threshold_met": threshold_met,
                "stats": {
                    "games_scanned": total_games,
                    "valid_predictions": len(all_predictions),
                    "elite_predictions": len(elite_predictions),
                    "previous_updated": updated_count
                },
                "accuracy": stats
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield send_event("error", {"message": str(e)})
    
    return Response(generate(), mimetype='text/event-stream')


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
    TEAM POINTS MARKET: Scan all games, predict Home/Away Over/Under.
    Returns top 5 best team point predictions.
    """
    selected_date = request.args.get('date', datetime.now(timezone.utc).strftime('%Y-%m-%d'))
    
    def generate():
        try:
            def send_event(event_type, data):
                return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
            
            # Update previous team predictions
            yield send_event("log", {"message": "🔄 Checking previous team predictions...", "type": "info"})
            updated_count = update_team_predictions_results()
            if updated_count > 0:
                yield send_event("log", {"message": f"✅ Updated {updated_count} previous team predictions", "type": "success"})
            
            current_time = datetime.now(timezone.utc)
            
            # Parse selected date
            try:
                scan_date = datetime.strptime(selected_date, '%Y-%m-%d')
            except:
                scan_date = datetime.now()
            
            year = scan_date.year
            month = scan_date.month
            
            # ============================================================
            # STEP 1: FETCH ALL BASKETBALL GAMES
            # ============================================================
            yield send_event("phase", {"phase": "fetching", "message": "Fetching all basketball games..."})
            yield send_event("log", {"message": f"🏀 Scanning games for {selected_date}...", "type": "info"})
            
            response = basketball_api.request("games", {"date": selected_date}, cache_hours=1)
            
            if not response or not response.get("response"):
                yield send_event("log", {"message": f"⚠️ No games found for {selected_date}", "type": "warning"})
                yield send_event("complete", {"success": True, "date": selected_date, "team_picks": [], "stats": {}})
                return
            
            raw_games = response["response"]
            
            # Filter eligible games
            scan_date_obj = datetime.strptime(selected_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            is_future = scan_date_obj.date() >= current_time.date()
            
            all_games = []
            
            for game in raw_games:
                try:
                    league_name = game.get("league", {}).get("name", "")
                    league_id = game.get("league", {}).get("id", 0)
                    country = game.get("country", {}).get("name", "")
                    game_status = game.get("status", {}).get("short", "")
                    
                    if is_future:
                        if game_status != "NS":
                            continue
                        game_time = datetime.fromisoformat(game["date"].replace("Z", "+00:00"))
                        if game_time <= current_time + timedelta(minutes=30):
                            continue
                    
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
            yield send_event("log", {"message": f"📊 Found {total_games} eligible games", "type": "info"})
            yield send_event("total", {"total": total_games})
            
            if total_games == 0:
                yield send_event("complete", {"success": True, "date": selected_date, "team_picks": [], "stats": {}})
                return
            
            # ============================================================
            # STEP 2: ANALYZE EACH GAME FOR TEAM PREDICTIONS
            # ============================================================
            yield send_event("phase", {"phase": "analyzing", "message": "Analyzing team scoring..."})
            
            all_team_predictions = []
            
            for idx, game_data in enumerate(all_games):
                try:
                    game = game_data["game"]
                    league_id = game_data["league_id"]
                    season = game_data["season"]
                    
                    home_team = game["teams"]["home"]
                    away_team = game["teams"]["away"]
                    fixture = f"{home_team['name']} vs {away_team['name']}"
                    
                    progress = int((idx + 1) / total_games * 100)
                    yield send_event("progress", {"current": idx + 1, "total": total_games, "percent": progress, "fixture": fixture})
                    
                    game_date = datetime.fromisoformat(game["date"].replace("Z", "+00:00"))
                    
                    # Fetch data
                    home_stats = basketball_api.get_team_statistics(home_team["id"], league_id, season) or {}
                    away_stats = basketball_api.get_team_statistics(away_team["id"], league_id, season) or {}
                    home_recent = basketball_api.get_team_games(home_team["id"], season, last=10) or []
                    away_recent = basketball_api.get_team_games(away_team["id"], season, last=10) or []
                    h2h = basketball_api.get_head_to_head(home_team["id"], away_team["id"], last=10) or []
                    odds = basketball_api.get_odds(game["id"]) or {}
                    
                    # Quality gates
                    if len(home_recent) < 5 or len(away_recent) < 5:
                        continue
                    
                    # Build game info
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
                        for line_str, odds_list in odds["totals"].items():
                            if "Over" in line_str or "Under" in line_str:
                                try:
                                    line_val = float(line_str.replace("Over ", "").replace("Under ", ""))
                                    game_info["total_line"] = line_val
                                    break
                                except:
                                    pass
                    
                    if not game_info.get("total_line"):
                        continue
                    
                    # Run predictions
                    predictions = basketball_predictor.analyze_game(
                        home_stats=home_stats,
                        away_stats=away_stats,
                        home_recent=home_recent,
                        away_recent=away_recent,
                        h2h=h2h,
                        league_id=league_id,
                        game_info=game_info
                    )
                    
                    # Extract odds data
                    bookmaker_odds = ""
                    bookmaker_name = ""
                    if odds.get("totals"):
                        for line_str, odds_list in odds["totals"].items():
                            if odds_list and len(odds_list) > 0:
                                first_odd = odds_list[0]
                                bookmaker_name = first_odd.get("bookmaker", "")
                                over_odd = first_odd.get("odd", "")
                                if over_odd:
                                    bookmaker_odds = str(over_odd)
                                break
                    
                    # Get HOME and AWAY team predictions
                    for pred in predictions:
                        if "POINTS" in pred.market and "TOTAL" not in pred.market:
                            team_name = pred.market.replace(" POINTS", "")
                            is_home = team_name == home_team["name"]
                            
                            # Skip if confidence tier is SKIP
                            if "SKIP" in pred.confidence_tier:
                                continue
                            
                            expected_val = pred.expected_home if is_home else pred.expected_away
                            
                            all_team_predictions.append({
                                "game_id": game["id"],
                                "fixture": fixture,
                                "home": home_team["name"],
                                "away": away_team["name"],
                                "time": game["date"],
                                "league": game_data["league_name"],
                                "team_name": team_name,
                                "team_type": "HOME" if is_home else "AWAY",
                                "prediction": pred.prediction,
                                "line": pred.line,
                                "expected": expected_val,
                                "probability": pred.our_probability,
                                "confidence_score": pred.confidence_score,
                                "confidence_tier": pred.confidence_tier,
                                "key_factors": pred.key_factors[:3],
                                "bookmaker_odds": bookmaker_odds,
                                "bookmaker": bookmaker_name
                            })
                    
                except Exception as e:
                    continue
            
            yield send_event("log", {"message": f"✅ Generated {len(all_team_predictions)} team predictions", "type": "success"})
            
            # ============================================================
            # STEP 3: QUALITY FILTER AND SELECT TOP 5
            # ============================================================
            yield send_event("phase", {"phase": "ranking", "message": "Filtering and selecting top 5..."})
            
            # Quality gates: minimum 70% probability
            quality_predictions = [p for p in all_team_predictions if p["probability"] >= 0.70]
            
            yield send_event("log", {"message": f"✓ {len(quality_predictions)} predictions meet 70% threshold", "type": "info"})
            
            # One team per fixture - keep only the best prediction from each game
            fixture_best = {}
            for pred in quality_predictions:
                game_id = pred["game_id"]
                if game_id not in fixture_best or pred["probability"] > fixture_best[game_id]["probability"]:
                    fixture_best[game_id] = pred
            
            unique_fixtures = list(fixture_best.values())
            yield send_event("log", {"message": f"✓ {len(unique_fixtures)} unique fixtures (one team per game)", "type": "info"})
            
            # Sort by probability * confidence_score for best overall picks
            unique_fixtures.sort(key=lambda p: p["probability"] * (p["confidence_score"] / 100), reverse=True)
            
            # Take top 5
            top_picks = unique_fixtures[:5]
            
            for i, pick in enumerate(top_picks):
                pick["rank"] = i + 1
                pick["is_crown"] = True
                emoji = "🏠" if pick["team_type"] == "HOME" else "✈️"
                yield send_event("log", {
                    "message": f"{emoji} #{i+1}: {pick['team_name']} {pick['prediction']} {pick['line']} @ {pick['probability']:.1%} ({pick['fixture']})",
                    "type": "success"
                })
            
            # Log to CSV
            yield send_event("log", {"message": "💾 Saving team predictions...", "type": "info"})
            for pick in top_picks:
                # Normalize confidence
                conf_score = pick["confidence_score"]
                if conf_score >= 85:
                    confidence = "HIGH"
                elif conf_score >= 70:
                    confidence = "MEDIUM"
                else:
                    confidence = "LOW"
                
                log_team_prediction({
                    "prediction_date": datetime.now(timezone.utc).isoformat(),
                    "game_date": pick["time"],
                    "game_id": pick["game_id"],
                    "fixture": pick["fixture"],
                    "team_name": pick["team_name"],
                    "team_type": pick["team_type"],
                    "prediction": pick["prediction"],
                    "line": pick["line"],
                    "expected": pick["expected"],
                    "our_probability": f"{pick['probability']:.1%}",
                    "confidence": confidence,
                    "confidence_tier": pick["confidence_tier"],
                    "is_crown": True,
                    "bookmaker_odds": pick.get("bookmaker_odds", ""),
                    "bookmaker": pick.get("bookmaker", "")
                })
            
            # Get team stats
            team_stats = get_team_prediction_stats()
            
            yield send_event("complete", {
                "success": True,
                "date": selected_date,
                "team_picks": top_picks,
                "stats": {
                    "games_scanned": total_games,
                    "team_predictions": len(all_team_predictions),
                    "top_picks": len(top_picks)
                },
                "accuracy": team_stats
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield send_event("error", {"message": str(e)})
    
    return Response(generate(), mimetype='text/event-stream')


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
