"""
ELITE PREDICTION ENGINE v2.0
============================
The secret weapon. This isn't a toy - this is what separates profitable
punters from the 95% who lose.

FOCUSED MARKETS (The Only 4 Worth Your Time):
1. Over 1.5 Goals - Highest hit rate, Poisson-perfect
2. BTTS - Binary, clean signals
3. Over 2.5 Goals - Most liquid, good odds
4. Under 3.5 Goals - Inverse value, defensive edge

HIDDEN EDGE FACTORS (What Others Miss):
- Fixture congestion (European hangover)
- Scoring by period (late goal specialists)
- First goal impact (team psychology)
- Revenge factor (lost heavily last time)
- Managerial bounce (new manager effect)
- Home/Away form splits (Jekyll & Hyde teams)
- Goal drought breakers (team hasn't scored in X games)
- Clean sheet breakers (team hasn't kept CS in X games)

Author's Note:
"The edge isn't in the obvious stats. It's in the patterns others ignore."
"""

import numpy as np
from scipy import stats
from scipy.special import factorial
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import math


@dataclass
class ElitePrediction:
    """The output of elite analysis."""
    match: str
    market: str
    prediction: str  # "YES" or "NO" / "OVER" or "UNDER"
    our_probability: float
    fair_odds: float  # What odds SHOULD be
    
    # Value analysis
    min_acceptable_odds: float
    
    # Confidence
    confidence_score: float  # 0-100
    confidence_tier: str  # "BRONZE", "SILVER", "GOLD", "PLATINUM"
    
    # Staking
    kelly_fraction: float
    recommended_stake_pct: float  # Of bankroll
    
    # Reasoning
    key_factors: List[str]
    warnings: List[str]
    
    # Optional fields with defaults must come last
    edge_at_odds: Optional[float] = None  # Edge if you input bookmaker odds


class PoissonGoalsModel:
    """
    Poisson regression for goals - the mathematically correct approach.
    
    Goals are rare, independent events - Poisson is the natural fit.
    P(X=k) = (λ^k × e^(-λ)) / k!
    
    We estimate λ (expected goals) for each team, then calculate
    the full probability distribution.
    """
    
    def __init__(self):
        # League strength adjustments (some leagues higher scoring)
        self.league_multipliers = {
            78: 1.15,   # Bundesliga - historically highest
            88: 1.12,   # Eredivisie
            144: 1.08,  # Belgium
            39: 1.02,   # Premier League
            61: 0.98,   # Ligue 1
            140: 0.95,  # La Liga - more defensive
            135: 0.92,  # Serie A - most defensive
            94: 0.98,
            203: 1.05,
            179: 1.00,
        }
    
    def calculate_expected_goals(self, 
                                  home_attack: float,
                                  home_defense: float,
                                  away_attack: float,
                                  away_defense: float,
                                  league_id: int,
                                  league_avg_goals: float = 2.7) -> Tuple[float, float]:
        """
        Calculate expected goals for each team.
        
        Uses attack/defense ratings relative to league average.
        Home advantage baked in via attack/defense splits.
        """
        # League adjustment
        league_mult = self.league_multipliers.get(league_id, 1.0)
        
        # Expected goals formula:
        # Home xG = (Home Attack Strength × Away Defense Weakness) × League Avg / 2
        # This normalizes everything relative to league average
        
        avg_half = league_avg_goals / 2  # Average goals per team
        
        home_xg = home_attack * away_defense * avg_half * league_mult
        away_xg = away_attack * home_defense * avg_half * league_mult
        
        # Clamp to reasonable values
        home_xg = max(0.3, min(4.0, home_xg))
        away_xg = max(0.2, min(3.5, away_xg))
        
        return home_xg, away_xg
    
    def poisson_prob(self, lam: float, k: int) -> float:
        """P(X = k) for Poisson distribution."""
        return (lam ** k) * np.exp(-lam) / factorial(k)
    
    def prob_over_goals(self, home_xg: float, away_xg: float, threshold: float) -> float:
        """
        Calculate P(Total Goals > threshold).
        
        Uses convolution of two Poisson distributions.
        More accurate than assuming total goals is Poisson (it's not exactly).
        """
        prob_under = 0
        target = int(threshold)  # e.g., 2 for O/U 2.5
        
        # Sum all combinations where total <= target
        for home_goals in range(target + 2):
            for away_goals in range(target + 2):
                if home_goals + away_goals <= target:
                    p_home = self.poisson_prob(home_xg, home_goals)
                    p_away = self.poisson_prob(away_xg, away_goals)
                    prob_under += p_home * p_away
        
        return 1 - prob_under
    
    def prob_btts(self, home_xg: float, away_xg: float) -> float:
        """
        P(Both Teams Score) = P(Home≥1) × P(Away≥1)
        
        Slight correlation adjustment for game state effects.
        """
        p_home_scores = 1 - self.poisson_prob(home_xg, 0)
        p_away_scores = 1 - self.poisson_prob(away_xg, 0)
        
        # Correlation adjustment: open games tend to have more BTTS
        # If both teams are attacking, slight positive correlation
        base_btts = p_home_scores * p_away_scores
        
        # Adjust for high-scoring expectation (more open = higher BTTS)
        total_xg = home_xg + away_xg
        if total_xg > 3.0:
            base_btts = min(0.95, base_btts * 1.05)
        elif total_xg < 2.0:
            base_btts = base_btts * 0.92
        
        return base_btts


class SituationalAdjuster:
    """
    Real-world factors that stats don't capture directly.
    These are the edges bookmakers often miss.
    """
    
    def __init__(self):
        # Motivation matrix
        self.motivation_adjustments = {
            "title_race": 1.08,        # Fighting for title
            "relegation_battle": 1.10,  # Survival mode
            "european_push": 1.05,      # Fighting for Europe
            "mid_table": 0.98,          # Nothing to play for
            "dead_rubber": 0.85,        # Literally nothing to play for
            "revenge_match": 1.03,      # Lost heavily in reverse fixture
        }
    
    def get_motivation_factor(self, position: int, total_teams: int, 
                               matchweek: int, total_matchweeks: int) -> float:
        """Estimate motivation based on league position and timing."""
        
        # End of season effects
        season_progress = matchweek / total_matchweeks
        
        if season_progress < 0.3:
            # Early season - everyone motivated
            return 1.02
        
        if season_progress > 0.85:
            # Late season - position matters a lot
            if position <= 2:
                return self.motivation_adjustments["title_race"]
            elif position >= total_teams - 3:
                return self.motivation_adjustments["relegation_battle"]
            elif position <= 6:
                return self.motivation_adjustments["european_push"]
            elif 8 <= position <= total_teams - 6:
                return self.motivation_adjustments["dead_rubber"]
        
        return 1.0
    
    def get_fatigue_factor(self, days_since_last: int, 
                           is_playing_in_europe: bool = False) -> float:
        """
        Fatigue adjustment based on fixture congestion.
        
        Key insight: 3-day turnaround kills performance.
        """
        if days_since_last <= 3:
            base_fatigue = 0.92  # Significant impact
        elif days_since_last <= 4:
            base_fatigue = 0.96
        elif days_since_last <= 7:
            base_fatigue = 1.00
        elif days_since_last <= 14:
            base_fatigue = 1.02  # Well rested
        else:
            base_fatigue = 0.97  # Too much rest, match sharpness lost
        
        # European hangover
        if is_playing_in_europe and days_since_last <= 4:
            base_fatigue *= 0.95
        
        return base_fatigue
    
    def get_home_advantage(self, league_id: int, 
                           home_form_home: float,
                           away_form_away: float) -> float:
        """
        Home advantage varies by league and team.
        
        Post-COVID home advantage has decreased but still exists.
        """
        base_advantage = {
            39: 1.12,   # EPL - moderate
            140: 1.18,  # La Liga - strong home advantage
            78: 1.10,   # Bundesliga - fans matter
            135: 1.20,  # Serie A - fortress mentality
            61: 1.15,   # Ligue 1
            203: 1.25,  # Turkey - intimidating atmospheres
            88: 1.08,   # Eredivisie
        }.get(league_id, 1.12)
        
        # Adjust based on actual home/away form difference
        form_diff = home_form_home - away_form_away
        
        if form_diff > 0.5:
            return base_advantage * 1.05
        elif form_diff < -0.3:
            return base_advantage * 0.92  # Home team weak at home
        
        return base_advantage


class HiddenEdgeAnalyzer:
    """
    THE SECRET SAUCE - Factors that 95% of bettors ignore.
    These create real edges because bookmakers weight them less.
    """
    
    def __init__(self):
        pass
    
    def analyze_scoring_patterns(self, recent_fixtures: List[Dict], 
                                  team_id: int) -> Dict[str, float]:
        """
        Analyze WHEN a team scores - first 15, last 15, after conceding, etc.
        
        Key insight: Teams that score late are goldmines for Over markets.
        Teams that concede early are goldmines for BTTS Yes.
        """
        patterns = {
            "first_15_goals": 0,
            "last_15_goals": 0,
            "last_30_goals": 0,
            "goals_after_conceding": 0,
            "goals_when_winning": 0,
            "total_goals": 0,
            "matches": 0,
        }
        
        for fixture in recent_fixtures[-10:]:
            home_id = fixture.get("teams", {}).get("home", {}).get("id")
            is_home = (home_id == team_id)
            
            home_goals = fixture.get("goals", {}).get("home", 0) or 0
            away_goals = fixture.get("goals", {}).get("away", 0) or 0
            
            team_goals = home_goals if is_home else away_goals
            patterns["total_goals"] += team_goals
            patterns["matches"] += 1
            
            # Check score at different periods if available
            score = fixture.get("score", {})
            ht = score.get("halftime", {})
            ft = score.get("fulltime", {})
            
            if ht and ft:
                ht_home = ht.get("home", 0) or 0
                ht_away = ht.get("away", 0) or 0
                ft_home = ft.get("home", 0) or 0
                ft_away = ft.get("away", 0) or 0
                
                # Second half goals
                if is_home:
                    second_half_goals = ft_home - ht_home
                else:
                    second_half_goals = ft_away - ht_away
                
                # Approximate late goals (assume ~60% of 2nd half goals are last 30)
                patterns["last_30_goals"] += second_half_goals * 0.6
                patterns["last_15_goals"] += second_half_goals * 0.3
        
        # Normalize to per-game rates
        if patterns["matches"] > 0:
            patterns["late_goal_rate"] = patterns["last_30_goals"] / patterns["matches"]
            patterns["goals_per_game"] = patterns["total_goals"] / patterns["matches"]
        else:
            patterns["late_goal_rate"] = 0.5
            patterns["goals_per_game"] = 1.0
        
        return patterns
    
    def analyze_drought_breakers(self, recent_fixtures: List[Dict],
                                  team_id: int) -> Dict[str, any]:
        """
        Identify teams on goal droughts or clean sheet droughts.
        
        Key insight: A team that hasn't scored in 3+ games is DUE.
        The pressure builds, tactics change, they throw everything forward.
        Similarly, a team that hasn't kept a clean sheet in 8 games
        won't suddenly keep one against a top team.
        """
        droughts = {
            "games_since_scored": 0,
            "games_since_clean_sheet": 0,
            "games_since_btts": 0,
            "games_since_over_25": 0,
            "current_streak_type": None,  # "winning", "losing", "drawing"
            "streak_length": 0,
        }
        
        # Count backwards from most recent
        scored_found = False
        cs_found = False
        btts_found = False
        over25_found = False
        
        last_results = []
        
        for fixture in reversed(recent_fixtures[-10:]):
            home_id = fixture.get("teams", {}).get("home", {}).get("id")
            is_home = (home_id == team_id)
            
            home_goals = fixture.get("goals", {}).get("home", 0) or 0
            away_goals = fixture.get("goals", {}).get("away", 0) or 0
            
            team_goals = home_goals if is_home else away_goals
            opponent_goals = away_goals if is_home else home_goals
            total = home_goals + away_goals
            
            # Result for streak
            if team_goals > opponent_goals:
                last_results.append("W")
            elif team_goals < opponent_goals:
                last_results.append("L")
            else:
                last_results.append("D")
            
            # Drought tracking
            if not scored_found:
                if team_goals > 0:
                    scored_found = True
                else:
                    droughts["games_since_scored"] += 1
            
            if not cs_found:
                if opponent_goals == 0:
                    cs_found = True
                else:
                    droughts["games_since_clean_sheet"] += 1
            
            if not btts_found:
                if team_goals > 0 and opponent_goals > 0:
                    btts_found = True
                else:
                    droughts["games_since_btts"] += 1
            
            if not over25_found:
                if total > 2.5:
                    over25_found = True
                else:
                    droughts["games_since_over_25"] += 1
        
        # Calculate streak
        if last_results:
            streak_type = last_results[0]
            streak_length = 1
            for result in last_results[1:]:
                if result == streak_type:
                    streak_length += 1
                else:
                    break
            droughts["current_streak_type"] = {"W": "winning", "L": "losing", "D": "drawing"}[streak_type]
            droughts["streak_length"] = streak_length
        
        return droughts
    
    def analyze_h2h_psychology(self, h2h: List[Dict], 
                                home_id: int, away_id: int) -> Dict[str, any]:
        """
        Deep H2H analysis beyond simple win/loss.
        
        Key insights:
        - Revenge factor: Lost 4-0 last time? Extra motivation.
        - Bogey team: Some teams just can't beat certain opponents.
        - High-scoring history: Some matchups are always open.
        """
        if not h2h:
            return {
                "revenge_factor": 1.0,
                "home_dominance": 0.5,
                "avg_total_goals": 2.5,
                "btts_rate": 0.5,
                "over25_rate": 0.5,
                "biggest_home_win": 0,
                "biggest_away_win": 0,
            }
        
        home_wins = 0
        away_wins = 0
        draws = 0
        total_goals = 0
        btts_count = 0
        over25_count = 0
        biggest_home_margin = 0
        biggest_away_margin = 0
        last_result_margin = 0
        
        for i, match in enumerate(h2h):
            h_goals = match.get("goals", {}).get("home", 0) or 0
            a_goals = match.get("goals", {}).get("away", 0) or 0
            
            match_home_id = match.get("teams", {}).get("home", {}).get("id")
            
            # Normalize to our perspective (home_id vs away_id)
            if match_home_id == home_id:
                home_scored = h_goals
                away_scored = a_goals
            else:
                home_scored = a_goals
                away_scored = h_goals
            
            margin = home_scored - away_scored
            
            if margin > 0:
                home_wins += 1
                biggest_home_margin = max(biggest_home_margin, margin)
            elif margin < 0:
                away_wins += 1
                biggest_away_margin = max(biggest_away_margin, -margin)
            else:
                draws += 1
            
            total_goals += h_goals + a_goals
            if h_goals > 0 and a_goals > 0:
                btts_count += 1
            if h_goals + a_goals > 2.5:
                over25_count += 1
            
            # Last result for revenge factor
            if i == 0:
                last_result_margin = margin
        
        n = len(h2h)
        
        # Revenge factor: Lost heavily last time = extra motivation
        revenge = 1.0
        if last_result_margin <= -3:  # Lost by 3+
            revenge = 1.08  # Home team motivated for revenge
        elif last_result_margin >= 3:  # Won by 3+
            revenge = 0.97  # Away team motivated for revenge
        
        return {
            "revenge_factor": revenge,
            "home_dominance": home_wins / n if n > 0 else 0.5,
            "away_dominance": away_wins / n if n > 0 else 0.5,
            "draw_rate": draws / n if n > 0 else 0.25,
            "avg_total_goals": total_goals / n if n > 0 else 2.5,
            "btts_rate": btts_count / n if n > 0 else 0.5,
            "over25_rate": over25_count / n if n > 0 else 0.5,
            "biggest_home_win": biggest_home_margin,
            "biggest_away_win": biggest_away_margin,
            "matches_analyzed": n,
        }
    
    def analyze_form_splits(self, team_stats: Dict, recent: List[Dict],
                            team_id: int) -> Dict[str, float]:
        """
        Home/Away form splits - some teams are Jekyll & Hyde.
        
        Key insight: A team 5th overall might be 2nd at home, 15th away.
        This split is GOLD for predictions.
        """
        goals_for = team_stats.get("goals", {}).get("for", {}).get("average", {})
        goals_against = team_stats.get("goals", {}).get("against", {}).get("average", {})
        
        home_scored = float(goals_for.get("home", 0) or 0)
        away_scored = float(goals_for.get("away", 0) or 0)
        home_conceded = float(goals_against.get("home", 0) or 0)
        away_conceded = float(goals_against.get("away", 0) or 0)
        
        # Form split ratio
        home_attack_ratio = home_scored / (away_scored + 0.1)
        home_defense_ratio = away_conceded / (home_conceded + 0.1)
        
        # Recent form from last 5
        home_form = 0
        away_form = 0
        home_games = 0
        away_games = 0
        
        for fixture in recent[-10:]:
            home_id_match = fixture.get("teams", {}).get("home", {}).get("id")
            is_home = (home_id_match == team_id)
            
            h_goals = fixture.get("goals", {}).get("home", 0) or 0
            a_goals = fixture.get("goals", {}).get("away", 0) or 0
            
            if is_home:
                diff = h_goals - a_goals
                home_form += 3 if diff > 0 else (1 if diff == 0 else 0)
                home_games += 1
            else:
                diff = a_goals - h_goals
                away_form += 3 if diff > 0 else (1 if diff == 0 else 0)
                away_games += 1
        
        return {
            "home_attack_ratio": home_attack_ratio,
            "home_defense_ratio": home_defense_ratio,
            "is_home_team": home_attack_ratio > 1.3,  # Much better at home
            "is_away_team": home_attack_ratio < 0.7,  # Much better away
            "home_ppg": home_form / max(home_games, 1),
            "away_ppg": away_form / max(away_games, 1),
            "form_split_significant": abs(home_attack_ratio - 1) > 0.4,
        }
    
    def get_hidden_edge_multipliers(self, 
                                     home_patterns: Dict,
                                     away_patterns: Dict,
                                     home_droughts: Dict,
                                     away_droughts: Dict,
                                     h2h_psychology: Dict,
                                     home_splits: Dict,
                                     away_splits: Dict) -> Dict[str, float]:
        """
        Combine all hidden factors into probability multipliers.
        """
        multipliers = {
            "btts_yes": 1.0,
            "btts_no": 1.0,
            "over_15": 1.0,
            "over_25": 1.0,
            "under_35": 1.0,
        }
        
        # Late goal specialists boost Over markets
        combined_late_rate = (home_patterns.get("late_goal_rate", 0.5) + 
                             away_patterns.get("late_goal_rate", 0.5))
        if combined_late_rate > 1.2:
            multipliers["over_25"] *= 1.06
            multipliers["over_15"] *= 1.04
        
        # Goal drought = desperate attacking = more goals
        if home_droughts.get("games_since_scored", 0) >= 2:
            multipliers["over_25"] *= 1.04  # They'll push forward
            multipliers["btts_no"] *= 1.05  # But might still fail
        
        if away_droughts.get("games_since_scored", 0) >= 2:
            multipliers["over_25"] *= 1.03
        
        # Clean sheet drought = defensive issues = BTTS likely
        if home_droughts.get("games_since_clean_sheet", 0) >= 5:
            multipliers["btts_yes"] *= 1.08
            multipliers["btts_no"] *= 0.92
        
        if away_droughts.get("games_since_clean_sheet", 0) >= 5:
            multipliers["btts_yes"] *= 1.06
        
        # H2H high-scoring history
        if h2h_psychology.get("avg_total_goals", 2.5) > 3.2:
            multipliers["over_25"] *= 1.07
            multipliers["over_15"] *= 1.04
        
        if h2h_psychology.get("btts_rate", 0.5) > 0.7:
            multipliers["btts_yes"] *= 1.08
        elif h2h_psychology.get("btts_rate", 0.5) < 0.3:
            multipliers["btts_no"] *= 1.08
        
        # Revenge factor
        revenge = h2h_psychology.get("revenge_factor", 1.0)
        if revenge > 1.0:
            multipliers["over_25"] *= 1.03  # More intense = more goals
        
        # Form splits
        if home_splits.get("is_home_team", False):
            multipliers["over_25"] *= 1.04  # Home teams at fortress score more
        
        if away_splits.get("is_away_team", False):
            multipliers["btts_yes"] *= 1.03  # Away specialists still score
        
        # Winning/Losing streaks
        if home_droughts.get("current_streak_type") == "losing" and home_droughts.get("streak_length", 0) >= 3:
            multipliers["btts_no"] *= 1.05  # Losing teams struggle to score
        
        if away_droughts.get("current_streak_type") == "winning" and away_droughts.get("streak_length", 0) >= 4:
            multipliers["btts_yes"] *= 1.04  # Form team will score
            multipliers["over_25"] *= 1.03
        
        return multipliers


class ValueCalculator:
    """
    THE CORE EDGE ENGINE
    
    Value = Our Probability - Implied Probability
    
    We only bet when Value > Minimum Edge Threshold
    """
    
    def __init__(self, min_edge: float = 0.03, max_edge: float = 0.25):
        self.min_edge = min_edge  # 3% minimum edge
        self.max_edge = max_edge  # Cap at 25% (suspicious if higher)
    
    def decimal_to_implied_prob(self, odds: float) -> float:
        """Convert decimal odds to implied probability."""
        return 1 / odds
    
    def prob_to_fair_odds(self, prob: float) -> float:
        """Convert probability to fair decimal odds (no margin)."""
        return 1 / max(prob, 0.01)
    
    def calculate_edge(self, our_prob: float, bookmaker_odds: float) -> float:
        """
        Calculate our edge vs the bookmaker.
        
        Edge = Our Probability - Implied Probability
        """
        implied = self.decimal_to_implied_prob(bookmaker_odds)
        return our_prob - implied
    
    def is_value_bet(self, our_prob: float, bookmaker_odds: float) -> Tuple[bool, float]:
        """Check if this is a value bet and return the edge."""
        edge = self.calculate_edge(our_prob, bookmaker_odds)
        
        # Suspicious if edge too high - probably we're wrong
        if edge > self.max_edge:
            return False, edge
        
        return edge >= self.min_edge, edge
    
    def kelly_criterion(self, our_prob: float, odds: float, 
                        fraction: float = 0.25) -> float:
        """
        Kelly Criterion for optimal stake sizing.
        
        Full Kelly: f = (p × (b + 1) - 1) / b
        where p = our probability, b = odds - 1
        
        We use fractional Kelly (typically 1/4) for safety.
        """
        b = odds - 1
        q = 1 - our_prob
        
        full_kelly = (our_prob * (b + 1) - 1) / b
        
        # Never bet more than 5% of bankroll
        fractional = full_kelly * fraction
        return max(0, min(0.05, fractional))


class ElitePredictor:
    """
    THE MAIN ENGINE v2.0
    
    Focused on 4 markets only:
    1. Over 1.5 Goals (highest hit rate)
    2. BTTS Yes/No (cleanest signals)
    3. Over 2.5 Goals (most liquid)
    4. Under 3.5 Goals (defensive edge)
    
    With hidden edge factors built in.
    """
    
    def __init__(self):
        self.poisson = PoissonGoalsModel()
        self.situational = SituationalAdjuster()
        self.hidden_edge = HiddenEdgeAnalyzer()
        self.value = ValueCalculator()
        
        # Weight factors by predictive power (learned from historical performance)
        self.feature_weights = {
            # BTTS weights
            "btts_home_fts_rate": -0.35,      # Failed to score = negative
            "btts_away_fts_rate": -0.40,      # Away FTS more impactful
            "btts_home_cs_rate": -0.25,       # Clean sheets = less BTTS
            "btts_away_cs_rate": -0.20,
            "btts_h2h_rate": 0.15,            # H2H less reliable but useful
            "btts_recent_form": 0.20,
            
            # Goals weights
            "goals_expected_total": 0.45,      # Primary driver
            "goals_home_attack": 0.18,
            "goals_away_attack": 0.12,
            "goals_h2h": 0.10,
            "goals_league_context": 0.15,
            
            # Corners weights
            "corners_home_avg": 0.30,
            "corners_away_avg": 0.30,
            "corners_h2h": 0.15,
            "corners_shots_proxy": 0.25,
        }
    
    def analyze_match(self,
                      home_stats: Dict,
                      away_stats: Dict,
                      home_recent: List[Dict],
                      away_recent: List[Dict],
                      h2h: List[Dict],
                      league_info: Dict,
                      match_info: Dict,
                      corners_data: Dict = None) -> List[ElitePrediction]:
        """
        Full match analysis - returns predictions for the 4 key markets.
        Now with hidden edge factors!
        """
        predictions = []
        
        # Extract core stats
        home_attack, home_defense = self._calculate_ratings(home_stats, is_home=True)
        away_attack, away_defense = self._calculate_ratings(away_stats, is_home=False)
        
        # ==================== HIDDEN EDGE ANALYSIS ====================
        home_patterns = self.hidden_edge.analyze_scoring_patterns(home_recent, match_info.get("home_id", 0))
        away_patterns = self.hidden_edge.analyze_scoring_patterns(away_recent, match_info.get("away_id", 0))
        
        home_droughts = self.hidden_edge.analyze_drought_breakers(home_recent, match_info.get("home_id", 0))
        away_droughts = self.hidden_edge.analyze_drought_breakers(away_recent, match_info.get("away_id", 0))
        
        h2h_psychology = self.hidden_edge.analyze_h2h_psychology(h2h, match_info.get("home_id", 0), match_info.get("away_id", 0))
        
        home_splits = self.hidden_edge.analyze_form_splits(home_stats, home_recent, match_info.get("home_id", 0))
        away_splits = self.hidden_edge.analyze_form_splits(away_stats, away_recent, match_info.get("away_id", 0))
        
        # Get hidden edge multipliers
        edge_multipliers = self.hidden_edge.get_hidden_edge_multipliers(
            home_patterns, away_patterns,
            home_droughts, away_droughts,
            h2h_psychology,
            home_splits, away_splits
        )
        # ==============================================================
        
        # Situational adjustments
        home_motivation = self.situational.get_motivation_factor(
            match_info.get("home_position", 10), 20,
            match_info.get("matchweek", 20), 38
        )
        away_motivation = self.situational.get_motivation_factor(
            match_info.get("away_position", 10), 20,
            match_info.get("matchweek", 20), 38
        )
        
        home_fatigue = self.situational.get_fatigue_factor(
            match_info.get("home_days_since_last", 7)
        )
        away_fatigue = self.situational.get_fatigue_factor(
            match_info.get("away_days_since_last", 7)
        )
        
        # Adjust ratings
        home_attack *= home_motivation * home_fatigue
        away_attack *= away_motivation * away_fatigue
        
        # Revenge factor from H2H
        home_attack *= h2h_psychology.get("revenge_factor", 1.0)
        
        # Home advantage
        home_adv = self.situational.get_home_advantage(
            league_info.get("league_id", 39),
            self._get_form(home_recent, True),
            self._get_form(away_recent, False)
        )
        home_attack *= home_adv
        away_defense *= (2 - home_adv)  # Inverse effect on away defense
        
        # Expected goals
        league_avg = league_info.get("avg_goals", 2.7)
        home_xg, away_xg = self.poisson.calculate_expected_goals(
            home_attack, home_defense, away_attack, away_defense,
            league_info.get("league_id", 39), league_avg
        )
        
        # Apply timing adjustment (midweek, early kickoff, etc.)
        timing_adj = match_info.get("timing_goals_adjustment", 1.0)
        season_adj = match_info.get("season_context_adjustment", 1.0)
        combined_timing_adj = timing_adj * season_adj
        
        home_xg *= combined_timing_adj
        away_xg *= combined_timing_adj
        
        match_name = f"{match_info.get('home_name', 'Home')} vs {match_info.get('away_name', 'Away')}"
        
        # Build hidden insights for display
        hidden_insights = self._build_hidden_insights(
            home_droughts, away_droughts, h2h_psychology, 
            home_patterns, away_patterns, home_splits, away_splits
        )
        
        # ============ MARKET 1: OVER 1.5 GOALS ============
        over15_pred = self._predict_over_goals_v2(
            home_xg, away_xg, 1.5, h2h, league_avg, match_name,
            edge_multipliers.get("over_15", 1.0), hidden_insights
        )
        predictions.append(over15_pred)
        
        # ============ MARKET 2: BTTS ============
        btts_pred = self._predict_btts_v2(
            home_stats, away_stats, home_xg, away_xg, h2h, match_name,
            edge_multipliers, hidden_insights, home_droughts, away_droughts
        )
        predictions.append(btts_pred)
        
        # ============ MARKET 3: OVER 2.5 GOALS ============
        over25_pred = self._predict_over_goals_v2(
            home_xg, away_xg, 2.5, h2h, league_avg, match_name,
            edge_multipliers.get("over_25", 1.0), hidden_insights
        )
        predictions.append(over25_pred)
        
        # ============ MARKET 4: UNDER 3.5 GOALS ============
        under35_pred = self._predict_under_goals_v2(
            home_xg, away_xg, 3.5, h2h, league_avg, match_name,
            edge_multipliers.get("under_35", 1.0), hidden_insights
        )
        predictions.append(under35_pred)
        
        return predictions
    
    def _build_hidden_insights(self, home_droughts, away_droughts, 
                                h2h_psychology, home_patterns, away_patterns,
                                home_splits, away_splits) -> List[str]:
        """Build list of hidden edge insights for display."""
        insights = []
        
        # Drought insights
        if home_droughts.get("games_since_scored", 0) >= 2:
            insights.append(f"🚨 Home hasn't scored in {home_droughts['games_since_scored']} games (DESPERATE)")
        
        if away_droughts.get("games_since_scored", 0) >= 2:
            insights.append(f"🚨 Away hasn't scored in {away_droughts['games_since_scored']} games")
        
        if home_droughts.get("games_since_clean_sheet", 0) >= 5:
            insights.append(f"⚠️ Home no clean sheet in {home_droughts['games_since_clean_sheet']} games")
        
        if away_droughts.get("games_since_clean_sheet", 0) >= 5:
            insights.append(f"⚠️ Away no clean sheet in {away_droughts['games_since_clean_sheet']} games")
        
        # Streak insights
        if home_droughts.get("streak_length", 0) >= 3:
            streak_type = home_droughts.get("current_streak_type", "")
            insights.append(f"📊 Home on {home_droughts['streak_length']}-game {streak_type} streak")
        
        if away_droughts.get("streak_length", 0) >= 3:
            streak_type = away_droughts.get("current_streak_type", "")
            insights.append(f"📊 Away on {away_droughts['streak_length']}-game {streak_type} streak")
        
        # H2H insights
        if h2h_psychology.get("revenge_factor", 1.0) > 1.0:
            insights.append("🔥 REVENGE FACTOR: Home lost heavily in last H2H")
        elif h2h_psychology.get("revenge_factor", 1.0) < 1.0:
            insights.append("🔥 REVENGE FACTOR: Away lost heavily in last H2H")
        
        if h2h_psychology.get("avg_total_goals", 2.5) > 3.2:
            insights.append(f"⚡ H2H averages {h2h_psychology['avg_total_goals']:.1f} goals (HIGH SCORING)")
        
        if h2h_psychology.get("btts_rate", 0.5) > 0.75:
            insights.append(f"⚡ BTTS in {h2h_psychology['btts_rate']*100:.0f}% of H2H matches")
        
        # Form split insights
        if home_splits.get("is_home_team", False):
            insights.append("🏟️ Home team is a FORTRESS at home")
        
        if away_splits.get("is_away_team", False):
            insights.append("✈️ Away team is an AWAY SPECIALIST")
        
        # Late goals
        if home_patterns.get("late_goal_rate", 0) > 0.8:
            insights.append("⏰ Home are LATE GOAL specialists")
        
        if away_patterns.get("late_goal_rate", 0) > 0.8:
            insights.append("⏰ Away score lots of LATE GOALS")
        
        return insights[:6]  # Max 6 insights
    
    def _calculate_ratings(self, stats: Dict, is_home: bool) -> Tuple[float, float]:
        """Calculate attack and defense ratings from stats."""
        goals_for = stats.get("goals", {}).get("for", {}).get("average", {})
        goals_against = stats.get("goals", {}).get("against", {}).get("average", {})
        
        location = "home" if is_home else "away"
        
        # Get goals per game (attack strength)
        attack = float(goals_for.get(location, 0) or goals_for.get("total", 1.3))
        
        # Get goals conceded (defense weakness - higher = worse)
        defense = float(goals_against.get(location, 0) or goals_against.get("total", 1.3))
        
        # Normalize to ~1.0 average
        attack = attack / 1.3 if attack > 0 else 0.7
        defense = defense / 1.3 if defense > 0 else 0.8
        
        return attack, defense
    
    def _get_form(self, recent: List[Dict], is_home: bool) -> float:
        """Calculate recent form as points per game."""
        if not recent:
            return 1.5  # Default
        
        points = 0
        for match in recent[-5:]:
            home_goals = match.get("goals", {}).get("home", 0) or 0
            away_goals = match.get("goals", {}).get("away", 0) or 0
            
            if is_home:
                diff = home_goals - away_goals
            else:
                diff = away_goals - home_goals
            
            if diff > 0:
                points += 3
            elif diff == 0:
                points += 1
        
        return points / len(recent[-5:])
    
    def _predict_btts(self, home_stats: Dict, away_stats: Dict,
                      home_xg: float, away_xg: float,
                      h2h: List[Dict], match_name: str) -> ElitePrediction:
        """Generate BTTS prediction with full analysis."""
        
        # Poisson-based BTTS probability
        poisson_btts = self.poisson.prob_btts(home_xg, away_xg)
        
        # Statistical BTTS from failed-to-score rates
        home_fts = home_stats.get("failed_to_score", {}).get("home", 0) or 0
        home_games = home_stats.get("fixtures", {}).get("played", {}).get("home", 1) or 1
        home_fts_rate = home_fts / home_games
        
        away_fts = away_stats.get("failed_to_score", {}).get("away", 0) or 0
        away_games = away_stats.get("fixtures", {}).get("played", {}).get("away", 1) or 1
        away_fts_rate = away_fts / away_games
        
        # Clean sheet rates
        home_cs = home_stats.get("clean_sheet", {}).get("home", 0) or 0
        home_cs_rate = home_cs / home_games
        
        away_cs = away_stats.get("clean_sheet", {}).get("away", 0) or 0
        away_cs_rate = away_cs / away_games
        
        # Statistical BTTS estimate
        p_home_scores = (1 - home_fts_rate) * (1 - away_cs_rate * 0.5)
        p_away_scores = (1 - away_fts_rate) * (1 - home_cs_rate * 0.5)
        stat_btts = p_home_scores * p_away_scores
        
        # H2H factor
        if h2h:
            h2h_btts = sum(1 for m in h2h if (m.get("goals", {}).get("home", 0) or 0) > 0 
                          and (m.get("goals", {}).get("away", 0) or 0) > 0) / len(h2h)
        else:
            h2h_btts = 0.5
        
        # Weighted combination
        final_prob = (
            poisson_btts * 0.40 +   # Poisson model
            stat_btts * 0.45 +      # Statistical rates
            h2h_btts * 0.15         # H2H
        )
        
        # Determine prediction direction
        if final_prob >= 0.5:
            prediction = "YES"
            prob = final_prob
        else:
            prediction = "NO"
            prob = 1 - final_prob
        
        # Key factors
        factors = []
        warnings = []
        
        if home_fts_rate < 0.15:
            factors.append(f"Home scores in {(1-home_fts_rate)*100:.0f}% of home games")
        elif home_fts_rate > 0.35:
            factors.append(f"Home fails to score in {home_fts_rate*100:.0f}% of home games")
        
        if away_fts_rate < 0.20:
            factors.append(f"Away scores in {(1-away_fts_rate)*100:.0f}% of away games")
        elif away_fts_rate > 0.40:
            factors.append(f"Away fails to score in {away_fts_rate*100:.0f}% of away games")
        
        if home_cs_rate > 0.35:
            factors.append(f"Home keeps clean sheet {home_cs_rate*100:.0f}% at home")
        
        if h2h_btts > 0.7:
            factors.append(f"H2H: BTTS in {h2h_btts*100:.0f}% of meetings")
        elif h2h_btts < 0.3:
            factors.append(f"H2H: BTTS in only {h2h_btts*100:.0f}% of meetings")
        
        factors.append(f"Expected goals: {home_xg:.1f} - {away_xg:.1f}")
        
        # Confidence calculation
        confidence = self._calculate_confidence(prob, home_games + away_games)
        
        # Value calculations
        fair_odds = self.value.prob_to_fair_odds(prob)
        min_odds = fair_odds * 1.03  # Need 3% edge
        kelly = self.value.kelly_criterion(prob, fair_odds)
        
        return ElitePrediction(
            match=match_name,
            market=f"BTTS {prediction}",
            prediction=prediction,
            our_probability=round(prob, 4),
            fair_odds=round(fair_odds, 2),
            min_acceptable_odds=round(min_odds, 2),
            confidence_score=confidence,
            confidence_tier=self._get_confidence_tier(confidence),
            kelly_fraction=round(kelly, 4),
            recommended_stake_pct=round(kelly * 100, 2),
            key_factors=factors[:4],
            warnings=warnings
        )
    
    def _predict_over_goals(self, home_xg: float, away_xg: float,
                            threshold: float, h2h: List[Dict],
                            league_avg: float, match_name: str) -> ElitePrediction:
        """Generate Over X.5 Goals prediction."""
        
        # Poisson probability
        prob_over = self.poisson.prob_over_goals(home_xg, away_xg, threshold)
        
        # H2H adjustment
        if h2h:
            h2h_over = sum(1 for m in h2h if 
                          ((m.get("goals", {}).get("home", 0) or 0) + 
                           (m.get("goals", {}).get("away", 0) or 0)) > threshold) / len(h2h)
            prob_over = prob_over * 0.85 + h2h_over * 0.15
        
        # Determine direction
        if prob_over >= 0.5:
            prediction = "OVER"
            prob = prob_over
        else:
            prediction = "UNDER"
            prob = 1 - prob_over
        
        # Key factors
        total_xg = home_xg + away_xg
        factors = [
            f"Expected total: {total_xg:.2f} goals",
            f"Home xG: {home_xg:.2f}",
            f"Away xG: {away_xg:.2f}",
            f"League avg: {league_avg:.1f} goals"
        ]
        
        warnings = []
        if total_xg < threshold - 0.3 and prediction == "OVER":
            warnings.append("Expected goals below threshold - risky OVER")
        if total_xg > threshold + 0.5 and prediction == "UNDER":
            warnings.append("Expected goals above threshold - risky UNDER")
        
        confidence = self._calculate_confidence(prob, 20)
        fair_odds = self.value.prob_to_fair_odds(prob)
        min_odds = fair_odds * 1.03
        kelly = self.value.kelly_criterion(prob, fair_odds)
        
        return ElitePrediction(
            match=match_name,
            market=f"{prediction} {threshold} GOALS",
            prediction=prediction,
            our_probability=round(prob, 4),
            fair_odds=round(fair_odds, 2),
            min_acceptable_odds=round(min_odds, 2),
            confidence_score=confidence,
            confidence_tier=self._get_confidence_tier(confidence),
            kelly_fraction=round(kelly, 4),
            recommended_stake_pct=round(kelly * 100, 2),
            key_factors=factors,
            warnings=warnings
        )
    
    def _predict_btts_v2(self, home_stats: Dict, away_stats: Dict,
                         home_xg: float, away_xg: float,
                         h2h: List[Dict], match_name: str,
                         edge_multipliers: Dict, hidden_insights: List[str],
                         home_droughts: Dict, away_droughts: Dict) -> ElitePrediction:
        """Generate BTTS prediction with hidden edge factors."""
        
        # Poisson-based BTTS probability
        poisson_btts = self.poisson.prob_btts(home_xg, away_xg)
        
        # Statistical BTTS from failed-to-score rates
        home_fts = home_stats.get("failed_to_score", {}).get("home", 0) or 0
        home_games = home_stats.get("fixtures", {}).get("played", {}).get("home", 1) or 1
        home_fts_rate = home_fts / home_games
        
        away_fts = away_stats.get("failed_to_score", {}).get("away", 0) or 0
        away_games = away_stats.get("fixtures", {}).get("played", {}).get("away", 1) or 1
        away_fts_rate = away_fts / away_games
        
        # Clean sheet rates
        home_cs = home_stats.get("clean_sheet", {}).get("home", 0) or 0
        home_cs_rate = home_cs / home_games
        
        away_cs = away_stats.get("clean_sheet", {}).get("away", 0) or 0
        away_cs_rate = away_cs / away_games
        
        # Statistical BTTS estimate
        p_home_scores = (1 - home_fts_rate) * (1 - away_cs_rate * 0.5)
        p_away_scores = (1 - away_fts_rate) * (1 - home_cs_rate * 0.5)
        stat_btts = p_home_scores * p_away_scores
        
        # H2H factor
        if h2h:
            h2h_btts = sum(1 for m in h2h if (m.get("goals", {}).get("home", 0) or 0) > 0 
                          and (m.get("goals", {}).get("away", 0) or 0) > 0) / len(h2h)
        else:
            h2h_btts = 0.5
        
        # Weighted combination
        final_prob = (
            poisson_btts * 0.35 +   # Poisson model
            stat_btts * 0.45 +      # Statistical rates
            h2h_btts * 0.20         # H2H (increased weight)
        )
        
        # Apply hidden edge multipliers
        btts_yes_mult = edge_multipliers.get("btts_yes", 1.0)
        btts_no_mult = edge_multipliers.get("btts_no", 1.0)
        
        # Determine prediction direction with multipliers
        adjusted_yes = final_prob * btts_yes_mult
        adjusted_no = (1 - final_prob) * btts_no_mult
        
        if adjusted_yes >= adjusted_no:
            prediction = "YES"
            prob = min(0.92, adjusted_yes / (adjusted_yes + adjusted_no))
        else:
            prediction = "NO"
            prob = min(0.92, adjusted_no / (adjusted_yes + adjusted_no))
        
        # Key factors
        factors = []
        warnings = []
        
        if prediction == "YES":
            if home_fts_rate < 0.20:
                factors.append(f"✅ Home scores in {(1-home_fts_rate)*100:.0f}% of home games")
            if away_fts_rate < 0.25:
                factors.append(f"✅ Away scores in {(1-away_fts_rate)*100:.0f}% of away games")
            if home_cs_rate < 0.25:
                factors.append(f"✅ Home keeps few clean sheets ({home_cs_rate*100:.0f}%)")
            if h2h_btts > 0.6:
                factors.append(f"✅ BTTS in {h2h_btts*100:.0f}% of H2H")
        else:
            if home_cs_rate > 0.35:
                factors.append(f"🛡️ Home CS rate: {home_cs_rate*100:.0f}%")
            if away_fts_rate > 0.35:
                factors.append(f"🛡️ Away FTS rate: {away_fts_rate*100:.0f}%")
            if away_cs_rate > 0.30:
                factors.append(f"🛡️ Away CS rate: {away_cs_rate*100:.0f}%")
        
        factors.append(f"📊 Expected: {home_xg:.1f} - {away_xg:.1f}")
        
        # Add hidden insights
        factors.extend(hidden_insights[:2])
        
        # Warnings based on droughts
        if home_droughts.get("games_since_scored", 0) >= 3 and prediction == "YES":
            warnings.append("⚠️ Home on goal drought - risky for BTTS Yes")
        if away_droughts.get("games_since_scored", 0) >= 3 and prediction == "YES":
            warnings.append("⚠️ Away on goal drought - risky for BTTS Yes")
        
        # Confidence calculation
        confidence = self._calculate_confidence(prob, home_games + away_games)
        
        # Value calculations
        fair_odds = self.value.prob_to_fair_odds(prob)
        min_odds = fair_odds * 1.03  # Need 3% edge
        kelly = self.value.kelly_criterion(prob, fair_odds)
        
        return ElitePrediction(
            match=match_name,
            market=f"BTTS {prediction}",
            prediction=prediction,
            our_probability=round(prob, 4),
            fair_odds=round(fair_odds, 2),
            min_acceptable_odds=round(min_odds, 2),
            confidence_score=confidence,
            confidence_tier=self._get_confidence_tier(confidence),
            kelly_fraction=round(kelly, 4),
            recommended_stake_pct=round(kelly * 100, 2),
            key_factors=factors[:5],
            warnings=warnings
        )
    
    def _predict_over_goals_v2(self, home_xg: float, away_xg: float,
                               threshold: float, h2h: List[Dict],
                               league_avg: float, match_name: str,
                               edge_multiplier: float,
                               hidden_insights: List[str]) -> ElitePrediction:
        """Generate Over X.5 Goals prediction with hidden edges."""
        
        # Poisson probability
        prob_over = self.poisson.prob_over_goals(home_xg, away_xg, threshold)
        
        # H2H adjustment
        if h2h:
            h2h_over = sum(1 for m in h2h if 
                          ((m.get("goals", {}).get("home", 0) or 0) + 
                           (m.get("goals", {}).get("away", 0) or 0)) > threshold) / len(h2h)
            prob_over = prob_over * 0.80 + h2h_over * 0.20
        
        # Apply hidden edge multiplier
        prob_over = min(0.95, prob_over * edge_multiplier)
        
        # Always predict OVER for these markets (we want value on overs)
        prediction = "OVER"
        prob = prob_over
        
        # Key factors
        total_xg = home_xg + away_xg
        factors = [
            f"📊 Expected total: {total_xg:.2f} goals",
            f"🏠 Home xG: {home_xg:.2f}",
            f"✈️ Away xG: {away_xg:.2f}",
        ]
        
        # Add H2H info
        if h2h:
            h2h_avg = sum((m.get("goals", {}).get("home", 0) or 0) + 
                          (m.get("goals", {}).get("away", 0) or 0) for m in h2h) / len(h2h)
            factors.append(f"📜 H2H avg: {h2h_avg:.1f} goals")
        
        # Add hidden insights
        factors.extend(hidden_insights[:2])
        
        warnings = []
        if total_xg < threshold:
            warnings.append(f"⚠️ Expected goals ({total_xg:.1f}) below threshold ({threshold})")
        
        if prob < 0.55:
            warnings.append("⚠️ Low confidence - consider skipping")
        
        confidence = self._calculate_confidence(prob, 20)
        fair_odds = self.value.prob_to_fair_odds(prob)
        min_odds = fair_odds * 1.03
        kelly = self.value.kelly_criterion(prob, fair_odds)
        
        return ElitePrediction(
            match=match_name,
            market=f"OVER {threshold} GOALS",
            prediction=prediction,
            our_probability=round(prob, 4),
            fair_odds=round(fair_odds, 2),
            min_acceptable_odds=round(min_odds, 2),
            confidence_score=confidence,
            confidence_tier=self._get_confidence_tier(confidence),
            kelly_fraction=round(kelly, 4),
            recommended_stake_pct=round(kelly * 100, 2),
            key_factors=factors[:5],
            warnings=warnings
        )
    
    def _predict_under_goals_v2(self, home_xg: float, away_xg: float,
                                threshold: float, h2h: List[Dict],
                                league_avg: float, match_name: str,
                                edge_multiplier: float,
                                hidden_insights: List[str]) -> ElitePrediction:
        """Generate Under X.5 Goals prediction with hidden edges."""
        
        # Poisson probability
        prob_over = self.poisson.prob_over_goals(home_xg, away_xg, threshold)
        prob_under = 1 - prob_over
        
        # H2H adjustment
        if h2h:
            h2h_under = sum(1 for m in h2h if 
                          ((m.get("goals", {}).get("home", 0) or 0) + 
                           (m.get("goals", {}).get("away", 0) or 0)) <= threshold) / len(h2h)
            prob_under = prob_under * 0.80 + h2h_under * 0.20
        
        # Apply hidden edge multiplier
        prob_under = min(0.95, prob_under * edge_multiplier)
        
        prediction = "UNDER"
        prob = prob_under
        
        # Key factors
        total_xg = home_xg + away_xg
        factors = [
            f"📊 Expected total: {total_xg:.2f} goals",
            f"🏠 Home xG: {home_xg:.2f}",
            f"✈️ Away xG: {away_xg:.2f}",
        ]
        
        if total_xg < threshold:
            factors.append(f"✅ xG ({total_xg:.1f}) below threshold ({threshold})")
        
        # Add hidden insights
        factors.extend(hidden_insights[:2])
        
        warnings = []
        if total_xg > threshold:
            warnings.append(f"⚠️ Expected goals ({total_xg:.1f}) ABOVE threshold")
        
        if prob < 0.55:
            warnings.append("⚠️ Low confidence - consider skipping")
        
        confidence = self._calculate_confidence(prob, 20)
        fair_odds = self.value.prob_to_fair_odds(prob)
        min_odds = fair_odds * 1.03
        kelly = self.value.kelly_criterion(prob, fair_odds)
        
        return ElitePrediction(
            match=match_name,
            market=f"UNDER {threshold} GOALS",
            prediction=prediction,
            our_probability=round(prob, 4),
            fair_odds=round(fair_odds, 2),
            min_acceptable_odds=round(min_odds, 2),
            confidence_score=confidence,
            confidence_tier=self._get_confidence_tier(confidence),
            kelly_fraction=round(kelly, 4),
            recommended_stake_pct=round(kelly * 100, 2),
            key_factors=factors[:5],
            warnings=warnings
        )
    
    def _predict_corners(self, corners_data: Dict, match_name: str) -> ElitePrediction:
        """Generate corners prediction."""
        home_corners = corners_data.get("home_corners_per_game", 5.0)
        away_corners = corners_data.get("away_corners_per_game", 5.0)
        expected_total = corners_data.get("expected_total_corners", 10.0)
        
        # Corners roughly follow Poisson but with higher variance
        threshold = 9.5
        
        # Simple probability estimate
        # Using normal approximation for sum of corners
        mean = expected_total
        std = 3.5  # Typical corner standard deviation
        
        prob_over = 1 - stats.norm.cdf(threshold, mean, std)
        
        if prob_over >= 0.5:
            prediction = "OVER"
            prob = prob_over
        else:
            prediction = "UNDER"
            prob = 1 - prob_over
        
        factors = [
            f"Expected corners: {expected_total:.1f}",
            f"Home avg: {home_corners:.1f}",
            f"Away avg: {away_corners:.1f}",
        ]
        
        confidence = self._calculate_confidence(prob, 15) * 0.85  # Corners less reliable
        fair_odds = self.value.prob_to_fair_odds(prob)
        kelly = self.value.kelly_criterion(prob, fair_odds)
        
        return ElitePrediction(
            match=match_name,
            market=f"{prediction} 9.5 CORNERS",
            prediction=prediction,
            our_probability=round(prob, 4),
            fair_odds=round(fair_odds, 2),
            min_acceptable_odds=round(fair_odds * 1.05, 2),  # Need more edge for corners
            confidence_score=confidence,
            confidence_tier=self._get_confidence_tier(confidence),
            kelly_fraction=round(kelly, 4),
            recommended_stake_pct=round(kelly * 100, 2),
            key_factors=factors,
            warnings=["Corners are more volatile than goals markets"]
        )
    
    def _calculate_confidence(self, prob: float, sample_size: int) -> float:
        """
        Calculate confidence score 0-100 based on:
        - Distance from 50% (stronger signal = higher confidence)
        - Sample size (more data = more confidence)
        """
        # Signal strength: how far from 50%
        signal = abs(prob - 0.5) * 2  # 0 to 1
        
        # Sample factor: diminishing returns after ~30 games
        sample_factor = min(1.0, sample_size / 30)
        
        # Combined score
        confidence = signal * 60 + sample_factor * 40
        
        return min(95, confidence)  # Cap at 95
    
    def _get_confidence_tier(self, score: float) -> str:
        if score >= 80:
            return "🏆 PLATINUM"
        elif score >= 65:
            return "🥇 GOLD"
        elif score >= 50:
            return "🥈 SILVER"
        else:
            return "🥉 BRONZE"


# Singleton
elite_predictor = ElitePredictor()


def format_prediction(pred: ElitePrediction) -> str:
    """Format prediction for display."""
    output = []
    output.append(f"\n{'='*60}")
    output.append(f"📊 {pred.market}")
    output.append(f"{'='*60}")
    output.append(f"Match: {pred.match}")
    output.append(f"")
    output.append(f"🎯 PREDICTION: {pred.prediction}")
    output.append(f"📈 Our Probability: {pred.our_probability:.1%}")
    output.append(f"💰 Fair Odds: {pred.fair_odds}")
    output.append(f"⚡ Min Acceptable Odds: {pred.min_acceptable_odds}")
    output.append(f"")
    output.append(f"🏅 Confidence: {pred.confidence_tier} ({pred.confidence_score:.0f}/100)")
    output.append(f"📊 Kelly Stake: {pred.recommended_stake_pct:.2f}% of bankroll")
    output.append(f"")
    output.append(f"🔑 KEY FACTORS:")
    for factor in pred.key_factors:
        output.append(f"   • {factor}")
    if pred.warnings:
        output.append(f"")
        output.append(f"⚠️ WARNINGS:")
        for warning in pred.warnings:
            output.append(f"   • {warning}")
    
    return "\n".join(output)
