"""
Football Predictor - Configuration Settings
============================================
Central configuration for API, leagues, and model parameters.
"""

import os
from typing import Dict, List

# =============================================================================
# API CONFIGURATION
# =============================================================================
# Football API
API_KEY = os.getenv("API_SPORTS_KEY", "35b24e6a19950a0f9516397f0679e120")
API_BASE_URL = "https://v3.football.api-sports.io"
API_HEADERS = {"x-apisports-key": API_KEY}
API_RATE_LIMIT = 10  # requests per minute for Pro plan
API_DAILY_LIMIT = 7500

# Basketball API
BASKETBALL_API_KEY = os.getenv("BASKETBALL_API_KEY", "ba992a7f724370343441dd57f609d336")
BASKETBALL_API_BASE_URL = "https://v1.basketball.api-sports.io"
BASKETBALL_API_HEADERS = {"x-apisports-key": BASKETBALL_API_KEY}
BASKETBALL_API_RATE_LIMIT = 10
BASKETBALL_API_DAILY_LIMIT = 7500

# =============================================================================
# LEAGUE CONFIGURATION - TIER 1 & TIER 2 ONLY
# =============================================================================
# These leagues have the best data quality and market efficiency for prediction

LEAGUES: Dict[str, Dict] = {
    # TIER 1 - Best data quality, most matches, highest liquidity
    "TIER_1": {
        39: {"name": "Premier League", "country": "England", "avg_goals": 2.8, "tempo": "high"},
        140: {"name": "La Liga", "country": "Spain", "avg_goals": 2.5, "tempo": "medium"},
        78: {"name": "Bundesliga", "country": "Germany", "avg_goals": 3.1, "tempo": "high"},
        135: {"name": "Serie A", "country": "Italy", "avg_goals": 2.6, "tempo": "medium"},
        61: {"name": "Ligue 1", "country": "France", "avg_goals": 2.7, "tempo": "medium"},
    },
    # TIER 2 - Good data, less efficient markets = more edge
    "TIER_2": {
        88: {"name": "Eredivisie", "country": "Netherlands", "avg_goals": 3.2, "tempo": "high"},
        94: {"name": "Primeira Liga", "country": "Portugal", "avg_goals": 2.6, "tempo": "medium"},
        144: {"name": "Jupiler Pro League", "country": "Belgium", "avg_goals": 2.9, "tempo": "high"},
        203: {"name": "Süper Lig", "country": "Turkey", "avg_goals": 2.8, "tempo": "medium"},
        179: {"name": "Premiership", "country": "Scotland", "avg_goals": 2.7, "tempo": "medium"},
    }
}

# Flatten for easy access
ALL_LEAGUE_IDS: List[int] = []
for tier in LEAGUES.values():
    ALL_LEAGUE_IDS.extend(tier.keys())

def get_league_info(league_id: int) -> Dict:
    """Get league metadata by ID."""
    for tier_name, tier_leagues in LEAGUES.items():
        if league_id in tier_leagues:
            info = tier_leagues[league_id].copy()
            info["tier"] = tier_name
            info["league_id"] = league_id
            return info
    return {}

# =============================================================================
# MARKET CONFIGURATION
# =============================================================================
MARKETS = {
    "BTTS": {
        "name": "Both Teams To Score",
        "type": "binary",
        "threshold_high": 0.72,   # Minimum probability for HIGH confidence
        "threshold_medium": 0.65,
        "min_matches_required": 8,  # Min matches per team before predicting
        "expected_accuracy": 0.75,
    },
    "OVER_25_GOALS": {
        "name": "Over 2.5 Goals",
        "type": "binary",
        "threshold_high": 0.70,
        "threshold_medium": 0.62,
        "min_matches_required": 8,
        "expected_accuracy": 0.72,
    },
    "UNDER_25_GOALS": {
        "name": "Under 2.5 Goals",
        "type": "binary",
        "threshold_high": 0.70,
        "threshold_medium": 0.62,
        "min_matches_required": 8,
        "expected_accuracy": 0.72,
    },
    "OVER_95_CORNERS": {
        "name": "Over 9.5 Corners",
        "type": "binary",
        "threshold_high": 0.68,
        "threshold_medium": 0.60,
        "min_matches_required": 10,  # Corners need more data
        "expected_accuracy": 0.68,
    },
    "UNDER_95_CORNERS": {
        "name": "Under 9.5 Corners",
        "type": "binary",
        "threshold_high": 0.68,
        "threshold_medium": 0.60,
        "min_matches_required": 10,
        "expected_accuracy": 0.68,
    },
}

# =============================================================================
# CONFIDENCE FILTERING THRESHOLDS
# =============================================================================
# This is where we enforce selectivity - only top 10-15% of matches pass

CONFIDENCE_FILTERS = {
    # Data quality requirements
    "min_historical_matches": 8,          # Each team must have 8+ matches in dataset
    "min_h2h_matches": 0,                 # H2H is nice but not required
    "max_days_since_last_match": 21,      # Skip if team hasn't played in 21+ days
    
    # Probability thresholds for betting
    "min_probability_to_bet": 0.65,       # Never bet below 65% confidence
    "high_confidence_threshold": 0.72,    # Label as HIGH confidence
    "very_high_confidence_threshold": 0.78,  # Label as VERY HIGH (rare)
    
    # Volatility filters
    "max_form_volatility": 0.35,          # Skip if team's recent results are erratic
    "min_sample_consistency": 0.60,       # Feature consistency across windows
    
    # Match context filters (CRITICAL for avoiding traps)
    "skip_matchweek_1": True,             # Season openers are unpredictable
    "skip_final_3_matchweeks": True,      # Dead rubbers, motivation issues
    "skip_derbies": True,                 # Local derbies are volatile
    "skip_cup_matches": True,             # Rotation, motivation varies
    
    # League reliability weighting
    "tier_1_weight": 1.0,                 # Full confidence
    "tier_2_weight": 0.95,                # Slight discount for less efficient markets
}

# =============================================================================
# MODEL CONFIGURATION
# =============================================================================
MODEL_CONFIG = {
    "rolling_windows": [3, 5, 10],        # Games to look back
    "train_seasons": 3,                    # Seasons of historical data
    "test_split": 0.2,                     # Hold-out for validation
    "cv_folds": 5,                         # Cross-validation folds
    
    # XGBoost defaults (will be tuned)
    "xgb_params": {
        "max_depth": 4,
        "learning_rate": 0.05,
        "n_estimators": 200,
        "min_child_weight": 3,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "random_state": 42,
    },
    
    # Calibration
    "calibration_method": "isotonic",      # isotonic or sigmoid
    "calibration_cv": 3,
}

# =============================================================================
# OUTPUT PATHS
# =============================================================================
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")

# Create directories if they don't exist
for dir_path in [DATA_DIR, MODELS_DIR, LOGS_DIR, OUTPUT_DIR]:
    os.makedirs(dir_path, exist_ok=True)
