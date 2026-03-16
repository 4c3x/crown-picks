"""
Basketball Prediction Tracker
==============================
Tracks all predictions and actual results in CSV format.
Automatically updates final scores after games complete.
"""

import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class PredictionTracker:
    """Tracks basketball predictions and results."""
    
    def __init__(self, csv_path: str = None):
        if csv_path is None:
            csv_path = Path(__file__).parent.parent / "output" / "basketball_predictions.csv"
        
        self.csv_path = Path(csv_path)
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create CSV with headers if it doesn't exist
        if not self.csv_path.exists():
            self._create_csv()
    
    def _create_csv(self):
        """Create CSV file with headers."""
        headers = [
            "prediction_date",
            "game_date",
            "game_id",
            "fixture",
            "home_team",
            "away_team",
            "market",
            "prediction",
            "line",
            "expected_total",
            "expected_home",
            "expected_away",
            "our_probability",
            "confidence",
            "confidence_tier",
            "is_crown",
            "final_total",
            "home_score",
            "away_score",
            "result",
            "margin",
            "updated_date"
        ]
        
        with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
        
        logger.info(f"Created prediction tracker CSV at {self.csv_path}")
    
    def log_prediction(self, 
                      game_id: int,
                      game_date: str,
                      fixture: str,
                      home_team: str,
                      away_team: str,
                      predictions: List[Dict],
                      is_crown: bool = False):
        """
        Log predictions for a game.
        
        Args:
            game_id: Unique game ID
            game_date: Game date/time
            fixture: Full fixture name
            home_team: Home team name
            away_team: Away team name
            predictions: List of prediction dicts
            is_crown: Whether this is a Crown pick (top 3)
        """
        now = datetime.now(timezone.utc).isoformat()
        
        rows = []
        for pred in predictions:
            market = pred.get("market", "")
            
            # Determine expected values based on market
            if "TOTAL" in market:
                expected_value = pred.get("expected", 0)
                expected_home = ""
                expected_away = ""
            elif home_team in market:
                expected_value = ""
                expected_home = pred.get("expected", 0)
                expected_away = ""
            elif away_team in market:
                expected_value = ""
                expected_home = ""
                expected_away = pred.get("expected", 0)
            else:
                expected_value = ""
                expected_home = ""
                expected_away = ""
            
            row = [
                now,                                    # prediction_date
                game_date,                              # game_date
                game_id,                                # game_id
                fixture,                                # fixture
                home_team,                              # home_team
                away_team,                              # away_team
                market,                                 # market
                pred.get("prediction", ""),             # prediction
                pred.get("line", ""),                   # line
                expected_value,                         # expected_total
                expected_home,                          # expected_home
                expected_away,                          # expected_away
                pred.get("our_probability", ""),        # our_probability
                pred.get("confidence_score", ""),       # confidence
                pred.get("confidence_tier", ""),        # confidence_tier
                str(is_crown),                          # is_crown
                "",                                     # final_total (empty until updated)
                "",                                     # home_score (empty until updated)
                "",                                     # away_score (empty until updated)
                "",                                     # result (empty until updated)
                "",                                     # margin (empty until updated)
                ""                                      # updated_date (empty until updated)
            ]
            rows.append(row)
        
        # Append to CSV
        with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        
        logger.info(f"Logged {len(rows)} predictions for {fixture}")
    
    def update_results(self, basketball_api):
        """
        Check all pending predictions and update final scores.
        
        Args:
            basketball_api: Basketball API client to fetch results
        """
        if not self.csv_path.exists():
            return
        
        # Read all rows
        rows = []
        with open(self.csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = list(reader)
        
        updated_count = 0
        now = datetime.now(timezone.utc)
        
        # Column indices for new structure:
        # 0: prediction_date, 1: game_date, 2: game_id, 3: fixture
        # 4: home_team, 5: away_team, 6: market, 7: prediction
        # 8: line, 9: expected_total, 10: expected_home, 11: expected_away
        # 12: our_probability, 13: confidence, 14: confidence_tier, 15: is_crown
        # 16: final_total, 17: home_score, 18: away_score, 19: result, 20: margin, 21: updated_date
        
        COL_FINAL_TOTAL = 16
        COL_HOME_SCORE = 17
        COL_AWAY_SCORE = 18
        COL_RESULT = 19
        COL_MARGIN = 20
        COL_UPDATED = 21
        
        # Update rows that don't have final scores yet
        for i, row in enumerate(rows):
            # Ensure row has enough columns
            while len(row) < 22:
                row.append("")
            
            # Skip if already has final score
            if row[COL_FINAL_TOTAL]:
                continue
            
            game_id = row[2]
            game_date_str = row[1]
            
            # Parse game date
            try:
                game_date = datetime.fromisoformat(game_date_str.replace('Z', '+00:00'))
            except:
                continue
            
            # Only check games that should have finished (at least 4 hours old)
            if (now - game_date).total_seconds() < 14400:  # 4 hours
                continue
            
            # Fetch game result - bypass cache to get fresh data
            try:
                result = basketball_api.get_game_by_id(int(game_id), bypass_cache=True)
                if not result:
                    continue
                
                # Check if game is finished
                status = result.get("status", {}).get("short", "")
                if status not in ["FT", "AOT"]:  # Finished or After Overtime
                    continue
                
                # Extract final scores
                scores = result.get("scores", {})
                home_score = scores.get("home", {}).get("total")
                away_score = scores.get("away", {}).get("total")
                
                if home_score is None or away_score is None:
                    continue
                
                total_score = home_score + away_score
                
                # Update the row
                row[COL_FINAL_TOTAL] = str(total_score)  # final_total
                row[COL_HOME_SCORE] = str(home_score)   # home_score
                row[COL_AWAY_SCORE] = str(away_score)   # away_score
                
                # Determine if prediction was correct
                market = row[6]
                prediction = row[7]
                line = float(row[8]) if row[8] else 0
                
                correct = False
                margin = 0
                if "TOTAL" in market:
                    margin = total_score - line
                    if "OVER" in prediction and total_score > line:
                        correct = True
                    elif "UNDER" in prediction and total_score < line:
                        correct = True
                elif row[4] in market:  # Home team market
                    margin = home_score - line
                    if "OVER" in prediction and home_score > line:
                        correct = True
                    elif "UNDER" in prediction and home_score < line:
                        correct = True
                elif row[5] in market:  # Away team market
                    margin = away_score - line
                    if "OVER" in prediction and away_score > line:
                        correct = True
                    elif "UNDER" in prediction and away_score < line:
                        correct = True
                
                row[COL_RESULT] = "✅ WIN" if correct else "❌ LOSS"
                row[COL_MARGIN] = f"{margin:+.1f}"
                row[COL_UPDATED] = now.isoformat()
                
                updated_count += 1
                logger.info(f"Updated result for game {game_id}: {row[3]} - {row[17]}")
                
            except Exception as e:
                logger.warning(f"Failed to update game {game_id}: {e}")
                continue
        
        # Write back to CSV
        with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
        
        if updated_count > 0:
            logger.info(f"Updated {updated_count} game results")
        
        return updated_count
    
    def _analyze_failure(self, market: str, prediction: str, line: float,
                        expected_total: Optional[float], expected_home: Optional[float],
                        expected_away: Optional[float], actual_total: int, actual_home: int,
                        actual_away: int, home_team: str, away_team: str) -> Dict[str, str]:
        """
        Analyze why a prediction failed and create an improvement plan.
        
        Returns:
            Dict with "reason" and "improvement_plan" keys
        """
        reason_parts = []
        improvements = []
        
        # Calculate the error magnitude
        if "TOTAL" in market:
            error = abs(expected_total - actual_total) if expected_total else 0
            direction = "higher" if actual_total > expected_total else "lower"
            
            reason_parts.append(f"Expected {expected_total:.1f} total points, actual was {actual_total} ({error:.1f} points {direction})")
            
            # Analyze why total was wrong
            if error > 15:
                reason_parts.append("MAJOR MISCALCULATION: Error >15 points")
                improvements.append("Critical: Review pace calculation formula and fatigue adjustments")
            elif error > 10:
                reason_parts.append("Significant error in total points projection")
                improvements.append("Review: Pace estimates may be off, check recent game averages")
            
            # Check if we underestimated scoring
            if actual_total > expected_total:
                if actual_home > (expected_home or 0) and actual_away > (expected_away or 0):
                    reason_parts.append("Both teams scored more than expected - likely underestimated pace or efficiency")
                    improvements.append("Adjust: Increase offensive efficiency factors, check if teams were well-rested")
                elif actual_home > (expected_home or 0):
                    reason_parts.append(f"{home_team} significantly outperformed expectations")
                    improvements.append(f"Research: Check {home_team}'s recent form and matchup advantages we missed")
                else:
                    reason_parts.append(f"{away_team} significantly outperformed expectations")
                    improvements.append(f"Research: Check {away_team}'s recent form and matchup advantages we missed")
            else:
                # Overestimated scoring
                reason_parts.append("Teams scored less than expected - may have overestimated pace or underestimated defense")
                improvements.append("Adjust: Review defensive ratings and pace-down factors")
        
        elif home_team in market:
            # Home team market
            error = abs(expected_home - actual_home) if expected_home else 0
            reason_parts.append(f"Expected {home_team} to score {expected_home:.1f}, actual was {actual_home} ({error:.1f} points off)")
            
            if error > 8:
                reason_parts.append("Large error in team-specific prediction")
                improvements.append(f"Deep dive: Analyze {home_team}'s scoring patterns and defensive matchups")
        
        elif away_team in market:
            # Away team market
            error = abs(expected_away - actual_away) if expected_away else 0
            reason_parts.append(f"Expected {away_team} to score {expected_away:.1f}, actual was {actual_away} ({error:.1f} points off)")
            
            if error > 8:
                reason_parts.append("Large error in team-specific prediction")
                improvements.append(f"Deep dive: Analyze {away_team}'s scoring patterns and road performance")
        
        # Check prediction direction
        if "OVER" in prediction and "UNDER" in market:
            if expected_total:
                margin = expected_total - line
                reason_parts.append(f"Predicted OVER {line} with expected {expected_total:.1f} (edge of {margin:.1f})")
                if margin < 3:
                    improvements.append("Avoid: OVER predictions with <3 point edge are too risky")
        
        elif "UNDER" in prediction and "TOTAL" in market:
            if expected_total:
                margin = line - expected_total
                reason_parts.append(f"Predicted UNDER {line} with expected {expected_total:.1f} (edge of {margin:.1f})")
                if margin < 3:
                    improvements.append("Avoid: UNDER predictions with <3 point edge are too risky")
        
        # General improvements
        if not improvements:
            improvements.append("Review: Re-examine all input factors (pace, efficiency, rest, injuries)")
            improvements.append("Validate: Check if external factors (injuries, lineup changes) affected the game")
        
        # Combine into final strings
        reason = "; ".join(reason_parts)
        improvement_plan = " | ".join(improvements)
        
        return {
            "reason": reason,
            "improvement_plan": improvement_plan
        }
    
    def get_stats(self) -> Dict:
        """Get prediction statistics for TOTAL POINTS market only."""
        if not self.csv_path.exists():
            return {}
        
        with open(self.csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = list(reader)
        
        # Column indices for new structure:
        # 6: market, 15: is_crown, 16: final_total, 19: result
        
        # Filter to TOTAL POINTS market only
        total_points_rows = [r for r in rows if len(r) > 6 and 'TOTAL POINTS' in r[6]]
        
        total = len(total_points_rows)
        completed = sum(1 for r in total_points_rows if len(r) > 16 and r[16])  # Has final_total
        wins = sum(1 for r in total_points_rows if len(r) > 19 and "WIN" in r[19])
        losses = sum(1 for r in total_points_rows if len(r) > 19 and "LOSS" in r[19])
        pending = total - completed
        
        # Crown stats
        crown_rows = [r for r in total_points_rows if len(r) > 15 and r[15].lower() == 'true']
        crown_completed = sum(1 for r in crown_rows if len(r) > 16 and r[16])
        crown_wins = sum(1 for r in crown_rows if len(r) > 19 and "WIN" in r[19])
        crown_losses = sum(1 for r in crown_rows if len(r) > 19 and "LOSS" in r[19])
        
        accuracy = (wins / completed * 100) if completed > 0 else 0
        crown_accuracy = (crown_wins / crown_completed * 100) if crown_completed > 0 else 0
        
        return {
            "total_predictions": total,
            "completed": completed,
            "pending": pending,
            "wins": wins,
            "losses": losses,
            "accuracy": round(accuracy, 1),
            "crown_total": len(crown_rows),
            "crown_completed": crown_completed,
            "crown_wins": crown_wins,
            "crown_losses": crown_losses,
            "crown_accuracy": round(crown_accuracy, 1)
        }
    
    def print_stats(self):
        """Print prediction statistics."""
        stats = self.get_stats()
        
        print("\n" + "=" * 70)
        print("📊 PREDICTION TRACKER STATISTICS")
        print("=" * 70)
        print(f"Total Predictions: {stats.get('total_predictions', 0)}")
        print(f"Completed Games: {stats.get('completed', 0)}")
        print(f"Pending Games: {stats.get('pending', 0)}")
        print(f"")
        print(f"Wins: {stats.get('wins', 0)} ✅")
        print(f"Losses: {stats.get('losses', 0)} ❌")
        print(f"Accuracy: {stats.get('accuracy', 0)}%")
        print("=" * 70)
        print(f"\n💾 CSV File: {self.csv_path}")


# Singleton instance
prediction_tracker = PredictionTracker()
