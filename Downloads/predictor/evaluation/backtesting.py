"""
Backtesting Framework
=====================
Proper backtesting with:
- Rolling time-series validation (no look-ahead bias)
- Market-specific accuracy tracking
- ROI calculation (the only metric that matters)
- Detection of overfitting

Key principle: Test on data the model has NEVER seen, in chronological order.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging

from config.settings import MARKETS, OUTPUT_DIR
from models.predictors import get_predictor, PredictionResult
from filters.confidence_filter import confidence_filter, FilterResult

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """Results from a backtest run."""
    market: str
    period_start: datetime
    period_end: datetime
    
    # Counts
    total_matches: int
    matches_predicted: int
    matches_skipped: int
    
    # Accuracy metrics
    correct_predictions: int
    accuracy: float
    accuracy_high_conf: float  # Accuracy on HIGH/VERY_HIGH only
    
    # Probability calibration
    avg_confidence: float
    brier_score: float
    
    # ROI (assumes flat stakes, even odds)
    simulated_roi: float
    
    # Breakdown by confidence
    results_by_confidence: Dict[str, Dict] = field(default_factory=dict)
    
    # Individual predictions (for analysis)
    predictions: List[Dict] = field(default_factory=list)


class Backtester:
    """
    Walk-forward backtesting engine.
    
    Process:
    1. Train on historical window (e.g., 2022-2023)
    2. Predict on next period (e.g., first 3 months of 2024)
    3. Roll window forward, retrain, predict next period
    4. Aggregate results
    
    This simulates real deployment where you only have past data.
    """
    
    def __init__(self, 
                 train_window_days: int = 365,
                 test_window_days: int = 30,
                 retrain_frequency_days: int = 30):
        """
        Args:
            train_window_days: How much history to train on
            test_window_days: How far ahead to predict before retraining
            retrain_frequency_days: How often to retrain
        """
        self.train_window = timedelta(days=train_window_days)
        self.test_window = timedelta(days=test_window_days)
        self.retrain_freq = timedelta(days=retrain_frequency_days)
        
    def run_backtest(self, 
                     features_df: pd.DataFrame,
                     targets: Dict[str, pd.Series],
                     match_info: pd.DataFrame,
                     market: str,
                     start_date: datetime = None,
                     end_date: datetime = None) -> BacktestResult:
        """
        Run walk-forward backtest for a market.
        
        Args:
            features_df: Feature matrix with date index
            targets: Dict of target series for each market
            match_info: Match metadata for filtering
            market: Market to backtest
            start_date: Start of backtest period
            end_date: End of backtest period
            
        Returns:
            BacktestResult with all metrics
        """
        if start_date is None:
            start_date = features_df.index.min() + self.train_window
        if end_date is None:
            end_date = features_df.index.max()
            
        logger.info(f"Backtesting {market} from {start_date} to {end_date}")
        
        predictor = get_predictor(market)
        target_col = self._get_target_column(market)
        y = targets[target_col]
        
        all_predictions = []
        current_date = start_date
        
        while current_date < end_date:
            # Define train/test split
            train_end = current_date
            train_start = train_end - self.train_window
            test_end = min(current_date + self.test_window, end_date)
            
            # Get training data
            train_mask = (features_df.index >= train_start) & (features_df.index < train_end)
            test_mask = (features_df.index >= train_end) & (features_df.index < test_end)
            
            X_train = features_df[train_mask]
            y_train = y[train_mask]
            X_test = features_df[test_mask]
            y_test = y[test_mask]
            
            if len(X_train) < 100 or len(X_test) < 5:
                current_date += self.retrain_freq
                continue
                
            # Train
            predictor.train(X_train, y_train)
            
            # Predict each test match
            for idx in X_test.index:
                features = X_test.loc[idx].to_dict()
                match = match_info.loc[idx].to_dict() if idx in match_info.index else {}
                
                # Get raw probability
                prob = predictor.predict_proba(X_test.loc[[idx]])[0]
                
                # Apply filter
                filter_result = confidence_filter.filter(
                    match_info=match,
                    features=features,
                    raw_probability=prob,
                    market=market
                )
                
                # Record prediction
                actual = y_test[idx] if idx in y_test.index else None
                
                prediction = {
                    "date": idx,
                    "match_id": match.get("match_id"),
                    "probability": prob,
                    "adjusted_probability": filter_result.adjusted_probability,
                    "confidence_tier": filter_result.confidence_tier,
                    "should_predict": filter_result.should_predict,
                    "actual": actual,
                    "correct": None,
                }
                
                if filter_result.should_predict and actual is not None:
                    # Determine if correct based on market direction
                    if "OVER" in market.upper() or market.upper() == "BTTS":
                        predicted_class = 1 if prob >= 0.5 else 0
                    else:
                        predicted_class = 0 if prob >= 0.5 else 1
                        
                    prediction["correct"] = (predicted_class == actual)
                    
                all_predictions.append(prediction)
                
            current_date += self.retrain_freq
            
        # Calculate metrics
        return self._calculate_metrics(all_predictions, market, start_date, end_date)
        
    def _get_target_column(self, market: str) -> str:
        """Map market to target column name."""
        mapping = {
            "BTTS": "btts",
            "OVER_25_GOALS": "over_25",
            "UNDER_25_GOALS": "over_25",  # Same target, interpret differently
            "OVER_95_CORNERS": "over_95_corners",
            "UNDER_95_CORNERS": "over_95_corners",
        }
        return mapping.get(market.upper(), market.lower())
        
    def _calculate_metrics(self, predictions: List[Dict], 
                           market: str,
                           start_date: datetime,
                           end_date: datetime) -> BacktestResult:
        """Calculate all backtest metrics."""
        
        total = len(predictions)
        predicted = [p for p in predictions if p["should_predict"]]
        skipped = [p for p in predictions if not p["should_predict"]]
        
        # Accuracy on predicted matches
        evaluated = [p for p in predicted if p["correct"] is not None]
        correct = [p for p in evaluated if p["correct"]]
        
        accuracy = len(correct) / max(len(evaluated), 1)
        
        # Accuracy by confidence tier
        results_by_conf = {}
        for tier in ["LOW", "MEDIUM", "HIGH", "VERY_HIGH"]:
            tier_preds = [p for p in evaluated if p["confidence_tier"] == tier]
            tier_correct = [p for p in tier_preds if p["correct"]]
            
            results_by_conf[tier] = {
                "count": len(tier_preds),
                "correct": len(tier_correct),
                "accuracy": len(tier_correct) / max(len(tier_preds), 1)
            }
            
        # High confidence accuracy
        high_conf = [p for p in evaluated if p["confidence_tier"] in ["HIGH", "VERY_HIGH"]]
        high_conf_correct = [p for p in high_conf if p["correct"]]
        accuracy_high = len(high_conf_correct) / max(len(high_conf), 1)
        
        # Average confidence
        avg_conf = np.mean([p["probability"] for p in evaluated]) if evaluated else 0
        
        # Brier score (lower is better)
        brier = 0
        if evaluated:
            brier = np.mean([
                (p["probability"] - p["actual"]) ** 2 
                for p in evaluated if p["actual"] is not None
            ])
            
        # Simulated ROI (flat stakes, assume 1.90 odds for simplicity)
        # This is a rough estimate - real ROI depends on actual odds
        stake = 1.0
        odds = 1.90  # Typical for -110 lines
        
        returns = sum(
            (stake * odds - stake) if p["correct"] else -stake
            for p in evaluated
        )
        total_staked = len(evaluated) * stake
        roi = returns / max(total_staked, 1)
        
        return BacktestResult(
            market=market,
            period_start=start_date,
            period_end=end_date,
            total_matches=total,
            matches_predicted=len(predicted),
            matches_skipped=len(skipped),
            correct_predictions=len(correct),
            accuracy=accuracy,
            accuracy_high_conf=accuracy_high,
            avg_confidence=avg_conf,
            brier_score=brier,
            simulated_roi=roi,
            results_by_confidence=results_by_conf,
            predictions=predictions,
        )
        
    def compare_markets(self, results: List[BacktestResult]) -> pd.DataFrame:
        """Compare backtest results across markets."""
        rows = []
        for r in results:
            rows.append({
                "Market": r.market,
                "Predicted": r.matches_predicted,
                "Skipped": r.matches_skipped,
                "Skip Rate": f"{r.matches_skipped/r.total_matches:.1%}",
                "Accuracy": f"{r.accuracy:.1%}",
                "High Conf Acc": f"{r.accuracy_high_conf:.1%}",
                "Brier Score": f"{r.brier_score:.4f}",
                "ROI": f"{r.simulated_roi:+.1%}",
            })
        return pd.DataFrame(rows)
        
    def detect_overfitting(self, train_accuracy: float, 
                           test_accuracy: float,
                           threshold: float = 0.10) -> Dict:
        """
        Detect if model is overfitting.
        
        Signs of overfitting:
        - Train accuracy >> Test accuracy
        - Perfect or near-perfect train accuracy
        - Declining accuracy over time in test set
        """
        gap = train_accuracy - test_accuracy
        
        is_overfitting = (
            gap > threshold or
            train_accuracy > 0.90 or
            (train_accuracy > 0.80 and test_accuracy < 0.60)
        )
        
        return {
            "train_accuracy": train_accuracy,
            "test_accuracy": test_accuracy,
            "gap": gap,
            "is_overfitting": is_overfitting,
            "recommendation": (
                "Reduce model complexity, add regularization, or get more data"
                if is_overfitting else "Model generalization looks acceptable"
            )
        }


def save_backtest_report(result: BacktestResult, path: Path = None):
    """Save backtest results to JSON."""
    if path is None:
        path = Path(OUTPUT_DIR) / f"backtest_{result.market}_{datetime.now().strftime('%Y%m%d')}.json"
        
    report = {
        "market": result.market,
        "period": f"{result.period_start} to {result.period_end}",
        "summary": {
            "total_matches": result.total_matches,
            "matches_predicted": result.matches_predicted,
            "skip_rate": f"{result.matches_skipped/result.total_matches:.1%}",
            "accuracy": f"{result.accuracy:.1%}",
            "accuracy_high_conf": f"{result.accuracy_high_conf:.1%}",
            "brier_score": result.brier_score,
            "simulated_roi": f"{result.simulated_roi:+.1%}",
        },
        "by_confidence": result.results_by_confidence,
    }
    
    with open(path, "w") as f:
        json.dump(report, f, indent=2, default=str)
        
    logger.info(f"Saved backtest report to {path}")


# Singleton
backtester = Backtester()
