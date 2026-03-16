"""
Quick Start Script
==================
Interactive walkthrough for first-time setup.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def main():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║           FOOTBALL PREDICTION SYSTEM - QUICK START               ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Markets: BTTS, Over/Under 2.5 Goals, Over/Under 9.5 Corners    ║
║  Leagues: Tier 1 + Tier 2 (EPL, La Liga, Bundesliga, etc.)      ║
║  Target: 70-78% accuracy on filtered predictions                ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    # Test API connection
    print("Step 1: Testing API connection...")
    print("-" * 50)
    
    from data.api_client import test_connection
    if test_connection():
        print("✓ API connection successful!\n")
    else:
        print("✗ API connection failed. Check your API key.\n")
        return
        
    # Check for existing data
    print("Step 2: Checking for historical data...")
    print("-" * 50)
    
    from data.collector import data_collector
    summary = data_collector.get_data_summary()
    
    if summary.get("total_fixtures", 0) > 0:
        print(f"✓ Found {summary['total_fixtures']} fixtures from {len(summary['leagues'])} leagues")
        print(f"  Seasons: {summary['seasons']}")
    else:
        print("✗ No historical data found.")
        print("\nTo collect data, run:")
        print("  python scripts/collect_data.py")
        print("\nOr collect a single league/season:")
        print("  from data.collector import data_collector")
        print("  data_collector.collect_season_data(39, 2024)  # Premier League 2024")
        
    # Check for trained models
    print("\nStep 3: Checking for trained models...")
    print("-" * 50)
    
    from config.settings import MODELS_DIR
    models_dir = Path(MODELS_DIR)
    models = list(models_dir.glob("*.pkl"))
    
    if models:
        print(f"✓ Found {len(models)} trained models:")
        for m in models:
            print(f"  - {m.name}")
    else:
        print("✗ No trained models found.")
        print("\nTo train models, run:")
        print("  python scripts/train_models.py")
        
    # Generate sample predictions
    print("\nStep 4: Sample prediction...")
    print("-" * 50)
    
    try:
        from pipeline.predictor import PredictionPipeline
        pipeline = PredictionPipeline()
        
        # Quick demo with one league
        from data.api_client import api_client
        fixtures = api_client.get_upcoming_fixtures(39)  # EPL
        
        if fixtures:
            print(f"✓ Found {len(fixtures)} upcoming EPL fixtures")
            fixture = fixtures[0]
            print(f"\nSample match: {fixture['teams']['home']['name']} vs {fixture['teams']['away']['name']}")
            print(f"Kickoff: {fixture['fixture']['date']}")
        else:
            print("No upcoming fixtures found")
            
    except Exception as e:
        print(f"Could not generate sample: {e}")
        
    # Next steps
    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print("""
1. COLLECT DATA (first time only, takes ~30 mins):
   python scripts/collect_data.py
   
2. TRAIN MODELS:
   python scripts/train_models.py
   
3. GENERATE DAILY PREDICTIONS:
   python -m pipeline.predictor
   
4. USE IN YOUR CODE:
   from predictor import get_recommended_bets
   bets = get_recommended_bets()
   for bet in bets:
       print(f"{bet['match']} - {bet['market']}: {bet['probability']:.0%}")
    """)
    
    # Honest expectations
    print("\n" + "=" * 60)
    print("REALISTIC EXPECTATIONS")
    print("=" * 60)
    print("""
┌─────────────────┬──────────────┬────────────────────────────────┐
│ Market          │ Expected Acc │ Notes                          │
├─────────────────┼──────────────┼────────────────────────────────┤
│ BTTS            │ 72-78%       │ Best signal, binary outcome    │
│ Over 2.5 Goals  │ 70-76%       │ Good data, Poisson helps       │
│ Over 9.5 Corners│ 65-72%       │ More volatile, less data       │
└─────────────────┴──────────────┴────────────────────────────────┘

NOTE: These are accuracy rates on FILTERED predictions only.
We skip 85%+ of matches where signals are weak.

80%+ sustained accuracy is not realistic for any market.
Anyone claiming otherwise is either lying or overfitting.

Focus on: Positive ROI > High raw accuracy
    """)


if __name__ == "__main__":
    main()
