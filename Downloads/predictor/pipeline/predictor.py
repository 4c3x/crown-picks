"""
Main Prediction Pipeline
=========================
Orchestrates the full prediction flow:
1. Fetch upcoming matches
2. Extract features
3. Generate predictions
4. Apply confidence filter
5. Output JSON recommendations

This is the entry point for daily predictions.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import logging

from config.settings import ALL_LEAGUE_IDS, MARKETS, OUTPUT_DIR, get_league_info
from data.api_client import api_client
from features.feature_engineering import feature_engineer
from models.predictors import get_predictor, BTTSPredictor, GoalsOverUnderPredictor, CornersOverUnderPredictor
from filters.confidence_filter import confidence_filter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PredictionPipeline:
    """
    Main pipeline for generating match predictions.
    
    Usage:
        pipeline = PredictionPipeline()
        predictions = pipeline.predict_upcoming_matches()
    """
    
    def __init__(self):
        self.api = api_client
        self.feature_eng = feature_engineer
        self.models: Dict = {}
        self.output_dir = Path(OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def load_models(self):
        """Load trained models for all markets."""
        for market in ["BTTS", "OVER_25_GOALS", "OVER_95_CORNERS"]:
            try:
                predictor = get_predictor(market)
                predictor.load()
                self.models[market] = predictor
                logger.info(f"Loaded model for {market}")
            except Exception as e:
                logger.warning(f"Could not load model for {market}: {e}")
                
    def predict_upcoming_matches(self, 
                                  days_ahead: int = 3,
                                  markets: List[str] = None) -> List[Dict]:
        """
        Generate predictions for upcoming matches.
        
        Args:
            days_ahead: How many days ahead to look
            markets: Which markets to predict (default: all)
            
        Returns:
            List of prediction dicts in standard format
        """
        if markets is None:
            markets = ["BTTS", "OVER_25_GOALS", "OVER_95_CORNERS"]
            
        predictions = []
        
        # Fetch upcoming fixtures
        all_fixtures = []
        for league_id in ALL_LEAGUE_IDS:
            fixtures = self.api.get_upcoming_fixtures(league_id, days_ahead)
            all_fixtures.extend(fixtures)
            
        logger.info(f"Found {len(all_fixtures)} upcoming fixtures")
        
        for fixture in all_fixtures:
            fixture_id = fixture["fixture"]["id"]
            home_team = fixture["teams"]["home"]
            away_team = fixture["teams"]["away"]
            league = fixture["league"]
            
            match_predictions = self._predict_match(
                fixture=fixture,
                markets=markets
            )
            
            predictions.extend(match_predictions)
            
        # Filter to only confident predictions
        confident = [p for p in predictions if p["recommendation"] == "BET"]
        
        logger.info(f"Generated {len(predictions)} total predictions, {len(confident)} recommended")
        
        return predictions
        
    def _predict_match(self, fixture: Dict, markets: List[str]) -> List[Dict]:
        """Generate predictions for a single match."""
        predictions = []
        
        fixture_info = fixture["fixture"]
        home_team = fixture["teams"]["home"]
        away_team = fixture["teams"]["away"]
        league = fixture["league"]
        
        # Get current season
        season = datetime.now().year if datetime.now().month >= 7 else datetime.now().year - 1
        
        # Fetch required data
        try:
            home_stats = self.api.get_team_statistics(
                home_team["id"], league["id"], season
            ) or {}
            away_stats = self.api.get_team_statistics(
                away_team["id"], league["id"], season
            ) or {}
            h2h = self.api.get_head_to_head(
                home_team["id"], away_team["id"], last=10
            ) or []
        except Exception as e:
            logger.warning(f"Failed to fetch data for fixture {fixture_info['id']}: {e}")
            return []
            
        # Get league averages
        league_info = get_league_info(league["id"])
        league_avg = {
            "avg_goals": league_info.get("avg_goals", 2.6),
            "btts_rate": 0.50,  # Would calculate from historical data
            "avg_corners": 10.0,
        }
        
        # Build match info for filtering
        match_info = {
            "match_id": fixture_info["id"],
            "home_team_id": home_team["id"],
            "away_team_id": away_team["id"],
            "league_id": league["id"],
            "matchweek": fixture.get("league", {}).get("round", "20"),
            "home_matches_played": home_stats.get("fixtures", {}).get("played", {}).get("total", 0),
            "away_matches_played": away_stats.get("fixtures", {}).get("played", {}).get("total", 0),
            "is_cup": False,
        }
        
        # Parse matchweek from round string
        round_str = str(match_info["matchweek"])
        try:
            match_info["matchweek"] = int(''.join(filter(str.isdigit, round_str)) or 20)
        except:
            match_info["matchweek"] = 20
            
        # CRITICAL: Fetch recent match data for hidden edge analysis
        home_recent = self.api.get_team_recent_fixtures(home_team["id"], last=10) or []
        away_recent = self.api.get_team_recent_fixtures(away_team["id"], last=10) or []
        
        # Fetch fixture stats for recent matches (for corner/xG analysis)
        home_recent_stats = []
        for f in home_recent[:5]:
            stats = self.api.get_fixture_statistics(f.get("fixture", {}).get("id"))
            if stats:
                home_recent_stats.append(stats)
        
        away_recent_stats = []
        for f in away_recent[:5]:
            stats = self.api.get_fixture_statistics(f.get("fixture", {}).get("id"))
            if stats:
                away_recent_stats.append(stats)
        
        # Fetch H2H fixture statistics
        h2h_stats = []
        for f in h2h[:5]:
            stats = self.api.get_fixture_statistics(f.get("fixture", {}).get("id"))
            if stats:
                h2h_stats.append(stats)
        
        for market in markets:
            prediction = self._predict_market(
                market=market,
                home_stats=home_stats,
                away_stats=away_stats,
                home_recent=home_recent,
                away_recent=away_recent,
                home_recent_stats=home_recent_stats,
                away_recent_stats=away_recent_stats,
                h2h=h2h,
                h2h_stats=h2h_stats,
                league_avg=league_avg,
                match_info=match_info,
                fixture=fixture
            )
            
            if prediction:
                predictions.append(prediction)
                
        return predictions
        
    def _predict_market(self, 
                        market: str,
                        home_stats: Dict,
                        away_stats: Dict,
                        home_recent: List,
                        away_recent: List,
                        home_recent_stats: List,
                        away_recent_stats: List,
                        h2h: List,
                        h2h_stats: List,
                        league_avg: Dict,
                        match_info: Dict,
                        fixture: Dict) -> Optional[Dict]:
        """Generate prediction for a specific market."""
        
        # Extract features based on market
        if market == "BTTS":
            features = self.feature_eng.extract_btts_features(
                home_stats, away_stats, home_recent, away_recent, h2h, league_avg
            )
        elif "GOALS" in market:
            features = self.feature_eng.extract_goals_features(
                home_stats, away_stats, home_recent, away_recent, h2h, league_avg
            )
        elif "CORNERS" in market:
            features = self.feature_eng.extract_corners_features(
                home_stats, away_stats, home_recent_stats, away_recent_stats, 
                h2h_stats, league_avg
            )
        else:
            return None
            
        # Get model prediction
        if market not in self.models:
            # Use naive probability from features if model not loaded
            if market == "BTTS":
                raw_prob = features.get("naive_btts_prob", 0.5)
            elif "OVER" in market:
                raw_prob = 0.5 + (features.get("expected_total_goals", 2.5) - 2.5) * 0.15
            else:
                raw_prob = 0.5
        else:
            predictor = self.models[market]
            import pandas as pd
            X = pd.DataFrame([features])
            raw_prob = predictor.predict_proba(X)[0]
            
        # Apply confidence filter
        filter_result = confidence_filter.filter(
            match_info=match_info,
            features=features,
            raw_probability=raw_prob,
            market=market
        )
        
        # Build key factors explanation
        key_factors = self._build_key_factors(market, features, raw_prob)
        
        # Format output
        fixture_info = fixture["fixture"]
        home_team = fixture["teams"]["home"]
        away_team = fixture["teams"]["away"]
        league = fixture["league"]
        
        return {
            "match_id": fixture_info["id"],
            "match": f"{home_team['name']} vs {away_team['name']}",
            "league": league["name"],
            "kickoff": fixture_info["date"],
            "market": MARKETS.get(market, {}).get("name", market),
            "probability": round(filter_result.adjusted_probability, 3),
            "raw_probability": round(raw_prob, 3),
            "confidence_level": filter_result.confidence_tier,
            "quality_score": round(filter_result.quality_score, 2),
            "key_factors": key_factors,
            "recommendation": "BET" if filter_result.should_predict else "SKIP",
            "rejection_reasons": filter_result.rejection_reasons if not filter_result.should_predict else [],
        }
        
    def _build_key_factors(self, market: str, features: Dict, prob: float) -> List[str]:
        """Build human-readable key factors."""
        factors = []
        
        if market == "BTTS":
            fts_home = features.get("home_failed_to_score_rate", 0)
            fts_away = features.get("away_failed_to_score_rate", 0)
            cs_home = features.get("home_clean_sheet_rate", 0)
            
            if prob > 0.5:
                factors.append(f"Home scores {(1-fts_home)*100:.0f}% of games")
                factors.append(f"Away scores {(1-fts_away)*100:.0f}% of games")
                if cs_home < 0.25:
                    factors.append("Home defense concedes frequently")
            else:
                factors.append(f"Home keeps clean sheet {cs_home*100:.0f}%")
                if fts_away > 0.35:
                    factors.append(f"Away fails to score {fts_away*100:.0f}%")
                    
        elif "GOALS" in market:
            exp = features.get("expected_total_goals", 2.5)
            factors.append(f"Expected total: {exp:.1f} goals")
            
            home_scored = features.get("home_goals_scored_home", 0)
            away_conceded = features.get("away_goals_conceded_away", 0)
            
            if prob > 0.5:
                factors.append(f"Home avg {home_scored:.1f} goals at home")
                factors.append(f"Away concedes {away_conceded:.1f} away")
            else:
                factors.append("Low-scoring profiles")
                
        elif "CORNERS" in market:
            exp = features.get("expected_total_corners", 10)
            factors.append(f"Expected total: {exp:.1f} corners")
            
            home_corners = features.get("home_corners_per_game", 5)
            away_corners = features.get("away_corners_per_game", 5)
            
            factors.append(f"Home avg {home_corners:.1f} corners")
            factors.append(f"Away avg {away_corners:.1f} corners")
            
        return factors[:4]
        
    def save_predictions(self, predictions: List[Dict], 
                         filename: str = None) -> Path:
        """Save predictions to JSON file."""
        if filename is None:
            filename = f"predictions_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
            
        path = self.output_dir / filename
        
        output = {
            "generated_at": datetime.now().isoformat(),
            "total_predictions": len(predictions),
            "recommended_bets": len([p for p in predictions if p["recommendation"] == "BET"]),
            "predictions": predictions
        }
        
        with open(path, "w") as f:
            json.dump(output, f, indent=2)
            
        logger.info(f"Saved predictions to {path}")
        return path
        
    def get_recommended_bets(self, predictions: List[Dict]) -> List[Dict]:
        """Filter to only recommended bets, sorted by confidence."""
        bets = [p for p in predictions if p["recommendation"] == "BET"]
        
        # Sort by probability (distance from 50%)
        bets.sort(key=lambda x: abs(x["probability"] - 0.5), reverse=True)
        
        return bets


def run_daily_predictions():
    """
    Main entry point for daily prediction run.
    
    Run this script daily before matches kick off.
    """
    logger.info("=" * 60)
    logger.info("STARTING DAILY PREDICTION RUN")
    logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    logger.info("=" * 60)
    
    pipeline = PredictionPipeline()
    
    # Try to load trained models
    pipeline.load_models()
    
    # Generate predictions
    predictions = pipeline.predict_upcoming_matches(days_ahead=3)
    
    # Save all predictions
    pipeline.save_predictions(predictions)
    
    # Get recommended bets
    recommended = pipeline.get_recommended_bets(predictions)
    
    # =========================================================================
    # TOP 4 HIGHEST PROBABILITY BETS
    # =========================================================================
    print("\n" + "=" * 70)
    print("⭐  TOP 4 HIGHEST PROBABILITY BETS  ⭐")
    print("=" * 70)
    
    if not recommended:
        print("No high-confidence bets found for upcoming matches.")
        print("This is normal - we only bet when signals are very strong.")
    else:
        for i, bet in enumerate(recommended[:4], 1):
            kickoff_dt = datetime.fromisoformat(bet['kickoff'].replace('Z', '+00:00'))
            kickoff_str = kickoff_dt.strftime('%a %d %b, %H:%M')
            print(f"\n  #{i}  {bet['match']}")
            print(f"      📅 {kickoff_str}")
            print(f"      🏆 {bet['league']}")
            print(f"      🎯 {bet['market']}: {bet['probability']:.1%}")
            print(f"      📊 Confidence: {bet['confidence_level']}")
            if bet['key_factors']:
                print(f"      💡 {', '.join(bet['key_factors'][:2])}")
    
    # =========================================================================
    # ALL GAMES GROUPED BY DAY
    # =========================================================================
    print("\n" + "=" * 70)
    print("📅  ALL RECOMMENDED BETS BY DAY")
    print("=" * 70)
    
    if recommended:
        # Group by date
        from collections import defaultdict
        games_by_day = defaultdict(list)
        
        for bet in recommended:
            kickoff_dt = datetime.fromisoformat(bet['kickoff'].replace('Z', '+00:00'))
            day_key = kickoff_dt.strftime('%Y-%m-%d')
            games_by_day[day_key].append((kickoff_dt, bet))
        
        # Sort days
        for day_key in sorted(games_by_day.keys()):
            day_games = games_by_day[day_key]
            # Sort games within the day by kickoff time
            day_games.sort(key=lambda x: x[0])
            
            # Format day header
            day_dt = datetime.strptime(day_key, '%Y-%m-%d')
            day_header = day_dt.strftime('%A, %d %B %Y')
            
            print(f"\n{'─' * 70}")
            print(f"  📆 {day_header}  ({len(day_games)} bet{'s' if len(day_games) != 1 else ''})")
            print(f"{'─' * 70}")
            
            for kickoff_dt, bet in day_games:
                time_str = kickoff_dt.strftime('%H:%M')
                prob_bar = "█" * int(bet['probability'] * 10) + "░" * (10 - int(bet['probability'] * 10))
                print(f"\n  {time_str}  {bet['match']}")
                print(f"         {bet['league']}")
                print(f"         {bet['market']}: {prob_bar} {bet['probability']:.1%}")
    
    # =========================================================================
    # SUMMARY STATS
    # =========================================================================
    print("\n" + "=" * 70)
    print("📊  SUMMARY")
    print("=" * 70)
    print(f"  Total matches analyzed: {len(predictions) // 3}")  # 3 markets per match
    print(f"  Total predictions: {len(predictions)}")
    print(f"  Recommended bets: {len(recommended)}")
    if predictions:
        print(f"  Skip rate: {(len(predictions) - len(recommended)) / len(predictions):.1%}")
    
    return predictions


if __name__ == "__main__":
    run_daily_predictions()
