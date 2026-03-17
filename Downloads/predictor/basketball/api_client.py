"""
API-Basketball Data Client
===========================
Handles all basketball API interactions with rate limiting and caching.

API-Basketball is part of the same API-Sports family as API-Football.
Uses the same API key and similar structure.
"""

import time
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

from config.settings import (
    BASKETBALL_API_BASE_URL, BASKETBALL_API_HEADERS,
    BASKETBALL_API_RATE_LIMIT, DATA_DIR
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supported basketball leagues
BASKETBALL_LEAGUES = {
    # NBA
    12: {"name": "NBA", "country": "USA", "avg_total": 224.5, "home_advantage": 3.5},
    # EuroLeague
    120: {"name": "EuroLeague", "country": "Europe", "avg_total": 160.0, "home_advantage": 4.0},
    # NCAA
    116: {"name": "NCAA", "country": "USA", "avg_total": 140.0, "home_advantage": 5.0},
    # Spanish Liga ACB
    117: {"name": "Liga ACB", "country": "Spain", "avg_total": 162.0, "home_advantage": 4.5},
    # Turkish BSL
    145: {"name": "Turkish BSL", "country": "Turkey", "avg_total": 158.0, "home_advantage": 5.0},
    # Australian NBL
    20: {"name": "NBL Australia", "country": "Australia", "avg_total": 175.0, "home_advantage": 4.0},
    # Chinese CBA
    99: {"name": "CBA China", "country": "China", "avg_total": 195.0, "home_advantage": 5.5},
}


class BasketballAPIClient:
    """
    Client for API-Basketball with rate limiting and local caching.
    """
    
    def __init__(self, cache_enabled: bool = True):
        self.base_url = BASKETBALL_API_BASE_URL
        self.headers = BASKETBALL_API_HEADERS
        self.cache_enabled = cache_enabled
        self.cache_dir = Path(DATA_DIR) / "cache" / "basketball"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._last_request_time = 0
        self._requests_this_minute = 0
        
    def _rate_limit(self):
        """Enforce rate limiting (small sleeps to avoid worker kills)."""
        current_time = time.time()
        
        if current_time - self._last_request_time > 60:
            self._requests_this_minute = 0
            
        if self._requests_this_minute >= BASKETBALL_API_RATE_LIMIT:
            sleep_time = 60 - (current_time - self._last_request_time)
            if sleep_time > 0:
                logger.info(f"Rate limit reached. Waiting {sleep_time:.1f}s...")
                # Sleep in 2-second chunks so gunicorn worker stays alive
                while sleep_time > 0:
                    time.sleep(min(2, sleep_time))
                    sleep_time -= 2
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
                cache_hours: int = 24, max_retries: int = 2) -> Optional[Dict]:
        """Make an API request with caching, rate limiting, and retry logic.
        
        Args:
            endpoint: API endpoint to call
            params: Query parameters
            cache_hours: Cache duration in hours
            max_retries: Number of retry attempts (default: 2)
        """
        params = params or {}
        cache_path = self._get_cache_path(endpoint, params)
        
        cached = self._load_from_cache(cache_path, cache_hours)
        if cached:
            logger.debug(f"Cache hit: {endpoint}")
            return cached
            
        self._rate_limit()
        url = f"{self.base_url}/{endpoint}"
        
        # Retry logic with shorter timeout
        for attempt in range(max_retries + 1):
            try:
                # Reduced timeout: 10 seconds (was 30)
                # This fails faster on slow/unresponsive requests
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
    # BASKETBALL-SPECIFIC ENDPOINTS
    # =========================================================================
    
    def get_upcoming_games(self, league_id: int = None, 
                           next_days: int = 3,
                           season: str = None) -> List[Dict]:
        """Get upcoming basketball games.
        
        Args:
            league_id: Optional league filter
            next_days: Number of days ahead (for cache logic)
            season: Season string. Free plans only support 2022-2024.
                    For NBA/NCAA: use year like "2023-2024"
                    Defaults to 2023-2024 (last fully available season)
        """
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Use 2023-2024 season by default (most recent on free plan)
        # Free API only supports 2022-2024
        if season is None:
            season = "2023-2024"
        
        params = {"date": today, "season": season}
        if league_id:
            params["league"] = league_id
            
        response = self.request("games", params, cache_hours=1)
        games = response.get("response", []) if response else []
        
        # Filter to supported leagues if no specific league
        if not league_id:
            games = [g for g in games 
                    if g.get("league", {}).get("id") in BASKETBALL_LEAGUES]
        
        # Filter to upcoming (not started)
        games = [g for g in games if g.get("status", {}).get("short") == "NS"]
        
        return games
    
    def get_team_statistics(self, team_id: int, league_id: int, 
                            season: str) -> Optional[Dict]:
        """Get seasonal statistics for a basketball team."""
        params = {"team": team_id, "league": league_id, "season": season}
        response = self.request("statistics", params, cache_hours=12)
        return response.get("response") if response else None
    
    def get_team_games(self, team_id: int, season: str, 
                       last: int = 10) -> List[Dict]:
        """Get team's recent games."""
        params = {"team": team_id, "season": season}
        response = self.request("games", params, cache_hours=6)
        
        if not response:
            return []
        
        games = response.get("response", [])
        
        # Filter to finished games only
        finished = [g for g in games 
                   if g.get("status", {}).get("short") == "FT"]
        
        # Sort by date descending and take last N
        finished.sort(key=lambda x: x.get("date", ""), reverse=True)
        
        return finished[:last]
    
    def get_head_to_head(self, team1_id: int, team2_id: int, 
                         last: int = 10) -> List[Dict]:
        """Get head-to-head history between two teams."""
        h2h_str = f"{team1_id}-{team2_id}"
        params = {"h2h": h2h_str}
        response = self.request("games", params, cache_hours=168)
        
        games = response.get("response", []) if response else []
        
        # Filter to finished games
        finished = [g for g in games 
                   if g.get("status", {}).get("short") == "FT"]
        
        return finished[:last]
    
    def get_standings(self, league_id: int, season: str) -> List[Dict]:
        """Get league standings."""
        params = {"league": league_id, "season": season}
        response = self.request("standings", params, cache_hours=6)
        
        if response and response.get("response"):
            standings = response["response"]
            if standings and len(standings) > 0:
                return standings[0]  # First group/conference
        return []
    
    def get_odds(self, game_id: int) -> Dict:
        """Get betting odds for a game."""
        params = {"game": game_id}
        response = self.request("odds", params, cache_hours=1)
        
        if not response or not response.get("response"):
            return {}
        
        odds_data = response["response"]
        if not odds_data:
            return {}
        
        # Parse odds
        parsed = {
            "bookmakers": [],
            "totals": {},  # Over/Under lines
            "spreads": {},
            "moneylines": {},
        }
        
        for bookie in odds_data[0].get("bookmakers", []):
            bookie_name = bookie.get("name")
            parsed["bookmakers"].append(bookie_name)
            
            for bet in bookie.get("bets", []):
                bet_name = bet.get("name", "")
                
                if "Over/Under" in bet_name or "Total" in bet_name:
                    for value in bet.get("values", []):
                        line = value.get("value", "")
                        odd = float(value.get("odd", 0))
                        
                        if line not in parsed["totals"]:
                            parsed["totals"][line] = []
                        parsed["totals"][line].append({
                            "bookmaker": bookie_name,
                            "odds": odd
                        })
        
        return parsed
    
    def get_game_statistics(self, game_id: int) -> List[Dict]:
        """Get detailed statistics for a specific game."""
        params = {"id": game_id}
        response = self.request("games/statistics", params, cache_hours=168)
        return response.get("response", []) if response else []
    
    def get_game_by_id(self, game_id: int, bypass_cache: bool = False) -> Optional[Dict]:
        """Get a specific game by ID (to check final scores).
        
        Args:
            game_id: The game ID to fetch
            bypass_cache: If True, bypass cache to get fresh data (for result updates)
        """
        params = {"id": game_id}
        cache_hours = 0 if bypass_cache else 6
        response = self.request("games", params, cache_hours=cache_hours)
        
        if response and response.get("response"):
            games = response["response"]
            if games:
                return games[0]
        return None


# Singleton instance
basketball_api = BasketballAPIClient()


def test_basketball_connection() -> bool:
    """Test basketball API connection."""
    client = BasketballAPIClient(cache_enabled=False)
    response = client.request("status", {}, cache_hours=0)
    
    if response and response.get("response"):
        status = response["response"]
        print(f"✓ Basketball API Connection Successful")
        print(f"  Plan: {status.get('subscription', {}).get('plan')}")
        print(f"  Requests today: {status.get('requests', {}).get('current')}")
        return True
    else:
        print("✗ Basketball API Connection Failed")
        return False


if __name__ == "__main__":
    test_basketball_connection()
