"""
Football Match Prediction System
================================

A selective, high-precision betting prediction system.

Usage:
    # 1. Collect historical data
    python -m scripts.collect_data
    
    # 2. Train models
    python -m scripts.train_models
    
    # 3. Generate predictions
    python -m pipeline.predictor
    
    # Or use the API
    from predictor import get_predictions
    predictions = get_predictions()
"""

from pipeline.predictor import PredictionPipeline, run_daily_predictions
from data.api_client import test_connection
from config.settings import MARKETS, ALL_LEAGUE_IDS


def get_predictions(days_ahead: int = 3):
    """
    Main API for getting predictions.
    
    Returns list of prediction dicts in format:
    {
        "match_id": "...",
        "match": "Team A vs Team B",
        "market": "Both Teams To Score",
        "probability": 0.76,
        "confidence_level": "HIGH",
        "key_factors": ["..."],
        "recommendation": "BET" | "SKIP"
    }
    """
    pipeline = PredictionPipeline()
    pipeline.load_models()
    return pipeline.predict_upcoming_matches(days_ahead=days_ahead)


def get_recommended_bets(days_ahead: int = 3):
    """Get only the recommended bets (filtered high-confidence)."""
    predictions = get_predictions(days_ahead)
    return [p for p in predictions if p["recommendation"] == "BET"]


__version__ = "1.0.0"
__all__ = [
    "get_predictions",
    "get_recommended_bets", 
    "run_daily_predictions",
    "test_connection",
    "MARKETS",
    "ALL_LEAGUE_IDS"
]
