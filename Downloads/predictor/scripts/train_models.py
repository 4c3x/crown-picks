"""
Training Script
===============
Trains models for all markets using historical data.

Run this:
1. After collecting historical data
2. Weekly to incorporate new match results
3. At the start of each season
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import logging

from config.settings import DATA_DIR, MODELS_DIR, ALL_LEAGUE_IDS
from data.collector import data_collector
from features.feature_engineering import feature_engineer
from models.predictors import get_predictor
from evaluation.backtesting import backtester, save_backtest_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelTrainer:
    """
    Trains and evaluates prediction models.
    """
    
    def __init__(self):
        self.data_dir = Path(DATA_DIR)
        self.models_dir = Path(MODELS_DIR)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
    def prepare_training_data(self) -> Tuple[pd.DataFrame, Dict[str, pd.Series], pd.DataFrame]:
        """
        Load historical data and prepare features/targets.
        
        Returns:
            features_df: Feature matrix
            targets: Dict of target series by market
            match_info: Match metadata
        """
        logger.info("Loading historical data...")
        
        all_data = data_collector.load_all_data()
        
        if not all_data:
            logger.warning("No historical data found. Please run data collection first.")
            return pd.DataFrame(), {}, pd.DataFrame()
            
        logger.info(f"Loaded data from {len(all_data)} league-seasons")
        
        # Process all matches
        rows = []
        
        for season_data in all_data:
            league_id = season_data["league_id"]
            fixtures = season_data.get("fixtures", [])
            fixture_stats = season_data.get("fixture_stats", {})
            team_stats = season_data.get("team_stats", {})
            
            league_avg = self._calculate_league_averages(fixtures, fixture_stats)
            
            for fixture in fixtures:
                row = self._process_fixture(
                    fixture, fixture_stats, team_stats, 
                    fixtures, league_avg
                )
                if row:
                    rows.append(row)
                    
        if not rows:
            logger.warning("No valid training examples found")
            return pd.DataFrame(), {}, pd.DataFrame()
            
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
        df = df.set_index("date")
        
        logger.info(f"Prepared {len(df)} training examples")
        
        # Separate features and targets
        feature_cols = [c for c in df.columns if c.startswith(("btts_", "goals_", "corners_", "home_", "away_", "h2h_", "league_", "expected_", "naive_"))]
        target_cols = ["btts", "over_25", "over_95_corners", "total_goals", "total_corners"]
        info_cols = ["match_id", "home_team_id", "away_team_id", "league_id", "matchweek"]
        
        features_df = df[[c for c in feature_cols if c in df.columns]]
        targets = {c: df[c] for c in target_cols if c in df.columns}
        match_info = df[[c for c in info_cols if c in df.columns]]
        
        # Fill missing values
        features_df = features_df.fillna(features_df.median())
        
        return features_df, targets, match_info
        
    def _calculate_league_averages(self, fixtures: List, fixture_stats: Dict) -> Dict:
        """Calculate league-level averages for normalization."""
        total_goals = 0
        btts_count = 0
        total_corners = 0
        corner_matches = 0
        
        for f in fixtures:
            goals = f.get("goals", {})
            home = goals.get("home") or 0
            away = goals.get("away") or 0
            total_goals += home + away
            
            if home > 0 and away > 0:
                btts_count += 1
                
            # Get corners from stats
            fid = f["fixture"]["id"]
            if fid in fixture_stats:
                corners = self._sum_corners(fixture_stats[fid])
                if corners > 0:
                    total_corners += corners
                    corner_matches += 1
                    
        n = max(len(fixtures), 1)
        
        return {
            "avg_goals": total_goals / n,
            "btts_rate": btts_count / n,
            "over25_rate": sum(1 for f in fixtures 
                             if (f["goals"].get("home") or 0) + (f["goals"].get("away") or 0) > 2.5) / n,
            "avg_corners": total_corners / max(corner_matches, 1),
        }
        
    def _sum_corners(self, stats: List) -> int:
        """Sum corners from match statistics."""
        total = 0
        for team in stats:
            for stat in team.get("statistics", []):
                if stat.get("type") == "Corner Kicks":
                    total += stat.get("value") or 0
        return total
        
    def _process_fixture(self, fixture: Dict, fixture_stats: Dict, 
                         team_stats: Dict, all_fixtures: List,
                         league_avg: Dict) -> Dict:
        """Process a single fixture into training row."""
        try:
            goals = fixture.get("goals", {})
            home_goals = goals.get("home") or 0
            away_goals = goals.get("away") or 0
            
            home_team_id = fixture["teams"]["home"]["id"]
            away_team_id = fixture["teams"]["away"]["id"]
            fixture_id = fixture["fixture"]["id"]
            
            # Get team stats
            home_stats = team_stats.get(home_team_id, {})
            away_stats = team_stats.get(away_team_id, {})
            
            if not home_stats or not away_stats:
                return None
                
            # Get fixture statistics
            fstats = fixture_stats.get(fixture_id, [])
            
            # Calculate corners
            corners = self._sum_corners(fstats)
            
            # Get H2H (would need to filter from all_fixtures)
            h2h = []  # Simplified for training
            
            # Get recent matches for each team (would filter from all_fixtures)
            home_recent = []
            away_recent = []
            
            # Extract features
            btts_features = feature_engineer.extract_btts_features(
                home_stats, away_stats, home_recent, away_recent, h2h, league_avg
            )
            goals_features = feature_engineer.extract_goals_features(
                home_stats, away_stats, home_recent, away_recent, h2h, league_avg
            )
            corners_features = feature_engineer.extract_corners_features(
                home_stats, away_stats, [], [], [], league_avg
            )
            
            # Combine all features
            row = {
                "date": fixture["fixture"]["date"],
                "match_id": fixture_id,
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "league_id": fixture["league"]["id"],
                "matchweek": 20,  # Would parse from round
                
                # Targets
                "btts": 1 if (home_goals > 0 and away_goals > 0) else 0,
                "over_25": 1 if (home_goals + away_goals) > 2.5 else 0,
                "over_95_corners": 1 if corners > 9.5 else 0,
                "total_goals": home_goals + away_goals,
                "total_corners": corners,
            }
            
            # Add prefixed features
            for k, v in btts_features.items():
                row[f"btts_{k}"] = v
            for k, v in goals_features.items():
                row[f"goals_{k}"] = v
            for k, v in corners_features.items():
                row[f"corners_{k}"] = v
                
            return row
            
        except Exception as e:
            logger.debug(f"Failed to process fixture: {e}")
            return None
            
    def train_all_models(self) -> Dict[str, Dict]:
        """Train models for all markets."""
        features_df, targets, match_info = self.prepare_training_data()
        
        if features_df.empty:
            logger.error("No training data available")
            return {}
            
        results = {}
        
        # Train BTTS model
        logger.info("\n" + "="*50)
        logger.info("Training BTTS model...")
        logger.info("="*50)
        
        btts_features = [c for c in features_df.columns if c.startswith("btts_")]
        if btts_features and "btts" in targets:
            btts_predictor = get_predictor("BTTS")
            btts_metrics = btts_predictor.train(
                features_df[btts_features], 
                targets["btts"]
            )
            btts_predictor.save()
            results["BTTS"] = btts_metrics
            
        # Train Goals model
        logger.info("\n" + "="*50)
        logger.info("Training Goals O/U model...")
        logger.info("="*50)
        
        goals_features = [c for c in features_df.columns if c.startswith("goals_")]
        if goals_features and "over_25" in targets:
            goals_predictor = get_predictor("OVER_25_GOALS")
            goals_metrics = goals_predictor.train(
                features_df[goals_features],
                targets["over_25"]
            )
            goals_predictor.save()
            results["OVER_25_GOALS"] = goals_metrics
            
        # Train Corners model
        logger.info("\n" + "="*50)
        logger.info("Training Corners O/U model...")
        logger.info("="*50)
        
        corners_features = [c for c in features_df.columns if c.startswith("corners_")]
        if corners_features and "over_95_corners" in targets:
            corners_predictor = get_predictor("OVER_95_CORNERS")
            corners_metrics = corners_predictor.train(
                features_df[corners_features],
                targets["over_95_corners"]
            )
            corners_predictor.save()
            results["OVER_95_CORNERS"] = corners_metrics
            
        # Print summary
        logger.info("\n" + "="*50)
        logger.info("TRAINING COMPLETE")
        logger.info("="*50)
        
        for market, metrics in results.items():
            logger.info(f"\n{market}:")
            logger.info(f"  CV Accuracy: {metrics.get('cv_accuracy', 0):.1%}")
            logger.info(f"  Training Size: {metrics.get('train_size', 0)}")
            
        return results


def main():
    """Main training entry point."""
    logger.info("="*60)
    logger.info("MODEL TRAINING SCRIPT")
    logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    logger.info("="*60)
    
    trainer = ModelTrainer()
    results = trainer.train_all_models()
    
    if not results:
        print("\n⚠ No models trained. Please collect historical data first:")
        print("  python -c \"from data.collector import data_collector; data_collector.collect_season_data(39, 2024)\"")
        

if __name__ == "__main__":
    main()
