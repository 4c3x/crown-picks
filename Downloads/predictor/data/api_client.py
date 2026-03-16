"""
API-Football Data Client
========================
Handles all API interactions with rate limiting and caching.
"""

import time
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

from config.settings import (
    API_BASE_URL, API_HEADERS, API_RATE_LIMIT, 
    DATA_DIR, ALL_LEAGUE_IDS
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class APIFootballClient:
    """
    Client for API-Football with rate limiting and local caching.
    """
    
    def __init__(self, cache_enabled: bool = True):
        self.base_url = API_BASE_URL
        self.headers = API_HEADERS
        self.cache_enabled = cache_enabled
        self.cache_dir = Path(DATA_DIR) / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._last_request_time = 0
        self._requests_this_minute = 0
        
    def _rate_limit(self):
        """Enforce rate limiting (10 requests/minute for Pro)."""
        current_time = time.time()
        
        # Reset counter every minute
        if current_time - self._last_request_time > 60:
            self._requests_this_minute = 0
            
        # Wait if we've hit the limit
        if self._requests_this_minute >= API_RATE_LIMIT:
            sleep_time = 60 - (current_time - self._last_request_time)
            if sleep_time > 0:
                logger.info(f"Rate limit reached. Sleeping {sleep_time:.1f}s...")
                time.sleep(sleep_time)
            self._requests_this_minute = 0
            
        self._last_request_time = current_time
        self._requests_this_minute += 1
        
    def _get_cache_path(self, endpoint: str, params: Dict) -> Path:
        """Generate cache file path for a request."""
        param_str = "_".join(f"{k}={v}" for k, v in sorted(params.items()))
        filename = f"{endpoint.replace('/', '_')}_{param_str}.json"
        return self.cache_dir / filename
        
    def _load_from_cache(self, cache_path: Path, max_age_hours: int = 24) -> Optional[Dict]:
        """Load data from cache if fresh enough."""
        if not self.cache_enabled or not cache_path.exists():
            return None
            
        # Check age
        mod_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        if datetime.now() - mod_time > timedelta(hours=max_age_hours):
            return None
            
        try:
            with open(cache_path, "r") as f:
                return json.load(f)
        except Exception:
            return None
            
    def _save_to_cache(self, cache_path: Path, data: Dict):
        """Save response to cache."""
        if not self.cache_enabled:
            return
        try:
            with open(cache_path, "w") as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning(f"Failed to cache: {e}")
    
    def request(self, endpoint: str, params: Dict = None, 
                cache_hours: int = 24) -> Optional[Dict]:
        """
        Make an API request with caching and rate limiting.
        
        Args:
            endpoint: API endpoint (e.g., "fixtures")
            params: Query parameters
            cache_hours: How long to cache results
            
        Returns:
            API response dict or None on error
        """
        params = params or {}
        cache_path = self._get_cache_path(endpoint, params)
        
        # Try cache first
        cached = self._load_from_cache(cache_path, cache_hours)
        if cached:
            logger.debug(f"Cache hit: {endpoint}")
            return cached
            
        # Make API request with retry logic
        self._rate_limit()
        url = f"{self.base_url}/{endpoint}"
        
        # Retry up to 2 times
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                # Reduced timeout: 10 seconds (was 30)
                # Fails faster on slow/unresponsive requests
                response = requests.get(url, headers=self.headers, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if data.get("errors"):
                    logger.error(f"API error: {data['errors']}")
                    return None
                    
                self._save_to_cache(cache_path, data)
                return data
                
            except requests.exceptions.Timeout as e:
                if attempt < max_retries:
                    logger.warning(f"Timeout on attempt {attempt + 1}/{max_retries + 1}, retrying...")
                    import time
                    time.sleep(1)  # Brief pause before retry
                else:
                    logger.error(f"Request timeout after {max_retries + 1} attempts: {e}")
                    return None
                    
            except requests.exceptions.RequestException as e:
                if attempt < max_retries:
                    logger.warning(f"Request failed on attempt {attempt + 1}/{max_retries + 1}, retrying...")
                    import time
                    time.sleep(1)
                else:
                    logger.error(f"Request failed after {max_retries + 1} attempts: {e}")
                    return None
        
        return None
            
    # =========================================================================
    # SPECIFIC ENDPOINTS
    # =========================================================================
    
    def get_fixtures(self, league_id: int, season: int, 
                     status: str = None) -> List[Dict]:
        """
        Get fixtures for a league/season.
        
        Args:
            league_id: League ID
            season: Season year (e.g., 2024)
            status: Filter by status (FT, NS, etc.)
        """
        params = {"league": league_id, "season": season}
        if status:
            params["status"] = status
            
        response = self.request("fixtures", params, cache_hours=1)
        return response.get("response", []) if response else []
    
    def get_fixture_by_id(self, fixture_id: int) -> Optional[Dict]:
        """Get a specific fixture by ID (to check final scores)."""
        params = {"id": fixture_id}
        response = self.request("fixtures", params, cache_hours=6)
        
        if response and response.get("response"):
            fixtures = response["response"]
            if fixtures:
                return fixtures[0]
        return None
        
    def get_fixture_statistics(self, fixture_id: int) -> Dict:
        """Get detailed statistics for a specific fixture."""
        params = {"fixture": fixture_id}
        response = self.request("fixtures/statistics", params, cache_hours=168)  # 1 week
        return response.get("response", []) if response else []
        
    def get_team_statistics(self, team_id: int, league_id: int, 
                            season: int) -> Optional[Dict]:
        """Get seasonal statistics for a team."""
        params = {"team": team_id, "league": league_id, "season": season}
        response = self.request("teams/statistics", params, cache_hours=24)
        return response.get("response") if response else None
        
    def get_standings(self, league_id: int, season: int) -> List[Dict]:
        """Get league standings."""
        params = {"league": league_id, "season": season}
        response = self.request("standings", params, cache_hours=6)
        if response and response.get("response"):
            return response["response"][0].get("league", {}).get("standings", [[]])[0]
        return []
        
    def get_head_to_head(self, team1_id: int, team2_id: int, 
                         last: int = 10) -> List[Dict]:
        """Get head-to-head history between two teams."""
        h2h_str = f"{team1_id}-{team2_id}"
        params = {"h2h": h2h_str, "last": last}
        response = self.request("fixtures/headtohead", params, cache_hours=168)
        return response.get("response", []) if response else []
        
    def get_upcoming_fixtures(self, league_id: int = None, 
                               next_days: int = 7) -> List[Dict]:
        """Get upcoming fixtures across leagues."""
        params = {"next": 50}  # Get next 50 fixtures
        if league_id:
            params["league"] = league_id
            
        response = self.request("fixtures", params, cache_hours=1)
        fixtures = response.get("response", []) if response else []
        
        # Filter to our supported leagues
        if not league_id:
            fixtures = [f for f in fixtures 
                       if f.get("league", {}).get("id") in ALL_LEAGUE_IDS]
                       
        return fixtures
        
    def get_fixture_events(self, fixture_id: int) -> List[Dict]:
        """Get match events (goals, cards, subs, etc.)."""
        params = {"fixture": fixture_id}
        response = self.request("fixtures/events", params, cache_hours=168)
        return response.get("response", []) if response else []
        
    def get_fixture_lineups(self, fixture_id: int) -> List[Dict]:
        """Get match lineups."""
        params = {"fixture": fixture_id}
        response = self.request("fixtures/lineups", params, cache_hours=168)
        return response.get("response", []) if response else []
    
    def get_team_recent_fixtures(self, team_id: int, last: int = 10) -> List[Dict]:
        """Get team's recent completed fixtures."""
        params = {"team": team_id, "last": last, "status": "FT"}
        response = self.request("fixtures", params, cache_hours=6)
        return response.get("response", []) if response else []
    
    def get_team_last_match_date(self, team_id: int) -> Optional[datetime]:
        """Get date of team's last completed match."""
        recent = self.get_team_recent_fixtures(team_id, last=1)
        if recent:
            date_str = recent[0]["fixture"]["date"]
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return None
    
    # =========================================================================
    # CRITICAL: xG, ODDS, INJURIES, REFEREE ENDPOINTS
    # =========================================================================
    
    def get_fixture_odds(self, fixture_id: int) -> Dict:
        """
        Get pre-match odds for a fixture from multiple bookmakers.
        
        Returns odds for 1X2, BTTS, Over/Under markets.
        """
        params = {"fixture": fixture_id}
        response = self.request("odds", params, cache_hours=1)  # Odds change frequently
        
        if not response or not response.get("response"):
            return {}
        
        odds_data = response["response"]
        if not odds_data:
            return {}
        
        # Parse odds into usable format
        parsed = {
            "bookmakers": [],
            "markets": {}
        }
        
        for bookie in odds_data[0].get("bookmakers", []):
            bookie_name = bookie.get("name")
            parsed["bookmakers"].append(bookie_name)
            
            for bet in bookie.get("bets", []):
                market_name = bet.get("name")
                if market_name not in parsed["markets"]:
                    parsed["markets"][market_name] = {}
                    
                for value in bet.get("values", []):
                    outcome = value.get("value")
                    odd = float(value.get("odd", 0))
                    
                    if outcome not in parsed["markets"][market_name]:
                        parsed["markets"][market_name][outcome] = []
                    parsed["markets"][market_name][outcome].append({
                        "bookmaker": bookie_name,
                        "odds": odd
                    })
        
        return parsed
    
    def get_best_odds(self, fixture_id: int, market: str, outcome: str) -> Optional[Dict]:
        """
        Get the best available odds for a specific market/outcome.
        
        Args:
            fixture_id: The fixture ID
            market: Market name (e.g., "Both Teams Score", "Over/Under")
            outcome: Outcome value (e.g., "Yes", "Over 2.5")
            
        Returns:
            Dict with best_odds, bookmaker, average_odds
        """
        all_odds = self.get_fixture_odds(fixture_id)
        if not all_odds or market not in all_odds.get("markets", {}):
            return None
        
        market_odds = all_odds["markets"].get(market, {}).get(outcome, [])
        if not market_odds:
            return None
        
        best = max(market_odds, key=lambda x: x["odds"])
        avg = sum(o["odds"] for o in market_odds) / len(market_odds)
        
        return {
            "best_odds": best["odds"],
            "best_bookmaker": best["bookmaker"],
            "average_odds": round(avg, 2),
            "num_bookmakers": len(market_odds)
        }
    
    def get_injuries(self, team_id: int, season: int = None) -> List[Dict]:
        """
        Get current injuries and suspensions for a team.
        
        CRITICAL: Key player absences affect predictions by 10-25%.
        """
        if season is None:
            season = datetime.now().year if datetime.now().month >= 7 else datetime.now().year - 1
        
        params = {"team": team_id, "season": season}
        response = self.request("injuries", params, cache_hours=2)  # Injuries change
        
        if not response:
            return []
        
        injuries = response.get("response", [])
        
        # Parse and categorize by severity
        parsed = []
        for inj in injuries:
            player = inj.get("player", {})
            team = inj.get("team", {})
            fixture = inj.get("fixture", {})
            
            parsed.append({
                "player_id": player.get("id"),
                "player_name": player.get("name"),
                "player_photo": player.get("photo"),
                "type": player.get("type"),  # "Missing Fixture", "Questionable", etc.
                "reason": player.get("reason"),  # "Injury", "Suspended", etc.
                "fixture_id": fixture.get("id"),
                "team_id": team.get("id"),
            })
        
        return parsed
    
    def get_team_injuries_summary(self, team_id: int, season: int = None) -> Dict:
        """
        Get summary of team's injury situation.
        
        Returns counts and key player status.
        """
        injuries = self.get_injuries(team_id, season)
        
        return {
            "total_out": len([i for i in injuries if i.get("type") == "Missing Fixture"]),
            "total_doubtful": len([i for i in injuries if i.get("type") == "Questionable"]),
            "injured": [i for i in injuries if i.get("reason") == "Injury"],
            "suspended": [i for i in injuries if i.get("reason") == "Suspended"],
            "all_absences": injuries
        }
    
    def get_fixture_referee(self, fixture_id: int) -> Optional[Dict]:
        """
        Get referee information for a fixture.
        
        Referees have measurable patterns in cards and fouls.
        """
        params = {"id": fixture_id}
        response = self.request("fixtures", params, cache_hours=6)
        
        if not response or not response.get("response"):
            return None
        
        fixture_data = response["response"][0]
        referee = fixture_data.get("fixture", {}).get("referee")
        
        if not referee:
            return None
        
        return {
            "name": referee,
            "fixture_id": fixture_id
        }
    
    def extract_xg_from_stats(self, fixture_stats: List[Dict]) -> Dict:
        """
        Extract xG (Expected Goals) from fixture statistics.
        
        xG is the MOST predictive single feature for goals markets.
        API-Football includes xG in fixture statistics for many leagues.
        """
        xg_data = {"home_xg": None, "away_xg": None}
        
        for team_stats in fixture_stats:
            team = team_stats.get("team", {})
            stats = team_stats.get("statistics", [])
            
            for stat in stats:
                if stat.get("type") == "expected_goals":
                    xg_value = stat.get("value")
                    if xg_value:
                        try:
                            xg = float(xg_value)
                            # Determine if home or away based on position in list
                            if xg_data["home_xg"] is None:
                                xg_data["home_xg"] = xg
                            else:
                                xg_data["away_xg"] = xg
                        except (ValueError, TypeError):
                            pass
        
        return xg_data
    
    def get_team_xg_history(self, team_id: int, last: int = 10) -> Dict:
        """
        Get rolling xG averages for a team.
        
        More reliable than actual goals for prediction.
        """
        recent = self.get_team_recent_fixtures(team_id, last=last)
        
        xg_for = []
        xg_against = []
        
        for fixture in recent:
            fixture_id = fixture.get("fixture", {}).get("id")
            if not fixture_id:
                continue
            
            stats = self.get_fixture_statistics(fixture_id)
            if not stats:
                continue
            
            xg = self.extract_xg_from_stats(stats)
            
            home_id = fixture.get("teams", {}).get("home", {}).get("id")
            is_home = (home_id == team_id)
            
            if xg["home_xg"] is not None and xg["away_xg"] is not None:
                if is_home:
                    xg_for.append(xg["home_xg"])
                    xg_against.append(xg["away_xg"])
                else:
                    xg_for.append(xg["away_xg"])
                    xg_against.append(xg["home_xg"])
        
        if not xg_for:
            return {"xg_for_avg": None, "xg_against_avg": None, "matches_with_xg": 0}
        
        return {
            "xg_for_avg": round(sum(xg_for) / len(xg_for), 2),
            "xg_against_avg": round(sum(xg_against) / len(xg_against), 2),
            "xg_for_total": xg_for,
            "xg_against_total": xg_against,
            "matches_with_xg": len(xg_for)
        }


# Singleton instance
api_client = APIFootballClient()


def test_connection() -> bool:
    """Test API connection and print account status."""
    client = APIFootballClient(cache_enabled=False)
    response = client.request("status", {}, cache_hours=0)
    
    if response and response.get("response"):
        status = response["response"]
        print(f"✓ API Connection Successful")
        print(f"  Plan: {status.get('subscription', {}).get('plan')}")
        print(f"  Requests today: {status.get('requests', {}).get('current')}")
        print(f"  Daily limit: {status.get('requests', {}).get('limit_day')}")
        return True
    else:
        print("✗ API Connection Failed")
        return False


if __name__ == "__main__":
    test_connection()
