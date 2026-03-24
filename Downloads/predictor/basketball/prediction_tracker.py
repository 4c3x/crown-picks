"""
Basketball Prediction Tracker
==============================
Tracks all predictions and actual results in JSON format.
Atomic writes prevent corruption.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import logging
import shutil

logger = logging.getLogger(__name__)


class PredictionTracker:
    """Tracks basketball predictions and results using JSON."""
    
    def __init__(self, json_path: str = None):
        if json_path is None:
            json_path = Path(__file__).parent.parent / "output" / "basketball_predictions.json"
        
        self.json_path = Path(json_path)
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Migrate from CSV if exists
        csv_path = self.json_path.with_suffix('.csv')
        if csv_path.exists() and not self.json_path.exists():
            self._migrate_from_csv(csv_path)
        
        if not self.json_path.exists():
            self._save([])
    
    def _load(self) -> List[Dict]:
        """Load predictions from JSON."""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logger.warning("Corrupted or missing JSON, starting fresh")
            return []
    
    def _save(self, predictions: List[Dict]):
        """Atomic write - write to temp file then rename (prevents corruption)."""
        tmp_path = self.json_path.with_suffix('.tmp')
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(predictions, f, indent=2, default=str)
        
        # Atomic rename
        if os.name == 'nt':
            # Windows: can't atomic rename over existing, so remove first
            if self.json_path.exists():
                self.json_path.unlink()
        shutil.move(str(tmp_path), str(self.json_path))
    
    def _migrate_from_csv(self, csv_path: Path):
        """One-time migration from CSV to JSON."""
        import csv
        predictions = []
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    predictions.append(dict(row))
            self._save(predictions)
            logger.info(f"Migrated {len(predictions)} predictions from CSV to JSON")
        except Exception as e:
            logger.warning(f"CSV migration failed: {e}")
            self._save([])
    
    def log_prediction(self, 
                      game_id: int,
                      game_date: str,
                      fixture: str,
                      home_team: str,
                      away_team: str,
                      predictions_list: List[Dict],
                      is_crown: bool = False):
        """Log predictions for a game."""
        now = datetime.now(timezone.utc).isoformat()
        all_preds = self._load()
        
        for pred in predictions_list:
            market = pred.get("market", "")
            
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
            
            all_preds.append({
                "prediction_date": now,
                "game_date": game_date,
                "game_id": str(game_id),
                "fixture": fixture,
                "home_team": home_team,
                "away_team": away_team,
                "market": market,
                "prediction": pred.get("prediction", ""),
                "line": pred.get("line", ""),
                "expected_total": expected_value,
                "expected_home": expected_home,
                "expected_away": expected_away,
                "our_probability": pred.get("our_probability", ""),
                "confidence": pred.get("confidence_score", ""),
                "confidence_tier": pred.get("confidence_tier", ""),
                "is_crown": str(is_crown),
                "final_total": "",
                "home_score": "",
                "away_score": "",
                "result": "",
                "margin": "",
                "updated_date": ""
            })
        
        self._save(all_preds)
        logger.info(f"Logged {len(predictions_list)} predictions for {fixture}")
    
    def update_results(self, basketball_api):
        """Check pending predictions and update final scores."""
        all_preds = self._load()
        if not all_preds:
            return 0
        
        updated_count = 0
        now = datetime.now(timezone.utc)
        
        for pred in all_preds:
            if pred.get("final_total"):
                continue
            
            game_id = pred.get("game_id", "")
            game_date_str = pred.get("game_date", "")
            
            try:
                game_date = datetime.fromisoformat(game_date_str.replace('Z', '+00:00'))
            except:
                continue
            
            if (now - game_date).total_seconds() < 14400:
                continue
            
            try:
                result = basketball_api.get_game_by_id(int(game_id), bypass_cache=True)
                if not result:
                    continue
                
                status = result.get("status", {}).get("short", "")
                if status not in ["FT", "AOT"]:
                    continue
                
                scores = result.get("scores", {})
                home_score = scores.get("home", {}).get("total")
                away_score = scores.get("away", {}).get("total")
                
                if home_score is None or away_score is None:
                    continue
                
                total_score = home_score + away_score
                pred["final_total"] = str(total_score)
                pred["home_score"] = str(home_score)
                pred["away_score"] = str(away_score)
                
                market = pred.get("market", "")
                prediction = pred.get("prediction", "")
                line = float(pred.get("line", 0)) if pred.get("line") else 0
                
                correct = False
                margin = 0
                if "TOTAL" in market:
                    margin = total_score - line
                    if "OVER" in prediction and total_score > line:
                        correct = True
                    elif "UNDER" in prediction and total_score < line:
                        correct = True
                elif pred.get("home_team", "") in market:
                    margin = home_score - line
                    if "OVER" in prediction and home_score > line:
                        correct = True
                    elif "UNDER" in prediction and home_score < line:
                        correct = True
                elif pred.get("away_team", "") in market:
                    margin = away_score - line
                    if "OVER" in prediction and away_score > line:
                        correct = True
                    elif "UNDER" in prediction and away_score < line:
                        correct = True
                
                pred["result"] = "WIN" if correct else "LOSS"
                pred["margin"] = f"{margin:+.1f}"
                pred["updated_date"] = now.isoformat()
                updated_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to update game {game_id}: {e}")
                continue
        
        if updated_count > 0:
            self._save(all_preds)
            logger.info(f"Updated {updated_count} game results")
        
        return updated_count
    
    def get_all(self) -> List[Dict]:
        """Get all predictions."""
        return self._load()
    
    def get_stats(self, market_filter: str = None) -> Dict:
        """Get accuracy statistics."""
        preds = self._load()
        stats = {"total": 0, "wins": 0, "losses": 0, "pending": 0}
        
        for p in preds:
            if market_filter and market_filter not in p.get("market", ""):
                continue
            result = p.get("result", "")
            if result == "WIN":
                stats["wins"] += 1
                stats["total"] += 1
            elif result == "LOSS":
                stats["losses"] += 1
                stats["total"] += 1
            else:
                stats["pending"] += 1
        
        stats["accuracy"] = (stats["wins"] / stats["total"] * 100) if stats["total"] > 0 else 0
        return stats


prediction_tracker = PredictionTracker()
