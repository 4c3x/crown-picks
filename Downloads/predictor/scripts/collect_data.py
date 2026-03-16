"""
Data Collection Script
======================
Collects historical data for model training.
"""

import sys
from pathlib import Path
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    from data.collector import data_collector
    from config.settings import ALL_LEAGUE_IDS, LEAGUES
    
    print("="*60)
    print("DATA COLLECTION SCRIPT")
    print("="*60)
    print(f"\nCollecting data for {len(ALL_LEAGUE_IDS)} leagues")
    print("This will take approximately 30-60 minutes.\n")
    
    # Collect last 2 seasons
    seasons = [2024, 2023]
    
    print(f"Seasons: {seasons}")
    print(f"Leagues:")
    for tier, leagues in LEAGUES.items():
        print(f"  {tier}:")
        for lid, info in leagues.items():
            print(f"    - {info['name']} ({info['country']})")
    
    print("\n" + "-"*60)
    input("Press Enter to start collection (Ctrl+C to cancel)...")
    print("-"*60 + "\n")
    
    summary = data_collector.collect_all_leagues(seasons)
    
    print("\n" + "="*60)
    print("COLLECTION COMPLETE")
    print("="*60)
    print(f"Leagues processed: {summary['leagues']}")
    print(f"Total fixtures collected: {summary['fixtures']}")
    
    if summary['errors']:
        print(f"\nErrors ({len(summary['errors'])}):")
        for err in summary['errors'][:5]:
            print(f"  - {err}")


if __name__ == "__main__":
    main()
