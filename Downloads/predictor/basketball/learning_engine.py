"""
Basketball Learning Engine
==========================
Self-learning system that analyzes past predictions and continuously improves.

This module:
1. Learns from actual results vs predictions
2. Calibrates confidence scores based on historical accuracy
3. Identifies which factors are most predictive
4. Adjusts prediction models based on performance
5. Filters out low-quality predictions
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class BasketballLearningEngine:
    """Self-learning engine that improves predictions over time."""
    
    def __init__(self, csv_path: str = None):
        if csv_path is None:
            csv_path = Path(__file__).parent.parent / "output" / "basketball_predictions.csv"
        
        self.csv_path = Path(csv_path)
        self.model_path = Path(__file__).parent.parent / "models" / "basketball_learned_params.json"
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Learned parameters
        self.learned_params = self._load_learned_params()
        
        # Minimum games needed before learning kicks in
        self.min_games_for_learning = 20
        
    def _load_learned_params(self) -> Dict:
        """Load previously learned parameters."""
        if self.model_path.exists():
            try:
                with open(self.model_path, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Default parameters (neutral - no learning yet)
        return {
            "version": "1.0",
            "last_updated": None,
            "total_games_analyzed": 0,
            
            # Confidence calibration (multipliers to adjust confidence scores)
            "confidence_calibration": {
                "total_points": 1.0,
                "team_points": 1.0,
            },
            
            # Factor importance (how much to weight each factor)
            "factor_weights": {
                "back_to_back": 1.0,
                "road_b2b": 1.0,
                "pace": 1.0,
                "recent_form": 1.0,
                "h2h": 1.0,
            },
            
            # Market-specific accuracy
            "market_accuracy": {
                "total_over": {"attempts": 0, "wins": 0, "accuracy": 0.0},
                "total_under": {"attempts": 0, "wins": 0, "accuracy": 0.0},
                "team_over": {"attempts": 0, "wins": 0, "accuracy": 0.0},
                "team_under": {"attempts": 0, "wins": 0, "accuracy": 0.0},
            },
            
            # Confidence tier performance
            "tier_performance": {
                "GOLD": {"attempts": 0, "wins": 0, "accuracy": 0.0},
                "SILVER": {"attempts": 0, "wins": 0, "accuracy": 0.0},
                "BRONZE": {"attempts": 0, "wins": 0, "accuracy": 0.0},
            },
            
            # Edge thresholds (minimum edge required for each confidence level)
            "edge_thresholds": {
                "GOLD": 0.15,    # 15% minimum edge for GOLD
                "SILVER": 0.10,  # 10% minimum edge for SILVER
                "BRONZE": 0.05,  # 5% minimum edge for BRONZE
            },
            
            # Prediction adjustments learned from results
            "adjustments": {
                "b2b_home_penalty": -4.0,  # Points to subtract for home back-to-back
                "b2b_road_penalty": -5.5,  # Points to subtract for road back-to-back
                "pace_multiplier": 1.0,     # Multiplier for pace calculations
                "form_weight": 1.0,         # How much to weight recent form
            }
        }
    
    def _save_learned_params(self):
        """Save learned parameters to disk."""
        self.learned_params["last_updated"] = datetime.now().isoformat()
        
        try:
            with open(self.model_path, 'w') as f:
                json.dump(self.learned_params, f, indent=2)
            logger.info(f"Saved learned parameters to {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to save learned parameters: {e}")
    
    def analyze_and_learn(self) -> Dict:
        """
        Analyze all completed predictions and update learned parameters.
        
        Returns:
            Dict with learning statistics
        """
        if not self.csv_path.exists():
            logger.warning(f"No CSV file found at {self.csv_path}")
            return {"status": "no_data"}
        
        # Load predictions
        df = pd.read_csv(self.csv_path)
        
        # Filter to completed games only
        completed = df[df['final_total'].notna()].copy()
        
        if len(completed) < self.min_games_for_learning:
            logger.info(f"Only {len(completed)} completed games. Need {self.min_games_for_learning} for learning.")
            return {
                "status": "insufficient_data",
                "completed_games": len(completed),
                "needed": self.min_games_for_learning
            }
        
        logger.info(f"Analyzing {len(completed)} completed games for learning...")
        
        # Update market accuracy
        self._analyze_market_accuracy(completed)
        
        # Update confidence tier performance
        self._analyze_tier_performance(completed)
        
        # Calibrate confidence scores
        self._calibrate_confidence(completed)
        
        # Analyze factor importance
        self._analyze_factors(completed)
        
        # Adjust prediction parameters
        self._optimize_adjustments(completed)
        
        # Update total games analyzed
        self.learned_params["total_games_analyzed"] = len(completed)
        
        # Save learned parameters
        self._save_learned_params()
        
        # Calculate overall stats
        total_wins = len(completed[completed['result'] == '✅ WIN'])
        overall_accuracy = (total_wins / len(completed) * 100) if len(completed) > 0 else 0
        
        return {
            "status": "success",
            "completed_games": len(completed),
            "overall_accuracy": round(overall_accuracy, 1),
            "market_accuracy": self.learned_params["market_accuracy"],
            "tier_performance": self.learned_params["tier_performance"],
            "adjustments": self.learned_params["adjustments"]
        }
    
    def _analyze_market_accuracy(self, df: pd.DataFrame):
        """Analyze accuracy by market type."""
        for market_type in ["total_over", "total_under", "team_over", "team_under"]:
            # Filter predictions
            if "total" in market_type:
                mask = df['market'].str.contains("TOTAL", na=False)
            else:
                mask = ~df['market'].str.contains("TOTAL", na=False)
            
            if "over" in market_type:
                mask &= df['prediction'].str.contains("OVER", na=False)
            else:
                mask &= df['prediction'].str.contains("UNDER", na=False)
            
            filtered = df[mask]
            
            if len(filtered) > 0:
                wins = len(filtered[filtered['result'] == '✅ WIN'])
                attempts = len(filtered)
                accuracy = (wins / attempts * 100) if attempts > 0 else 0
                
                self.learned_params["market_accuracy"][market_type] = {
                    "attempts": attempts,
                    "wins": wins,
                    "accuracy": round(accuracy, 1)
                }
    
    def _analyze_tier_performance(self, df: pd.DataFrame):
        """Analyze accuracy by confidence tier."""
        for tier in ["GOLD", "SILVER", "BRONZE"]:
            mask = df['confidence_tier'].str.contains(tier, na=False)
            filtered = df[mask]
            
            if len(filtered) > 0:
                wins = len(filtered[filtered['result'] == '✅ WIN'])
                attempts = len(filtered)
                accuracy = (wins / attempts * 100) if attempts > 0 else 0
                
                self.learned_params["tier_performance"][tier] = {
                    "attempts": attempts,
                    "wins": wins,
                    "accuracy": round(accuracy, 1)
                }
    
    def _calibrate_confidence(self, df: pd.DataFrame):
        """
        Calibrate confidence scores based on actual performance.
        
        If SILVER tier is performing like GOLD, increase its multiplier.
        If GOLD tier is underperforming, decrease its multiplier.
        """
        tier_perf = self.learned_params["tier_performance"]
        
        # Adjust confidence multipliers based on performance
        for tier, perf in tier_perf.items():
            if perf["attempts"] >= 10:  # Need at least 10 samples
                accuracy = perf["accuracy"]
                
                # Expected accuracy targets
                targets = {"GOLD": 75, "SILVER": 65, "BRONZE": 55}
                target = targets.get(tier, 60)
                
                # Calculate calibration factor
                # If performing above target, increase multiplier slightly
                # If performing below target, decrease multiplier
                if accuracy > target + 10:
                    # Performing much better than expected
                    calibration = 1.1
                elif accuracy > target:
                    # Performing slightly better
                    calibration = 1.05
                elif accuracy < target - 10:
                    # Performing much worse
                    calibration = 0.85
                elif accuracy < target:
                    # Performing slightly worse
                    calibration = 0.95
                else:
                    calibration = 1.0
                
                # Apply to market types
                self.learned_params["confidence_calibration"]["total_points"] = calibration
                self.learned_params["confidence_calibration"]["team_points"] = calibration
    
    def _analyze_factors(self, df: pd.DataFrame):
        """Analyze which factors are most predictive of success."""
        # This would require more detailed data about each prediction's factors
        # For now, we maintain the weights but could expand this with more data
        pass
    
    def _optimize_adjustments(self, df: pd.DataFrame):
        """
        Optimize prediction adjustments based on results.
        
        Analyzes games with back-to-backs and adjusts penalties if needed.
        """
        # Filter to total points predictions (easier to analyze)
        totals = df[df['market'].str.contains("TOTAL", na=False)].copy()
        
        if len(totals) < 10:
            return
        
        # Convert to numeric
        totals['expected_total'] = pd.to_numeric(totals['expected_total'], errors='coerce')
        totals['final_total'] = pd.to_numeric(totals['final_total'], errors='coerce')
        
        # Calculate prediction errors
        totals['error'] = totals['final_total'] - totals['expected_total']
        
        # Average error (positive means we're predicting too low, negative means too high)
        avg_error = totals['error'].mean()
        
        # If we're consistently off in one direction, adjust
        if abs(avg_error) > 2.0:  # More than 2 points off on average
            # Adjust pace multiplier
            current_pace = self.learned_params["adjustments"]["pace_multiplier"]
            
            if avg_error > 0:
                # We're predicting too low, increase pace multiplier
                new_pace = min(current_pace * 1.02, 1.15)  # Max 15% increase
            else:
                # We're predicting too high, decrease pace multiplier
                new_pace = max(current_pace * 0.98, 0.85)  # Max 15% decrease
            
            self.learned_params["adjustments"]["pace_multiplier"] = round(new_pace, 3)
            logger.info(f"Adjusted pace multiplier from {current_pace} to {new_pace} (avg error: {avg_error:.1f})")
    
    def should_show_prediction(self, prediction: Dict, market_type: str) -> Tuple[bool, str]:
        """
        Determine if a prediction meets quality standards.
        
        Args:
            prediction: Prediction dict with confidence_score, our_probability, etc.
            market_type: "total" or "team"
            
        Returns:
            (should_show, reason)
        """
        # Not enough data yet - use conservative defaults
        if self.learned_params["total_games_analyzed"] < self.min_games_for_learning:
            # Only show high confidence predictions
            if prediction.get("confidence_score", 0) >= 60:
                return True, "High confidence (no learning data yet)"
            return False, f"Low confidence ({prediction.get('confidence_score', 0)}/100) - need more data for learning"
        
        # Check historical performance of this tier
        tier = prediction.get("confidence_tier", "").replace("🥇 ", "").replace("🥈 ", "").replace("🥉 ", "").strip()
        
        if tier in self.learned_params["tier_performance"]:
            tier_perf = self.learned_params["tier_performance"][tier]
            
            # Don't show predictions from tiers with poor track record
            if tier_perf["attempts"] >= 10:  # Need sample size
                if tier_perf["accuracy"] < 50:  # Less than 50% accuracy
                    return False, f"{tier} tier has {tier_perf['accuracy']}% accuracy (below threshold)"
        
        # Check if edge is sufficient
        our_prob = prediction.get("our_probability", 0.5)
        line_prob = prediction.get("bookmaker_probability", 0.5)
        edge = our_prob - line_prob
        
        # Get minimum edge threshold for this tier
        min_edge = self.learned_params["edge_thresholds"].get(tier, 0.05)
        
        if edge < min_edge:
            return False, f"Edge {edge:.1%} below {tier} threshold {min_edge:.1%}"
        
        # All checks passed
        return True, f"Passes quality filter: {tier} tier, {edge:.1%} edge"
    
    def get_learning_report(self) -> str:
        """Generate a human-readable learning report."""
        if self.learned_params["total_games_analyzed"] < self.min_games_for_learning:
            return f"""
╔══════════════════════════════════════════════════════════════════════╗
║                   🧠 LEARNING ENGINE STATUS 🧠                       ║
╠══════════════════════════════════════════════════════════════════════╣
║  STATUS: Collecting Data                                            ║
║  Progress: {self.learned_params['total_games_analyzed']}/{self.min_games_for_learning} games needed for learning                    ║
║                                                                      ║
║  The engine needs {self.min_games_for_learning} completed games before it can start   ║
║  learning and optimizing predictions.                                ║
╚══════════════════════════════════════════════════════════════════════╝
"""
        
        tier_perf = self.learned_params["tier_performance"]
        market_acc = self.learned_params["market_accuracy"]
        
        report = f"""
╔══════════════════════════════════════════════════════════════════════╗
║                   🧠 LEARNING ENGINE STATUS 🧠                       ║
╠══════════════════════════════════════════════════════════════════════╣
║  STATUS: ✅ ACTIVE & LEARNING                                       ║
║  Games Analyzed: {self.learned_params['total_games_analyzed']}                                                  ║
║  Last Updated: {self.learned_params.get('last_updated', 'Never')[:19]}                           ║
╠══════════════════════════════════════════════════════════════════════╣
║  CONFIDENCE TIER PERFORMANCE                                         ║
╠══════════════════════════════════════════════════════════════════════╣
"""
        
        for tier in ["GOLD", "SILVER", "BRONZE"]:
            perf = tier_perf.get(tier, {})
            attempts = perf.get("attempts", 0)
            wins = perf.get("wins", 0)
            acc = perf.get("accuracy", 0)
            
            if attempts > 0:
                status = "✅" if acc >= 60 else "⚠️" if acc >= 50 else "❌"
                report += f"║  {status} {tier:6} | {wins:2}/{attempts:2} wins | {acc:5.1f}% accuracy                      ║\n"
        
        report += f"""╠══════════════════════════════════════════════════════════════════════╣
║  MARKET PERFORMANCE                                                  ║
╠══════════════════════════════════════════════════════════════════════╣
"""
        
        for market, perf in market_acc.items():
            attempts = perf.get("attempts", 0)
            wins = perf.get("wins", 0)
            acc = perf.get("accuracy", 0)
            
            if attempts > 0:
                status = "✅" if acc >= 60 else "⚠️" if acc >= 50 else "❌"
                market_name = market.replace("_", " ").title()
                report += f"║  {status} {market_name:12} | {wins:2}/{attempts:2} | {acc:5.1f}%                          ║\n"
        
        adj = self.learned_params["adjustments"]
        
        report += f"""╠══════════════════════════════════════════════════════════════════════╣
║  LEARNED ADJUSTMENTS                                                 ║
╠══════════════════════════════════════════════════════════════════════╣
║  🏃 Home B2B Penalty: {adj['b2b_home_penalty']:.1f} points                               ║
║  🛣️  Road B2B Penalty: {adj['b2b_road_penalty']:.1f} points                               ║
║  ⚡ Pace Multiplier: {adj['pace_multiplier']:.3f}                                     ║
║  📊 Form Weight: {adj['form_weight']:.2f}                                          ║
╠══════════════════════════════════════════════════════════════════════╣
║  QUALITY FILTERS                                                     ║
╠══════════════════════════════════════════════════════════════════════╣
║  Only showing predictions that meet learned quality standards       ║
║  Minimum edge thresholds enforced per confidence tier                ║
║  Poor-performing prediction types automatically filtered             ║
╚══════════════════════════════════════════════════════════════════════╝
"""
        
        return report
    
    def get_adjustments(self) -> Dict:
        """Get learned adjustments to apply to predictions."""
        return self.learned_params["adjustments"].copy()


# Singleton instance
learning_engine = BasketballLearningEngine()
