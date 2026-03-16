"""
Football Prediction Tracker
============================
Tracks all football predictions and actual results in CSV format.
Automatically updates final scores after games complete.
"""

import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class FootballPredictionTracker:
    """Tracks football predictions and results."""
    
    def __init__(self, csv_path: str = None):
        if csv_path is None:
            csv_path = Path(__file__).parent.parent / "output" / "football_predictions.csv"
        
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
            "fixture_id",
            "fixture",
            "home_team",
            "away_team",
            "market",
            "prediction",
            "line",
            "expected_home_goals",
            "expected_away_goals",
            "our_probability",
            "bookmaker_probability",
            "edge",
            "confidence_tier",
            "final_home_goals",
            "final_away_goals",
            "result",
            "updated_date",
            "failure_reason",
            "improvement_plan"
        ]
        
        with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
        
        logger.info(f"Created football prediction tracker CSV at {self.csv_path}")
    
    def log_prediction(self, 
                      fixture_id: int,
                      game_date: str,
                      fixture: str,
                      home_team: str,
                      away_team: str,
                      market: str,
                      prediction: str,
                      line: str,
                      expected_home: float,
                      expected_away: float,
                      our_probability: float,
                      bookmaker_probability: float,
                      edge: float,
                      confidence_tier: str):
        """
        Log a single football prediction.
        
        Args:
            fixture_id: Unique fixture ID
            game_date: Game date/time
            fixture: Full fixture name
            home_team: Home team name
            away_team: Away team name
            market: Market type (e.g., "BTTS", "Over 2.5")
            prediction: The prediction (e.g., "YES", "OVER")
            line: The line/odds
            expected_home: Expected home goals
            expected_away: Expected away goals
            our_probability: Our calculated probability
            bookmaker_probability: Bookmaker's implied probability
            edge: Our edge percentage
            confidence_tier: Confidence level
        """
        now = datetime.now(timezone.utc).isoformat()
        
        row = [
            now,                        # prediction_date
            game_date,                  # game_date
            fixture_id,                 # fixture_id
            fixture,                    # fixture
            home_team,                  # home_team
            away_team,                  # away_team
            market,                     # market
            prediction,                 # prediction
            line,                       # line
            round(expected_home, 2),    # expected_home_goals
            round(expected_away, 2),    # expected_away_goals
            f"{our_probability:.1%}",   # our_probability
            f"{bookmaker_probability:.1%}",  # bookmaker_probability
            f"{edge:.1%}",              # edge
            confidence_tier,            # confidence_tier
            "",                         # final_home_goals (empty until updated)
            "",                         # final_away_goals (empty until updated)
            "",                         # result (empty until updated)
            "",                         # updated_date (empty until updated)
            "",                         # failure_reason (empty until updated)
            ""                          # improvement_plan (empty until updated)
        ]
        
        # Append to CSV
        with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(row)
        
        logger.info(f"Logged prediction for {fixture}: {market} {prediction}")
    
    def update_results(self, football_api):
        """
        Check all pending predictions and update final scores.
        
        Args:
            football_api: Football API client to fetch results
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
        
        # Update rows that don't have final scores yet
        for i, row in enumerate(rows):
            # Skip if already has final score
            if row[15]:  # final_home_goals column
                continue
            
            fixture_id = row[2]
            game_date_str = row[1]
            
            # Parse game date
            try:
                game_date = datetime.fromisoformat(game_date_str.replace('Z', '+00:00'))
            except:
                continue
            
            # Only check games that should have finished (at least 3 hours old)
            if (now - game_date).total_seconds() < 10800:  # 3 hours
                continue
            
            # Fetch game result
            try:
                result = football_api.get_fixture_by_id(int(fixture_id))
                if not result:
                    continue
                
                # Check if game is finished
                status = result.get("fixture", {}).get("status", {}).get("short", "")
                if status not in ["FT", "AET", "PEN"]:  # Finished, After Extra Time, Penalties
                    continue
                
                # Extract final scores
                goals = result.get("goals", {})
                home_goals = goals.get("home")
                away_goals = goals.get("away")
                
                if home_goals is None or away_goals is None:
                    continue
                
                # Update the row
                row[15] = str(home_goals)    # final_home_goals
                row[16] = str(away_goals)    # final_away_goals
                
                # Determine if prediction was correct
                market = row[6]
                prediction = row[7]
                
                correct = False
                
                if "BTTS" in market:
                    btts_occurred = home_goals > 0 and away_goals > 0
                    if (prediction == "YES" and btts_occurred) or (prediction == "NO" and not btts_occurred):
                        correct = True
                
                elif "Over" in market or "Under" in market:
                    line_value = float(row[8].split()[-1])
                    total_goals = home_goals + away_goals
                    if "Over" in prediction and total_goals > line_value:
                        correct = True
                    elif "Under" in prediction and total_goals < line_value:
                        correct = True
                
                elif "Home Win" in market or "Draw" in market or "Away Win" in market:
                    if home_goals > away_goals and "Home" in prediction:
                        correct = True
                    elif home_goals == away_goals and "Draw" in prediction:
                        correct = True
                    elif away_goals > home_goals and "Away" in prediction:
                        correct = True
                
                row[17] = "✅ WIN" if correct else "❌ LOSS"  # result
                row[18] = now.isoformat()                    # updated_date
                
                # Analyze failure and create improvement plan
                if not correct:
                    failure_analysis = self._analyze_failure(
                        market=market,
                        prediction=prediction,
                        expected_home=float(row[9]),
                        expected_away=float(row[10]),
                        actual_home=home_goals,
                        actual_away=away_goals,
                        home_team=row[4],
                        away_team=row[5],
                        edge=row[13]
                    )
                    row[19] = failure_analysis["reason"]
                    row[20] = failure_analysis["improvement_plan"]
                else:
                    row[19] = ""
                    row[20] = ""
                
                updated_count += 1
                logger.info(f"Updated result for fixture {fixture_id}: {row[3]} - {row[17]}")
                
            except Exception as e:
                logger.warning(f"Failed to update fixture {fixture_id}: {e}")
                continue
        
        # Write back to CSV
        with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
        
        if updated_count > 0:
            logger.info(f"Updated {updated_count} fixture results")
        
        return updated_count
    
    def _analyze_failure(self, market: str, prediction: str, expected_home: float,
                        expected_away: float, actual_home: int, actual_away: int,
                        home_team: str, away_team: str, edge: str) -> Dict[str, str]:
        """
        Analyze why a football prediction failed and create an improvement plan.
        
        Returns:
            Dict with "reason" and "improvement_plan" keys
        """
        reason_parts = []
        improvements = []
        
        # Calculate goal errors
        home_error = abs(expected_home - actual_home)
        away_error = abs(expected_away - actual_away)
        total_error = home_error + away_error
        
        reason_parts.append(f"Expected {expected_home:.1f}-{expected_away:.1f}, actual was {actual_home}-{actual_away}")
        
        # Analyze specific markets
        if "BTTS" in market:
            expected_btts = expected_home >= 0.7 and expected_away >= 0.7
            actual_btts = actual_home > 0 and actual_away > 0
            
            if "YES" in prediction and not actual_btts:
                if actual_home == 0:
                    reason_parts.append(f"{home_team} failed to score (expected {expected_home:.1f} goals)")
                    improvements.append(f"Review: {home_team}'s attacking form was overestimated")
                    improvements.append(f"Check: {away_team}'s defensive strength and home fortress factor")
                if actual_away == 0:
                    reason_parts.append(f"{away_team} failed to score (expected {expected_away:.1f} goals)")
                    improvements.append(f"Review: {away_team}'s away scoring ability was overestimated")
                    improvements.append(f"Check: {home_team}'s defensive solidity at home")
            
            elif "NO" in prediction and actual_btts:
                reason_parts.append("Both teams scored despite low xG predictions")
                improvements.append("Factor in: Match context (derby, relegation battle) can inflate goals")
                improvements.append("Recalibrate: Clean sheet probabilities may be too optimistic")
        
        elif "Over" in market or "Under" in market:
            # Extract line value
            line_str = market.split()[-1]
            try:
                line = float(line_str)
                total_actual = actual_home + actual_away
                total_expected = expected_home + expected_away
                
                if "Over" in prediction and total_actual <= line:
                    shortfall = line - total_actual
                    reason_parts.append(f"Predicted Over {line} but only {total_actual} goals scored (shortfall: {shortfall})")
                    
                    if total_expected - line < 0.3:
                        improvements.append(f"Avoid: Over {line} predictions with edge <0.3 goals too risky")
                    
                    if home_error > 1.0 or away_error > 1.0:
                        improvements.append("Poisson model miscalibration: Review lambda calculations")
                        improvements.append("Check: Were injuries/suspensions properly accounted for?")
                    
                elif "Under" in prediction and total_actual > line:
                    excess = total_actual - line
                    reason_parts.append(f"Predicted Under {line} but {total_actual} goals scored (excess: {excess})")
                    
                    if line - total_expected < 0.3:
                        improvements.append(f"Avoid: Under {line} predictions with edge <0.3 goals too risky")
                    
                    improvements.append("Underestimated: Attacking potential or game flow factors")
            except:
                pass
        
        elif "Win" in market or "Draw" in market:
            result = "draw" if actual_home == actual_away else ("home_win" if actual_home > actual_away else "away_win")
            
            if "Home" in prediction and result != "home_win":
                reason_parts.append(f"{home_team} failed to win (drew or lost)")
                improvements.append(f"Overestimated: {home_team}'s home advantage or form")
                improvements.append(f"Underestimated: {away_team}'s away performance")
            
            elif "Draw" in prediction and result != "draw":
                reason_parts.append("Match didn't end in draw despite close xG")
                improvements.append("Review: Draw predictions need very tight xG margins (within 0.2)")
            
            elif "Away" in prediction and result != "away_win":
                reason_parts.append(f"{away_team} failed to win away")
                improvements.append(f"Overestimated: {away_team}'s away form")
                improvements.append(f"Home advantage factor may be stronger than calculated")
        
        # Check edge quality
        try:
            edge_val = float(edge.strip('%')) / 100
            if edge_val < 0.05:
                improvements.append("CRITICAL: Edge was <5% - only bet with 8%+ edge minimum")
        except:
            pass
        
        # Check magnitude of errors
        if total_error > 3.0:
            reason_parts.append("MAJOR MISCALCULATION: Total error >3 goals")
            improvements.append("Urgent: Review entire Poisson model and all input factors")
            improvements.append("Check: Were there red cards, early goals that changed game dynamics?")
        elif total_error > 2.0:
            improvements.append("Significant error: Review recent form data and xG calculations")
        
        # General improvements if none specific
        if not improvements:
            improvements.append("Review: Match-specific factors (weather, motivation, tactical setup)")
            improvements.append("Validate: Check if lineup news or late changes affected the game")
        
        # Combine into final strings
        reason = "; ".join(reason_parts)
        improvement_plan = " | ".join(improvements)
        
        return {
            "reason": reason,
            "improvement_plan": improvement_plan
        }
    
    def get_stats(self) -> Dict:
        """Get prediction statistics."""
        if not self.csv_path.exists():
            return {}
        
        with open(self.csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = list(reader)
        
        total = len(rows)
        completed = sum(1 for r in rows if r[15])  # Has final_home_goals
        wins = sum(1 for r in rows if r[17] == "✅ WIN")
        losses = sum(1 for r in rows if r[17] == "❌ LOSS")
        pending = total - completed
        
        accuracy = (wins / completed * 100) if completed > 0 else 0
        
        return {
            "total_predictions": total,
            "completed": completed,
            "pending": pending,
            "wins": wins,
            "losses": losses,
            "accuracy": round(accuracy, 1)
        }
    
    def print_stats(self):
        """Print prediction statistics."""
        stats = self.get_stats()
        
        print("\n" + "=" * 70)
        print("⚽ FOOTBALL PREDICTION TRACKER STATISTICS")
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
football_prediction_tracker = FootballPredictionTracker()
