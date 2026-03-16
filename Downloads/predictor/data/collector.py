"""
Data Collection Pipeline
========================
Fetches and stores historical data for model training.
Handles both initial collection and incremental updates.
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from config.settings import DATA_DIR, ALL_LEAGUE_IDS, LEAGUES
from data.api_client import APIFootballClient, api_client

logger = logging.getLogger(__name__)


class DataCollector:
    """
    Collects and stores historical match data for training.
    
    Data collected per match:
    - Basic fixture info (teams, date, score)
    - Match statistics (shots, corners, possession, xG)
    - Team seasonal stats
    - Head-to-head history
    """
    
    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir or DATA_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.api = api_client
        
    def collect_season_data(self, league_id: int, season: int) -> Dict:
        """
        Collect all data for a league season.
        
        Args:
            league_id: League ID
            season: Season year (e.g., 2024)
            
        Returns:
            Dict with fixtures, stats, etc.
        """
        logger.info(f"Collecting data for league {league_id}, season {season}")
        
        # Get all finished fixtures
        fixtures = self.api.get_fixtures(league_id, season, status="FT")
        logger.info(f"Found {len(fixtures)} finished fixtures")
        
        # Collect statistics for each fixture
        fixture_stats = {}
        for i, fixture in enumerate(fixtures):
            fixture_id = fixture["fixture"]["id"]
            stats = self.api.get_fixture_statistics(fixture_id)
            if stats:
                fixture_stats[fixture_id] = stats
                
            # Progress logging
            if (i + 1) % 20 == 0:
                logger.info(f"Collected stats for {i+1}/{len(fixtures)} fixtures")
                time.sleep(1)  # Respect rate limits
                
        # Get team statistics
        teams = set()
        for f in fixtures:
            teams.add(f["teams"]["home"]["id"])
            teams.add(f["teams"]["away"]["id"])
            
        team_stats = {}
        for team_id in teams:
            stats = self.api.get_team_statistics(team_id, league_id, season)
            if stats:
                team_stats[team_id] = stats
                
        # Get standings
        standings = self.api.get_standings(league_id, season)
        
        season_data = {
            "league_id": league_id,
            "season": season,
            "collected_at": datetime.now().isoformat(),
            "fixtures": fixtures,
            "fixture_stats": fixture_stats,
            "team_stats": team_stats,
            "standings": standings,
        }
        
        # Save to disk
        self._save_season_data(league_id, season, season_data)
        
        return season_data
        
    def collect_all_leagues(self, seasons: List[int] = None) -> Dict[str, int]:
        """
        Collect data for all supported leagues.
        
        Args:
            seasons: List of seasons to collect (default: last 3)
            
        Returns:
            Summary of collected data
        """
        if seasons is None:
            current_year = datetime.now().year
            # Current season + 2 previous
            seasons = [current_year - 1, current_year - 2, current_year - 3]
            
        summary = {"leagues": 0, "fixtures": 0, "errors": []}
        
        for league_id in ALL_LEAGUE_IDS:
            for season in seasons:
                try:
                    data = self.collect_season_data(league_id, season)
                    summary["fixtures"] += len(data.get("fixtures", []))
                    logger.info(f"✓ Collected league {league_id}, season {season}")
                except Exception as e:
                    error = f"League {league_id}, season {season}: {str(e)}"
                    summary["errors"].append(error)
                    logger.error(error)
                    
                time.sleep(2)  # Be nice to the API
                
            summary["leagues"] += 1
            
        return summary
        
    def load_season_data(self, league_id: int, season: int) -> Optional[Dict]:
        """Load previously collected season data."""
        path = self.data_dir / f"league_{league_id}_season_{season}.json"
        if not path.exists():
            return None
        with open(path, "r") as f:
            return json.load(f)
            
    def load_all_data(self) -> List[Dict]:
        """Load all collected season data."""
        all_data = []
        for path in self.data_dir.glob("league_*_season_*.json"):
            with open(path, "r") as f:
                all_data.append(json.load(f))
        return all_data
        
    def _save_season_data(self, league_id: int, season: int, data: Dict):
        """Save season data to disk."""
        path = self.data_dir / f"league_{league_id}_season_{season}.json"
        with open(path, "w") as f:
            json.dump(data, f)
        logger.info(f"Saved data to {path}")
        
    def get_data_summary(self) -> Dict:
        """Get summary of all collected data."""
        summary = {
            "leagues": set(),
            "seasons": set(),
            "total_fixtures": 0,
            "files": [],
        }
        
        for path in self.data_dir.glob("league_*_season_*.json"):
            parts = path.stem.split("_")
            league_id = int(parts[1])
            season = int(parts[3])
            
            summary["leagues"].add(league_id)
            summary["seasons"].add(season)
            summary["files"].append(path.name)
            
            # Quick fixture count
            with open(path, "r") as f:
                data = json.load(f)
                summary["total_fixtures"] += len(data.get("fixtures", []))
                
        summary["leagues"] = list(summary["leagues"])
        summary["seasons"] = list(summary["seasons"])
        
        return summary


# Singleton
data_collector = DataCollector()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Example: Collect Premier League 2024
    collector = DataCollector()
    data = collector.collect_season_data(39, 2024)
    print(f"Collected {len(data['fixtures'])} fixtures")
