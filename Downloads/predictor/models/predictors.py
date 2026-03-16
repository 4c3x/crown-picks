"""
Prediction Models
=================
Market-specific models with probability calibration.

Architecture:
1. BTTS → Gradient Boosting + Logistic fallback
2. Goals O/U → Poisson regression + XGBoost ensemble  
3. Corners O/U → XGBoost (corners don't follow Poisson well)

All models output calibrated probabilities, not raw predictions.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod
import pickle
from pathlib import Path
import logging

from scipy import stats
from scipy.special import factorial
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import brier_score_loss, log_loss, accuracy_score
from sklearn.preprocessing import StandardScaler

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    
from config.settings import MODEL_CONFIG, MODELS_DIR

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """Container for a model prediction."""
    probability: float
    confidence_level: str  # "LOW", "MEDIUM", "HIGH", "VERY_HIGH"
    model_agreement: float  # How much ensemble models agree
    key_drivers: List[str]  # Top factors driving this prediction


class BasePredictor(ABC):
    """Abstract base class for all market predictors."""
    
    def __init__(self, market_name: str):
        self.market_name = market_name
        self.model = None
        self.calibrator = None
        self.scaler = StandardScaler()
        self.feature_names: List[str] = []
        self.is_trained = False
        
    @abstractmethod
    def train(self, X: pd.DataFrame, y: pd.Series) -> Dict:
        """Train the model. Returns metrics dict."""
        pass
        
    @abstractmethod
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict probabilities for positive class."""
        pass
        
    def get_confidence_level(self, prob: float) -> str:
        """Convert probability to confidence level."""
        if prob >= 0.78 or prob <= 0.22:
            return "VERY_HIGH"
        elif prob >= 0.72 or prob <= 0.28:
            return "HIGH"
        elif prob >= 0.65 or prob <= 0.35:
            return "MEDIUM"
        else:
            return "LOW"
            
    def save(self, path: Path = None):
        """Save model to disk."""
        if path is None:
            path = Path(MODELS_DIR) / f"{self.market_name}_model.pkl"
        with open(path, "wb") as f:
            pickle.dump({
                "model": self.model,
                "calibrator": self.calibrator,
                "scaler": self.scaler,
                "feature_names": self.feature_names,
                "is_trained": self.is_trained,
            }, f)
        logger.info(f"Saved model to {path}")
        
    def load(self, path: Path = None):
        """Load model from disk."""
        if path is None:
            path = Path(MODELS_DIR) / f"{self.market_name}_model.pkl"
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.model = data["model"]
        self.calibrator = data["calibrator"]
        self.scaler = data["scaler"]
        self.feature_names = data["feature_names"]
        self.is_trained = data["is_trained"]
        logger.info(f"Loaded model from {path}")


class BTTSPredictor(BasePredictor):
    """
    Predicts Both Teams To Score (Yes/No).
    
    Model: Gradient Boosting with isotonic calibration
    
    Why this works:
    - BTTS is binary with clear signals (clean sheets, failed to score)
    - GBM handles feature interactions well (attack vs defense matchups)
    - Calibration fixes GBM's tendency to be overconfident
    """
    
    def __init__(self):
        super().__init__("btts")
        self.feature_importance: Dict[str, float] = {}
        
    def train(self, X: pd.DataFrame, y: pd.Series) -> Dict:
        """
        Train BTTS model with time-series cross-validation.
        
        Args:
            X: Feature matrix (from extract_btts_features)
            y: Binary target (1=BTTS, 0=Not BTTS)
            
        Returns:
            Dict with training metrics
        """
        self.feature_names = list(X.columns)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Use Gradient Boosting (works better than XGBoost for small datasets)
        if HAS_XGB and len(X) > 1000:
            base_model = xgb.XGBClassifier(
                **MODEL_CONFIG["xgb_params"],
                use_label_encoder=False,
                eval_metric="logloss"
            )
        else:
            base_model = GradientBoostingClassifier(
                n_estimators=150,
                max_depth=4,
                learning_rate=0.05,
                min_samples_leaf=10,
                subsample=0.8,
                random_state=42
            )
        
        # Time-series split for validation
        tscv = TimeSeriesSplit(n_splits=MODEL_CONFIG["cv_folds"])
        
        # Cross-validation
        cv_scores = cross_val_score(
            base_model, X_scaled, y, 
            cv=tscv, scoring="accuracy"
        )
        cv_brier = cross_val_score(
            base_model, X_scaled, y,
            cv=tscv, scoring="neg_brier_score"
        )
        
        # Train final model
        base_model.fit(X_scaled, y)
        
        # Calibrate probabilities
        self.calibrator = CalibratedClassifierCV(
            base_model, 
            method=MODEL_CONFIG["calibration_method"],
            cv=MODEL_CONFIG["calibration_cv"]
        )
        self.calibrator.fit(X_scaled, y)
        
        self.model = base_model
        self.is_trained = True
        
        # Feature importance
        if hasattr(base_model, "feature_importances_"):
            self.feature_importance = dict(
                zip(self.feature_names, base_model.feature_importances_)
            )
        
        metrics = {
            "cv_accuracy": np.mean(cv_scores),
            "cv_accuracy_std": np.std(cv_scores),
            "cv_brier": -np.mean(cv_brier),
            "train_size": len(X),
            "n_features": len(self.feature_names),
        }
        
        logger.info(f"BTTS Model trained: Accuracy={metrics['cv_accuracy']:.3f} ± {metrics['cv_accuracy_std']:.3f}")
        return metrics
        
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Get calibrated probability of BTTS=Yes."""
        if not self.is_trained:
            raise ValueError("Model not trained yet")
            
        X_scaled = self.scaler.transform(X)
        
        # Use calibrated probabilities
        proba = self.calibrator.predict_proba(X_scaled)[:, 1]
        return proba
        
    def predict(self, features: Dict[str, float]) -> PredictionResult:
        """
        Make a single prediction with explanation.
        
        Args:
            features: Dict from extract_btts_features
            
        Returns:
            PredictionResult with probability and drivers
        """
        X = pd.DataFrame([features])
        prob = self.predict_proba(X)[0]
        
        # Get top drivers
        key_drivers = self._get_key_drivers(features, prob)
        
        return PredictionResult(
            probability=prob,
            confidence_level=self.get_confidence_level(prob),
            model_agreement=1.0,  # Single model
            key_drivers=key_drivers
        )
        
    def _get_key_drivers(self, features: Dict, prob: float) -> List[str]:
        """Identify top factors driving the prediction."""
        drivers = []
        
        # BTTS=Yes drivers
        if prob > 0.5:
            if features.get("home_failed_to_score_rate", 1) < 0.25:
                drivers.append(f"Home scores in {(1-features['home_failed_to_score_rate'])*100:.0f}% of games")
            if features.get("away_failed_to_score_rate", 1) < 0.30:
                drivers.append(f"Away scores in {(1-features['away_failed_to_score_rate'])*100:.0f}% of games")
            if features.get("home_clean_sheet_rate", 0) < 0.25:
                drivers.append("Home defense leaky (few clean sheets)")
            if features.get("h2h_btts_rate", 0.5) > 0.6:
                drivers.append(f"H2H shows BTTS in {features['h2h_btts_rate']*100:.0f}% of meetings")
        # BTTS=No drivers
        else:
            if features.get("home_clean_sheet_rate", 0) > 0.40:
                drivers.append(f"Home keeps clean sheet in {features['home_clean_sheet_rate']*100:.0f}% of games")
            if features.get("away_failed_to_score_rate", 0) > 0.40:
                drivers.append(f"Away fails to score in {features['away_failed_to_score_rate']*100:.0f}% of games")
                
        return drivers[:4]  # Top 4


class GoalsOverUnderPredictor(BasePredictor):
    """
    Predicts Over/Under 2.5 Goals.
    
    Model: Poisson-based expected goals + XGBoost adjustment
    
    Why this combination:
    - Poisson captures the natural distribution of goals
    - XGBoost adjusts for matchup-specific factors
    - Ensemble improves robustness
    """
    
    def __init__(self, threshold: float = 2.5):
        super().__init__(f"goals_ou_{threshold}")
        self.threshold = threshold
        self.poisson_weight = 0.4  # How much to weight Poisson vs ML
        
    def train(self, X: pd.DataFrame, y: pd.Series) -> Dict:
        """Train goals model."""
        self.feature_names = list(X.columns)
        X_scaled = self.scaler.fit_transform(X)
        
        # ML model
        if HAS_XGB:
            base_model = xgb.XGBClassifier(
                **MODEL_CONFIG["xgb_params"],
                use_label_encoder=False,
                eval_metric="logloss"
            )
        else:
            base_model = GradientBoostingClassifier(
                n_estimators=150,
                max_depth=4,
                learning_rate=0.05,
                min_samples_leaf=10,
                random_state=42
            )
            
        tscv = TimeSeriesSplit(n_splits=MODEL_CONFIG["cv_folds"])
        cv_scores = cross_val_score(base_model, X_scaled, y, cv=tscv, scoring="accuracy")
        
        base_model.fit(X_scaled, y)
        
        self.calibrator = CalibratedClassifierCV(
            base_model,
            method=MODEL_CONFIG["calibration_method"],
            cv=MODEL_CONFIG["calibration_cv"]
        )
        self.calibrator.fit(X_scaled, y)
        
        self.model = base_model
        self.is_trained = True
        
        if hasattr(base_model, "feature_importances_"):
            self.feature_importance = dict(
                zip(self.feature_names, base_model.feature_importances_)
            )
        
        metrics = {
            "cv_accuracy": np.mean(cv_scores),
            "cv_accuracy_std": np.std(cv_scores),
            "train_size": len(X),
        }
        
        logger.info(f"Goals O/U Model trained: Accuracy={metrics['cv_accuracy']:.3f}")
        return metrics
        
    def _poisson_over_prob(self, expected_goals: float) -> float:
        """
        Calculate P(Total Goals > threshold) using Poisson distribution.
        
        P(X > 2.5) = 1 - P(X <= 2) = 1 - [P(0) + P(1) + P(2)]
        """
        if expected_goals <= 0:
            return 0.0
            
        # P(X = k) = (λ^k * e^-λ) / k!
        prob_under = sum(
            (expected_goals ** k) * np.exp(-expected_goals) / factorial(k)
            for k in range(int(self.threshold) + 1)
        )
        
        return 1.0 - prob_under
        
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Get ensemble probability of Over."""
        if not self.is_trained:
            raise ValueError("Model not trained")
            
        X_scaled = self.scaler.transform(X)
        
        # ML probability
        ml_prob = self.calibrator.predict_proba(X_scaled)[:, 1]
        
        # Poisson probability (if expected_total_goals is available)
        if "expected_total_goals" in X.columns:
            poisson_prob = X["expected_total_goals"].apply(self._poisson_over_prob).values
        else:
            poisson_prob = ml_prob  # Fallback to ML only
            
        # Ensemble
        ensemble_prob = (
            self.poisson_weight * poisson_prob + 
            (1 - self.poisson_weight) * ml_prob
        )
        
        return ensemble_prob
        
    def predict(self, features: Dict[str, float]) -> PredictionResult:
        """Make a single prediction."""
        X = pd.DataFrame([features])
        prob = self.predict_proba(X)[0]
        
        drivers = self._get_key_drivers(features, prob)
        
        return PredictionResult(
            probability=prob,
            confidence_level=self.get_confidence_level(prob),
            model_agreement=1.0,
            key_drivers=drivers
        )
        
    def _get_key_drivers(self, features: Dict, prob: float) -> List[str]:
        """Identify key factors."""
        drivers = []
        
        exp_goals = features.get("expected_total_goals", 2.5)
        
        if prob > 0.5:  # Over
            drivers.append(f"Expected total goals: {exp_goals:.1f}")
            if features.get("home_goals_scored_home", 0) > 1.5:
                drivers.append(f"Home avg {features['home_goals_scored_home']:.1f} goals at home")
            if features.get("away_goals_conceded_away", 0) > 1.5:
                drivers.append(f"Away concedes {features['away_goals_conceded_away']:.1f} away")
            if features.get("h2h_avg_goals", 2.5) > 3.0:
                drivers.append(f"H2H avg {features['h2h_avg_goals']:.1f} goals")
        else:  # Under
            drivers.append(f"Expected total goals: {exp_goals:.1f}")
            if features.get("home_clean_sheet_rate", 0) > 0.35:
                drivers.append("Strong home defense")
            if exp_goals < 2.3:
                drivers.append("Low-scoring matchup expected")
                
        return drivers[:4]


class CornersOverUnderPredictor(BasePredictor):
    """
    Predicts Over/Under 9.5 Corners.
    
    Model: XGBoost (corners don't follow Poisson - too many factors)
    
    Key differences from goals:
    - Corners are tactical, not just chance
    - Style matters more (crossing teams vs possession)
    - Less variance game-to-game = more predictable
    """
    
    def __init__(self, threshold: float = 9.5):
        super().__init__(f"corners_ou_{threshold}")
        self.threshold = threshold
        
    def train(self, X: pd.DataFrame, y: pd.Series) -> Dict:
        """Train corners model."""
        self.feature_names = list(X.columns)
        X_scaled = self.scaler.fit_transform(X)
        
        if HAS_XGB:
            base_model = xgb.XGBClassifier(
                max_depth=3,  # Shallower for corners (less complex)
                learning_rate=0.05,
                n_estimators=100,
                min_child_weight=5,
                subsample=0.8,
                random_state=42,
                use_label_encoder=False,
                eval_metric="logloss"
            )
        else:
            base_model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=3,
                learning_rate=0.05,
                random_state=42
            )
            
        tscv = TimeSeriesSplit(n_splits=MODEL_CONFIG["cv_folds"])
        cv_scores = cross_val_score(base_model, X_scaled, y, cv=tscv, scoring="accuracy")
        
        base_model.fit(X_scaled, y)
        
        self.calibrator = CalibratedClassifierCV(
            base_model,
            method="sigmoid",  # Sigmoid works better for corners
            cv=3
        )
        self.calibrator.fit(X_scaled, y)
        
        self.model = base_model
        self.is_trained = True
        
        metrics = {
            "cv_accuracy": np.mean(cv_scores),
            "cv_accuracy_std": np.std(cv_scores),
            "train_size": len(X),
        }
        
        logger.info(f"Corners O/U Model trained: Accuracy={metrics['cv_accuracy']:.3f}")
        return metrics
        
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Get probability of Over 9.5 corners."""
        if not self.is_trained:
            raise ValueError("Model not trained")
            
        X_scaled = self.scaler.transform(X)
        return self.calibrator.predict_proba(X_scaled)[:, 1]
        
    def predict(self, features: Dict[str, float]) -> PredictionResult:
        """Make a single prediction."""
        X = pd.DataFrame([features])
        prob = self.predict_proba(X)[0]
        
        drivers = self._get_key_drivers(features, prob)
        
        return PredictionResult(
            probability=prob,
            confidence_level=self.get_confidence_level(prob),
            model_agreement=1.0,
            key_drivers=drivers
        )
        
    def _get_key_drivers(self, features: Dict, prob: float) -> List[str]:
        """Identify key factors."""
        drivers = []
        
        exp_corners = features.get("expected_total_corners", 10.0)
        
        if prob > 0.5:
            drivers.append(f"Expected total corners: {exp_corners:.1f}")
            if features.get("home_corners_per_game", 5) > 5.5:
                drivers.append(f"Home avg {features['home_corners_per_game']:.1f} corners")
            if features.get("away_corners_per_game", 5) > 5.0:
                drivers.append(f"Away avg {features['away_corners_per_game']:.1f} corners")
        else:
            drivers.append(f"Expected total corners: {exp_corners:.1f}")
            if exp_corners < 9.0:
                drivers.append("Low-corner matchup")
                
        return drivers[:4]


# Factory function
def get_predictor(market: str) -> BasePredictor:
    """Get the appropriate predictor for a market."""
    market = market.upper()
    
    if market == "BTTS":
        return BTTSPredictor()
    elif market in ["OVER_25_GOALS", "UNDER_25_GOALS"]:
        return GoalsOverUnderPredictor(threshold=2.5)
    elif market in ["OVER_95_CORNERS", "UNDER_95_CORNERS"]:
        return CornersOverUnderPredictor(threshold=9.5)
    else:
        raise ValueError(f"Unknown market: {market}")
