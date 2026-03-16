"""
Confidence Filter
=================
The most critical component for achieving high accuracy.

This module decides which matches to SKIP based on:
1. Data quality issues
2. Match context (derbies, cup games, dead rubbers)
3. Prediction uncertainty
4. Volatility indicators

Philosophy: Skip 85-90% of matches. Only predict when signals are strong.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from config.settings import CONFIDENCE_FILTERS, LEAGUES, get_league_info

logger = logging.getLogger(__name__)


@dataclass
class FilterResult:
    """Result of filtering decision."""
    should_predict: bool
    confidence_tier: str  # "SKIP", "LOW", "MEDIUM", "HIGH", "VERY_HIGH"
    rejection_reasons: List[str]
    quality_score: float  # 0-1, composite quality metric
    adjusted_probability: float  # Probability after adjustments


class ConfidenceFilter:
    """
    Multi-stage filter to identify high-confidence betting opportunities.
    
    Stage 1: Data Quality Filter
        - Do we have enough historical data?
        - Is the data recent enough?
        
    Stage 2: Context Filter
        - Is this a "trap" match? (derby, cup, dead rubber)
        - Is this a reliable league?
        
    Stage 3: Probability Filter
        - Is the probability high enough?
        - Is the model confident enough?
        
    Stage 4: Volatility Filter
        - Are the teams' results consistent?
        - Is there unusual uncertainty?
    """
    
    def __init__(self):
        self.config = CONFIDENCE_FILTERS
        self.derby_pairs = self._load_derby_pairs()
        
    def _load_derby_pairs(self) -> Dict[int, List[Tuple[int, int]]]:
        """
        Known derby matchups to avoid.
        Format: {league_id: [(team1_id, team2_id), ...]}
        """
        return {
            # Premier League
            39: [
                (33, 34),   # Man Utd vs Man City
                (40, 42),   # Liverpool vs Everton
                (47, 48),   # Tottenham vs Arsenal
                (49, 52),   # Chelsea vs Crystal Palace (London)
            ],
            # La Liga
            140: [
                (529, 530), # Barcelona vs Real Madrid
                (531, 532), # Athletic vs Real Sociedad (Basque)
                (533, 541), # Atletico vs Real Madrid
            ],
            # Bundesliga
            78: [
                (157, 165), # Bayern vs Dortmund
                (172, 182), # Schalke vs Dortmund (if Schalke promoted)
            ],
            # Serie A
            135: [
                (489, 496), # AC Milan vs Inter (Derby della Madonnina)
                (492, 487), # Juventus vs Torino (Derby della Mole)
                (497, 492), # Roma vs Lazio (Derby della Capitale)
            ],
            # Ligue 1
            61: [
                (80, 81),   # Lyon vs Saint-Etienne
                (85, 91),   # PSG vs Marseille (Le Classique)
            ],
        }
        
    def filter(self, 
               match_info: Dict,
               features: Dict[str, float],
               raw_probability: float,
               market: str) -> FilterResult:
        """
        Apply all filtering stages to a match.
        
        Args:
            match_info: Basic match data (teams, league, date, matchweek)
            features: Extracted features for the market
            raw_probability: Model's raw prediction
            market: Market type (BTTS, OVER_25_GOALS, etc.)
            
        Returns:
            FilterResult with decision and reasoning
        """
        rejection_reasons = []
        quality_score = 1.0
        
        # =====================================================================
        # STAGE 1: DATA QUALITY
        # =====================================================================
        
        # Check minimum matches played
        home_matches = match_info.get("home_matches_played", 0)
        away_matches = match_info.get("away_matches_played", 0)
        min_required = self.config["min_historical_matches"]
        
        if home_matches < min_required:
            rejection_reasons.append(f"Home team only played {home_matches} matches (need {min_required})")
            quality_score *= 0.5
            
        if away_matches < min_required:
            rejection_reasons.append(f"Away team only played {away_matches} matches (need {min_required})")
            quality_score *= 0.5
            
        # Check recency
        home_last_match = match_info.get("home_days_since_last", 0)
        away_last_match = match_info.get("away_days_since_last", 0)
        max_days = self.config["max_days_since_last_match"]
        
        if home_last_match > max_days:
            rejection_reasons.append(f"Home team hasn't played in {home_last_match} days")
            quality_score *= 0.7
            
        if away_last_match > max_days:
            rejection_reasons.append(f"Away team hasn't played in {away_last_match} days")
            quality_score *= 0.7
            
        # =====================================================================
        # STAGE 2: CONTEXT FILTER
        # =====================================================================
        
        league_id = match_info.get("league_id")
        league_info = get_league_info(league_id)
        
        # Skip unreliable leagues
        if not league_info:
            rejection_reasons.append("League not in supported list")
            quality_score *= 0.3
            
        # Apply tier weighting
        tier = league_info.get("tier", "TIER_2")
        tier_weight = (self.config["tier_1_weight"] if tier == "TIER_1" 
                      else self.config["tier_2_weight"])
        quality_score *= tier_weight
        
        # Skip season openers
        matchweek = match_info.get("matchweek", 20)
        if matchweek <= 1 and self.config["skip_matchweek_1"]:
            rejection_reasons.append("Season opener - unpredictable")
            quality_score *= 0.4
            
        # Skip end-of-season dead rubbers
        total_matchweeks = match_info.get("total_matchweeks", 38)
        if matchweek >= total_matchweeks - 2 and self.config["skip_final_3_matchweeks"]:
            # Check if teams still have something to play for
            home_position = match_info.get("home_position", 10)
            away_position = match_info.get("away_position", 10)
            
            # Mid-table clash at end of season = dead rubber
            if 8 <= home_position <= 14 and 8 <= away_position <= 14:
                rejection_reasons.append("End of season dead rubber")
                quality_score *= 0.5
                
        # Skip derbies
        if self.config["skip_derbies"]:
            home_id = match_info.get("home_team_id")
            away_id = match_info.get("away_team_id")
            
            if self._is_derby(league_id, home_id, away_id):
                rejection_reasons.append("Derby match - volatile")
                quality_score *= 0.4
                
        # Skip cup matches
        if self.config["skip_cup_matches"]:
            is_cup = match_info.get("is_cup", False)
            if is_cup:
                rejection_reasons.append("Cup match - rotation risk")
                quality_score *= 0.5
                
        # =====================================================================
        # STAGE 3: PROBABILITY FILTER
        # =====================================================================
        
        min_prob = self.config["min_probability_to_bet"]
        
        # For binary markets, we can bet on either side
        effective_prob = max(raw_probability, 1 - raw_probability)
        
        if effective_prob < min_prob:
            rejection_reasons.append(
                f"Probability {effective_prob:.1%} below threshold {min_prob:.1%}"
            )
            
        # =====================================================================
        # STAGE 4: VOLATILITY FILTER
        # =====================================================================
        
        # Check form volatility (inconsistent teams are harder to predict)
        home_form_vol = features.get("home_form_volatility", 0.3)
        away_form_vol = features.get("away_form_volatility", 0.3)
        max_vol = self.config["max_form_volatility"]
        
        if home_form_vol > max_vol:
            rejection_reasons.append(f"Home team form volatile ({home_form_vol:.2f})")
            quality_score *= 0.8
            
        if away_form_vol > max_vol:
            rejection_reasons.append(f"Away team form volatile ({away_form_vol:.2f})")
            quality_score *= 0.8
            
        # =====================================================================
        # FINAL DECISION
        # =====================================================================
        
        # Adjust probability by quality score
        adjusted_prob = self._adjust_probability(effective_prob, quality_score)
        
        # Determine confidence tier
        confidence_tier = self._get_confidence_tier(adjusted_prob, quality_score, rejection_reasons)
        
        # Should we predict?
        should_predict = (
            confidence_tier in ["MEDIUM", "HIGH", "VERY_HIGH"] and
            len([r for r in rejection_reasons if "below threshold" not in r]) <= 1
        )
        
        return FilterResult(
            should_predict=should_predict,
            confidence_tier=confidence_tier,
            rejection_reasons=rejection_reasons,
            quality_score=quality_score,
            adjusted_probability=adjusted_prob
        )
        
    def _is_derby(self, league_id: int, home_id: int, away_id: int) -> bool:
        """Check if this is a known derby match."""
        if league_id not in self.derby_pairs:
            return False
            
        for team1, team2 in self.derby_pairs[league_id]:
            if (home_id == team1 and away_id == team2) or \
               (home_id == team2 and away_id == team1):
                return True
        return False
        
    def _adjust_probability(self, prob: float, quality: float) -> float:
        """
        Adjust probability toward 50% based on quality score.
        
        Low quality = more uncertainty = regress toward 0.5
        """
        # Regression factor: 1.0 = no regression, 0.0 = full regression to 0.5
        regression = 0.5 + (quality * 0.5)
        
        adjusted = prob * regression + 0.5 * (1 - regression)
        return adjusted
        
    def _get_confidence_tier(self, prob: float, quality: float, 
                             reasons: List[str]) -> str:
        """Determine overall confidence tier."""
        
        # Too many red flags
        if len(reasons) >= 3:
            return "SKIP"
            
        # Quality too low
        if quality < 0.5:
            return "SKIP"
            
        # Probability-based tiers
        effective_prob = max(prob, 1 - prob)
        
        if effective_prob >= self.config["very_high_confidence_threshold"] and quality >= 0.85:
            return "VERY_HIGH"
        elif effective_prob >= self.config["high_confidence_threshold"] and quality >= 0.75:
            return "HIGH"
        elif effective_prob >= self.config["min_probability_to_bet"] and quality >= 0.6:
            return "MEDIUM"
        elif effective_prob >= 0.58:
            return "LOW"
        else:
            return "SKIP"
            
    def get_filter_summary(self, results: List[FilterResult]) -> Dict:
        """
        Summarize filtering results across multiple matches.
        
        This helps track:
        - What % of matches we're skipping
        - Most common rejection reasons
        - Distribution of confidence tiers
        """
        total = len(results)
        if total == 0:
            return {}
            
        tier_counts = {"SKIP": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 0, "VERY_HIGH": 0}
        all_reasons = []
        
        for r in results:
            tier_counts[r.confidence_tier] += 1
            all_reasons.extend(r.rejection_reasons)
            
        # Count reason frequency
        from collections import Counter
        reason_counts = Counter(all_reasons).most_common(10)
        
        return {
            "total_matches": total,
            "predicted": sum(1 for r in results if r.should_predict),
            "skipped": sum(1 for r in results if not r.should_predict),
            "skip_rate": tier_counts["SKIP"] / total,
            "tier_distribution": {k: v/total for k, v in tier_counts.items()},
            "top_rejection_reasons": reason_counts,
            "avg_quality_score": np.mean([r.quality_score for r in results]),
        }


# Singleton
confidence_filter = ConfidenceFilter()
