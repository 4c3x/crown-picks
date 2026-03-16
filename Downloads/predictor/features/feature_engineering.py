"""
Feature Engineering Module
===========================
Extracts predictive features for each market from raw API data.

CRITICAL: Each feature is chosen based on actual predictive signal,
not just data availability. Features are market-specific.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class MatchFeatures:
    """Container for all features extracted for a match."""
    match_id: int
    home_team_id: int
    away_team_id: int
    league_id: int
    date: datetime
    
    # Common features
    home_form: float
    away_form: float
    
    # BTTS features
    btts_features: Dict[str, float]
    
    # Goals O/U features
    goals_features: Dict[str, float]
    
    # Corners O/U features
    corners_features: Dict[str, float]
    
    # Meta features (for filtering)
    data_quality_score: float
    is_derby: bool
    matchweek: int
    home_matches_played: int
    away_matches_played: int


class FeatureEngineer:
    """
    Extracts features from historical match data.
    
    Design Philosophy:
    - Every feature must have a clear causal relationship to the target
    - Rolling averages smooth out noise but shouldn't hide signal
    - Home/Away splits matter (teams behave differently)
    - Recent form weighted more than season averages
    - League context adjusts for different playing styles
    """
    
    def __init__(self, rolling_windows: List[int] = [3, 5, 10]):
        self.windows = rolling_windows
    
    def calculate_form_volatility(self, recent_fixtures: List[Dict], team_id: int) -> float:
        """
        Calculate volatility of recent results.
        High volatility = inconsistent, unpredictable.
        
        Returns: 0.0 (very consistent) to 1.0 (very volatile)
        """
        if len(recent_fixtures) < 3:
            return 0.35  # Default moderate volatility
        
        results = []
        for fixture in recent_fixtures[-10:]:  # Last 10 games
            home_goals = fixture.get("goals", {}).get("home", 0) or 0
            away_goals = fixture.get("goals", {}).get("away", 0) or 0
            home_id = fixture.get("teams", {}).get("home", {}).get("id")
            
            # Determine result from this team's perspective
            if home_id == team_id:
                result_score = home_goals - away_goals
            else:
                result_score = away_goals - home_goals
            
            # Convert to points: Win=3, Draw=1, Loss=0
            if result_score > 0:
                points = 3
            elif result_score == 0:
                points = 1
            else:
                points = 0
            
            results.append(points)
        
        # Calculate coefficient of variation
        if len(results) > 1:
            mean_points = np.mean(results)
            std_points = np.std(results)
            cv = std_points / (mean_points + 0.1)  # Avoid division by zero
            # Normalize to 0-1 range
            volatility = min(cv / 2.0, 1.0)
            return volatility
        
        return 0.35
        
    # =========================================================================
    # BTTS FEATURES
    # Why these features work for BTTS:
    # - BTTS = "Can home score?" + "Can away score?"
    # - Need: Attack strength + Opponent defensive weakness
    # - Key signals: Failed to score rate, clean sheet rate, scoring consistency
    # =========================================================================
    
    def extract_btts_features(self, home_stats: Dict, away_stats: Dict,
                               home_recent: List[Dict], away_recent: List[Dict],
                               h2h: List[Dict], league_avg: Dict) -> Dict[str, float]:
        """
        Extract features specifically for BTTS prediction.
        
        The key insight for BTTS:
        - It's TWO independent events: Home scores AND Away scores
        - Model P(BTTS) ≈ P(Home scores) × P(Away scores)
        - But not exactly - there's correlation (game tempo, referee style)
        """
        features = {}
        
        # ----- HOME TEAM SCORING ABILITY -----
        # How often do they score at home?
        home_goals_for = home_stats.get("goals", {}).get("for", {})
        features["home_goals_per_game_home"] = float(
            home_goals_for.get("average", {}).get("home", 0) or 0
        )
        
        # How often do they FAIL to score at home? (Critical for BTTS=No)
        home_fixtures = home_stats.get("fixtures", {}).get("played", {})
        home_fts = home_stats.get("failed_to_score", {}).get("home", 0)
        home_games = home_fixtures.get("home", 1) or 1
        features["home_failed_to_score_rate"] = home_fts / home_games
        
        # ----- AWAY TEAM SCORING ABILITY -----
        away_goals_for = away_stats.get("goals", {}).get("for", {})
        features["away_goals_per_game_away"] = float(
            away_goals_for.get("average", {}).get("away", 0) or 0
        )
        
        away_fixtures = away_stats.get("fixtures", {}).get("played", {})
        away_fts = away_stats.get("failed_to_score", {}).get("away", 0)
        away_games = away_fixtures.get("away", 1) or 1
        features["away_failed_to_score_rate"] = away_fts / away_games
        
        # ----- DEFENSIVE WEAKNESS (allows opponent to score) -----
        # Home team conceding = Away team can score
        home_cs = home_stats.get("clean_sheet", {}).get("home", 0)
        features["home_clean_sheet_rate"] = home_cs / home_games
        
        # Away team conceding = Home team can score
        away_cs = away_stats.get("clean_sheet", {}).get("away", 0)
        features["away_clean_sheet_rate"] = away_cs / away_games
        
        # Goals conceded per game
        home_goals_against = home_stats.get("goals", {}).get("against", {})
        features["home_conceded_per_game"] = float(
            home_goals_against.get("average", {}).get("home", 0) or 0
        )
        
        away_goals_against = away_stats.get("goals", {}).get("against", {})
        features["away_conceded_per_game"] = float(
            away_goals_against.get("average", {}).get("away", 0) or 0
        )
        
        # ----- RECENT FORM (last 5 games) -----
        # More predictive than season average for BTTS
        home_recent_scored = self._count_scoring_games(home_recent, is_home=True)
        away_recent_scored = self._count_scoring_games(away_recent, is_home=False)
        
        features["home_recent_scoring_rate"] = home_recent_scored / max(len(home_recent), 1)
        features["away_recent_scoring_rate"] = away_recent_scored / max(len(away_recent), 1)
        
        # ----- HEAD TO HEAD -----
        if h2h:
            btts_count = sum(1 for m in h2h if self._was_btts(m))
            features["h2h_btts_rate"] = btts_count / len(h2h)
        else:
            features["h2h_btts_rate"] = 0.5  # Neutral if no H2H
            
        # ----- COMBINED PROBABILITY ESTIMATE -----
        # Naive Bayes-style: P(home scores) × P(away scores)
        p_home_scores = 1 - features["home_failed_to_score_rate"]
        p_away_scores = 1 - features["away_failed_to_score_rate"]
        
        # Adjust for opponent defense
        # If home rarely keeps clean sheets, away more likely to score
        p_away_scores_adj = p_away_scores * (1 - features["home_clean_sheet_rate"] * 0.3)
        p_home_scores_adj = p_home_scores * (1 - features["away_clean_sheet_rate"] * 0.3)
        
        features["naive_btts_prob"] = p_home_scores_adj * p_away_scores_adj
        
        # ----- LEAGUE ADJUSTMENT -----
        # High-scoring leagues have more BTTS
        league_btts_rate = league_avg.get("btts_rate", 0.5)
        features["league_btts_rate"] = league_btts_rate
        
        return features
    
    # =========================================================================
    # GOALS OVER/UNDER FEATURES
    # Why these features work:
    # - Total goals = Home attack + Away attack + Defensive collapses
    # - Poisson distribution fits well (goals are rare, independent events)
    # - xG is the best predictor but not always available
    # - Tempo (shots, corners) indicates attacking intent
    # =========================================================================
    
    def extract_goals_features(self, home_stats: Dict, away_stats: Dict,
                                home_recent: List[Dict], away_recent: List[Dict],
                                h2h: List[Dict], league_avg: Dict) -> Dict[str, float]:
        """
        Extract features for Over/Under 2.5 Goals prediction.
        
        Key insight: Model expected total goals, then compare to 2.5 threshold.
        Poisson(λ=2.7) → P(Over 2.5) ≈ 55%
        Poisson(λ=2.0) → P(Over 2.5) ≈ 32%
        """
        features = {}
        
        # ----- ATTACK STRENGTH -----
        home_goals_for = home_stats.get("goals", {}).get("for", {})
        away_goals_for = away_stats.get("goals", {}).get("for", {})
        
        features["home_goals_scored_home"] = float(
            home_goals_for.get("average", {}).get("home", 0) or 0
        )
        features["away_goals_scored_away"] = float(
            away_goals_for.get("average", {}).get("away", 0) or 0
        )
        
        # ----- DEFENSIVE WEAKNESS -----
        home_goals_against = home_stats.get("goals", {}).get("against", {})
        away_goals_against = away_stats.get("goals", {}).get("against", {})
        
        features["home_goals_conceded_home"] = float(
            home_goals_against.get("average", {}).get("home", 0) or 0
        )
        features["away_goals_conceded_away"] = float(
            away_goals_against.get("average", {}).get("away", 0) or 0
        )
        
        # ----- EXPECTED TOTAL (Simple Additive Model) -----
        # This is the core feature - weighted combination of attack and defense
        expected_home_goals = (
            features["home_goals_scored_home"] * 0.6 + 
            features["away_goals_conceded_away"] * 0.4
        )
        expected_away_goals = (
            features["away_goals_scored_away"] * 0.6 + 
            features["home_goals_conceded_home"] * 0.4
        )
        
        features["expected_total_goals"] = expected_home_goals + expected_away_goals
        
        # ----- OVER/UNDER HISTORICAL RATES -----
        home_over25 = home_stats.get("goals", {}).get("for", {}).get("under_over", {})
        if home_over25:
            over = home_over25.get("2.5", {}).get("over", 0)
            under = home_over25.get("2.5", {}).get("under", 0)
            total = over + under
            features["home_over25_rate"] = over / max(total, 1)
        else:
            features["home_over25_rate"] = 0.5
            
        away_over25 = away_stats.get("goals", {}).get("for", {}).get("under_over", {})
        if away_over25:
            over = away_over25.get("2.5", {}).get("over", 0)
            under = away_over25.get("2.5", {}).get("under", 0)
            total = over + under
            features["away_over25_rate"] = over / max(total, 1)
        else:
            features["away_over25_rate"] = 0.5
        
        # ----- GOALS BY PERIOD (Tempo indicator) -----
        # Late goals indicate open, high-tempo endings
        home_late = home_stats.get("goals", {}).get("for", {}).get("minute", {})
        late_goals_pct = 0
        if home_late:
            late = (home_late.get("76-90", {}).get("total", 0) or 0) + \
                   (home_late.get("91-105", {}).get("total", 0) or 0)
            total = sum(
                (p.get("total", 0) or 0) for p in home_late.values() 
                if isinstance(p, dict)
            )
            late_goals_pct = late / max(total, 1)
        features["home_late_goals_pct"] = late_goals_pct
        
        # ----- RECENT FORM -----
        home_recent_goals = self._sum_goals(home_recent, is_home=True)
        away_recent_goals = self._sum_goals(away_recent, is_home=False)
        
        features["home_recent_goals_per_game"] = home_recent_goals / max(len(home_recent), 1)
        features["away_recent_goals_per_game"] = away_recent_goals / max(len(away_recent), 1)
        
        # Recent total goals (both teams combined)
        home_recent_total = self._sum_total_goals(home_recent)
        away_recent_total = self._sum_total_goals(away_recent)
        
        features["home_recent_match_total"] = home_recent_total / max(len(home_recent), 1)
        features["away_recent_match_total"] = away_recent_total / max(len(away_recent), 1)
        
        # ----- HEAD TO HEAD -----
        if h2h:
            h2h_goals = sum(self._get_total_goals(m) for m in h2h)
            features["h2h_avg_goals"] = h2h_goals / len(h2h)
            over25_count = sum(1 for m in h2h if self._get_total_goals(m) > 2.5)
            features["h2h_over25_rate"] = over25_count / len(h2h)
        else:
            features["h2h_avg_goals"] = league_avg.get("avg_goals", 2.6)
            features["h2h_over25_rate"] = 0.5
            
        # ----- LEAGUE CONTEXT -----
        features["league_avg_goals"] = league_avg.get("avg_goals", 2.6)
        features["league_over25_rate"] = league_avg.get("over25_rate", 0.5)
        
        return features
    
    # =========================================================================
    # CORNERS OVER/UNDER FEATURES
    # Why corners are different from goals:
    # - Corners are more frequent, less random
    # - Driven by tactical style (crossing teams = more corners)
    # - Possession-dominant teams often get fewer corners (don't need to cross)
    # - Desperate teams (chasing game) get more late corners
    # - Referee has less impact than on goals
    # =========================================================================
    
    def extract_corners_features(self, home_stats: Dict, away_stats: Dict,
                                  home_recent_stats: List[Dict], 
                                  away_recent_stats: List[Dict],
                                  h2h_stats: List[Dict],
                                  league_avg: Dict) -> Dict[str, float]:
        """
        Extract features for Over/Under 9.5 Corners prediction.
        
        Key insight: Corners are style-dependent.
        - Teams that cross a lot → more corners
        - Teams that play through middle → fewer corners
        - Mismatches in height → more corners for taller team
        """
        features = {}
        
        # ----- CORNER AVERAGES FROM RECENT MATCHES -----
        # API doesn't give season corner stats, so we calculate from recent fixtures
        home_corners = self._avg_corners(home_recent_stats, is_home=True, which="for")
        away_corners = self._avg_corners(away_recent_stats, is_home=False, which="for")
        
        features["home_corners_per_game"] = home_corners
        features["away_corners_per_game"] = away_corners
        
        # Corners conceded (opponent corners)
        home_corners_against = self._avg_corners(home_recent_stats, is_home=True, which="against")
        away_corners_against = self._avg_corners(away_recent_stats, is_home=False, which="against")
        
        features["home_corners_conceded"] = home_corners_against
        features["away_corners_conceded"] = away_corners_against
        
        # ----- EXPECTED TOTAL CORNERS -----
        expected_home = (home_corners * 0.7 + away_corners_against * 0.3)
        expected_away = (away_corners * 0.7 + home_corners_against * 0.3)
        
        features["expected_total_corners"] = expected_home + expected_away
        
        # ----- SHOTS PROXY (more shots = more corners from blocks/saves) -----
        # Using shots outside box as proxy for crossing/corner likelihood
        home_shots = self._avg_shots(home_recent_stats, is_home=True)
        away_shots = self._avg_shots(away_recent_stats, is_home=False)
        
        features["home_shots_per_game"] = home_shots
        features["away_shots_per_game"] = away_shots
        
        # ----- POSSESSION INVERSE -----
        # Counter-intuitive: Lower possession often = more corners (counter-attacks, crosses)
        # This is a style indicator
        
        # ----- HEAD TO HEAD CORNERS -----
        if h2h_stats:
            h2h_corners = self._avg_h2h_corners(h2h_stats)
            features["h2h_avg_corners"] = h2h_corners
            over95_count = sum(1 for m in h2h_stats 
                              if self._get_match_corners(m) > 9.5)
            features["h2h_over95_rate"] = over95_count / len(h2h_stats)
        else:
            features["h2h_avg_corners"] = league_avg.get("avg_corners", 10.0)
            features["h2h_over95_rate"] = 0.5
            
        # ----- LEAGUE CONTEXT -----
        features["league_avg_corners"] = league_avg.get("avg_corners", 10.0)
        
        # ----- VARIANCE/CONSISTENCY -----
        # High variance = less predictable
        home_corner_std = self._std_corners(home_recent_stats, is_home=True)
        features["home_corners_std"] = home_corner_std
        
        return features
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _count_scoring_games(self, matches: List[Dict], is_home: bool) -> int:
        """Count games where team scored at least 1 goal."""
        count = 0
        for m in matches:
            goals = m.get("goals", {})
            if is_home:
                scored = goals.get("home", 0) or 0
            else:
                scored = goals.get("away", 0) or 0
            if scored > 0:
                count += 1
        return count
        
    def _was_btts(self, match: Dict) -> bool:
        """Check if both teams scored in a match."""
        goals = match.get("goals", {})
        home = goals.get("home", 0) or 0
        away = goals.get("away", 0) or 0
        return home > 0 and away > 0
        
    def _sum_goals(self, matches: List[Dict], is_home: bool) -> int:
        """Sum goals scored by team."""
        total = 0
        for m in matches:
            goals = m.get("goals", {})
            if is_home:
                total += goals.get("home", 0) or 0
            else:
                total += goals.get("away", 0) or 0
        return total
        
    def _sum_total_goals(self, matches: List[Dict]) -> int:
        """Sum total goals in matches (both teams)."""
        total = 0
        for m in matches:
            goals = m.get("goals", {})
            total += (goals.get("home", 0) or 0) + (goals.get("away", 0) or 0)
        return total
        
    def _get_total_goals(self, match: Dict) -> int:
        """Get total goals in a single match."""
        goals = match.get("goals", {})
        return (goals.get("home", 0) or 0) + (goals.get("away", 0) or 0)
        
    def _avg_corners(self, match_stats: List[Dict], is_home: bool, 
                     which: str = "for") -> float:
        """Calculate average corners from match statistics."""
        corners_list = []
        for stats in match_stats:
            corners = self._extract_corner_count(stats, is_home, which)
            if corners is not None:
                corners_list.append(corners)
        return np.mean(corners_list) if corners_list else 5.0  # Default
        
    def _extract_corner_count(self, match_stats: Dict, is_home: bool,
                               which: str) -> Optional[int]:
        """Extract corner count from match statistics response."""
        # match_stats is the statistics array for one match
        if not match_stats:
            return None
            
        for team_stats in match_stats:
            stats_list = team_stats.get("statistics", [])
            for stat in stats_list:
                if stat.get("type") == "Corner Kicks":
                    return stat.get("value", 0) or 0
        return None
        
    def _avg_shots(self, match_stats: List[Dict], is_home: bool) -> float:
        """Calculate average shots from match statistics."""
        shots_list = []
        for stats in match_stats:
            shots = self._extract_stat(stats, "Total Shots")
            if shots is not None:
                shots_list.append(shots)
        return np.mean(shots_list) if shots_list else 12.0  # Default
        
    def _extract_stat(self, match_stats: Dict, stat_type: str) -> Optional[float]:
        """Extract a specific stat from match statistics."""
        if not match_stats:
            return None
        for team_stats in match_stats:
            stats_list = team_stats.get("statistics", [])
            for stat in stats_list:
                if stat.get("type") == stat_type:
                    val = stat.get("value")
                    if isinstance(val, str):
                        val = val.replace("%", "")
                        try:
                            return float(val)
                        except:
                            return None
                    return val
        return None
        
    def _avg_h2h_corners(self, h2h_stats: List[Dict]) -> float:
        """Average corners from H2H matches."""
        totals = []
        for match in h2h_stats:
            total = self._get_match_corners(match)
            if total:
                totals.append(total)
        return np.mean(totals) if totals else 10.0
        
    def _get_match_corners(self, match_stats: Dict) -> int:
        """Get total corners from a match's statistics."""
        # This needs the full statistics, not just the fixture
        total = 0
        if isinstance(match_stats, list):
            for team in match_stats:
                for stat in team.get("statistics", []):
                    if stat.get("type") == "Corner Kicks":
                        total += stat.get("value", 0) or 0
        return total
        
    def _std_corners(self, match_stats: List[Dict], is_home: bool) -> float:
        """Calculate standard deviation of corners."""
        corners_list = []
        for stats in match_stats:
            corners = self._extract_corner_count(stats, is_home, "for")
            if corners is not None:
                corners_list.append(corners)
        return np.std(corners_list) if len(corners_list) > 1 else 2.0
    
    # =========================================================================
    # MATCH TIMING FEATURES - Hidden Edge Factors
    # =========================================================================
    
    def extract_timing_features(self, fixture: Dict) -> Dict[str, any]:
        """
        Extract match timing features that affect predictions.
        
        KEY INSIGHTS:
        - Midweek games (Tue-Thu) average 0.3 fewer goals
        - Early kickoffs (12:30) have different patterns
        - Night games (20:00+) tend to be more open
        - End of season games have different motivation
        """
        fixture_data = fixture.get("fixture", {})
        date_str = fixture_data.get("date", "")
        
        features = {
            "day_of_week": None,
            "is_weekend": False,
            "is_midweek": False,
            "hour_of_day": None,
            "is_early_kickoff": False,
            "is_evening_game": False,
            "is_night_game": False,
            "timing_goals_adjustment": 1.0,
        }
        
        if not date_str:
            return features
        
        try:
            # Parse datetime
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            
            features["day_of_week"] = dt.weekday()  # 0=Monday, 6=Sunday
            features["is_weekend"] = dt.weekday() >= 5  # Sat/Sun
            features["is_midweek"] = dt.weekday() in [1, 2, 3]  # Tue/Wed/Thu
            features["hour_of_day"] = dt.hour
            
            # Kickoff time categories
            features["is_early_kickoff"] = dt.hour < 14  # Before 2pm
            features["is_evening_game"] = 17 <= dt.hour < 20
            features["is_night_game"] = dt.hour >= 20
            
            # Calculate timing adjustment for goals
            adjustment = 1.0
            
            # Midweek penalty (fatigue, lower intensity)
            if features["is_midweek"]:
                adjustment *= 0.92  # ~8% fewer goals
            
            # Early kickoff penalty (players not fully awake)
            if features["is_early_kickoff"]:
                adjustment *= 0.95  # ~5% fewer goals
            
            # Night games bonus (more open, fans create atmosphere)
            if features["is_night_game"]:
                adjustment *= 1.03  # ~3% more goals
            
            features["timing_goals_adjustment"] = round(adjustment, 3)
            
        except Exception as e:
            logger.warning(f"Failed to parse fixture date: {e}")
        
        return features
    
    def extract_season_context(self, fixture: Dict, 
                                home_position: int, 
                                away_position: int,
                                total_teams: int = 20) -> Dict[str, any]:
        """
        Extract season context features.
        
        KEY INSIGHTS:
        - Last 5 matchweeks: relegation battles are chaotic
        - Top 4 races: more cagey, fewer goals
        - Mid-table with nothing to play for: unpredictable
        - Title deciders: can go either way
        """
        league = fixture.get("league", {})
        round_str = str(league.get("round", "20"))
        
        # Extract matchweek number
        try:
            matchweek = int(''.join(filter(str.isdigit, round_str)) or 20)
        except:
            matchweek = 20
        
        total_matchweeks = 38  # Assume 38-game season
        
        features = {
            "matchweek": matchweek,
            "season_stage": "mid",
            "is_early_season": matchweek <= 6,
            "is_late_season": matchweek >= 33,
            "is_final_day": matchweek >= 37,
            "home_in_title_race": home_position <= 2,
            "away_in_title_race": away_position <= 2,
            "home_in_top_4_race": home_position <= 5,
            "away_in_top_4_race": away_position <= 5,
            "home_in_relegation": home_position >= total_teams - 3,
            "away_in_relegation": away_position >= total_teams - 3,
            "both_have_nothing_to_play_for": False,
            "motivation_differential": 0,
            "season_context_adjustment": 1.0,
        }
        
        # Season stage
        if matchweek <= 6:
            features["season_stage"] = "early"
        elif matchweek >= 33:
            features["season_stage"] = "late"
        else:
            features["season_stage"] = "mid"
        
        # Both teams mid-table with nothing to play for
        mid_low = total_teams // 3
        mid_high = 2 * total_teams // 3
        home_mid = mid_low < home_position < mid_high
        away_mid = mid_low < away_position < mid_high
        features["both_have_nothing_to_play_for"] = home_mid and away_mid and matchweek >= 30
        
        # Motivation differential
        home_motivation = 0
        away_motivation = 0
        
        if features["home_in_relegation"]:
            home_motivation += 3
        if features["home_in_top_4_race"]:
            home_motivation += 2
        if features["home_in_title_race"]:
            home_motivation += 1
        
        if features["away_in_relegation"]:
            away_motivation += 3
        if features["away_in_top_4_race"]:
            away_motivation += 2
        if features["away_in_title_race"]:
            away_motivation += 1
        
        features["motivation_differential"] = home_motivation - away_motivation
        
        # Season context adjustment
        adjustment = 1.0
        
        if features["is_late_season"]:
            if features["home_in_relegation"] or features["away_in_relegation"]:
                adjustment *= 1.05  # Relegation battles = more open
            if features["home_in_title_race"] or features["away_in_title_race"]:
                adjustment *= 0.95  # Title race = cagey
        
        if features["both_have_nothing_to_play_for"]:
            adjustment *= 1.08  # Open, meaningless games
        
        if features["is_early_season"]:
            adjustment *= 0.97  # Teams still finding rhythm
        
        features["season_context_adjustment"] = round(adjustment, 3)
        
        return features


# Create singleton instance
feature_engineer = FeatureEngineer()
