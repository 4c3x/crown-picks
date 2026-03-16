"""
🔄 AUTO-IMPROVE SYSTEM v1.0
============================
Runs every 3 days to check accuracy and auto-tune the predictor.

Goal: 80% accuracy
- If >= 80% in last 3 days → Do nothing
- If < 80% → Analyze failures and adjust parameters

Usage:
    python scripts/auto_improve.py          # Run check and improve if needed
    python scripts/auto_improve.py --force  # Force improvement even if >= 80%
    python scripts/auto_improve.py --dry    # Show what would change without applying
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
import csv
import re

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Config
PREDICTIONS_CSV = Path(__file__).parent.parent / "output" / "basketball_predictions.csv"
TEAM_PREDICTIONS_CSV = Path(__file__).parent.parent / "output" / "team_predictions.csv"
PREDICTOR_FILE = Path(__file__).parent.parent / "basketball" / "predictor.py"
TARGET_ACCURACY = 0.80
CHECK_DAYS = 3
MIN_PREDICTIONS_TO_ADJUST = 3  # Need at least 3 predictions to make changes

# Current tunable parameters and their limits
TUNABLE_PARAMS = {
    "UNDER_BIAS_ADJUSTMENT": {"min": 0.0, "max": 15.0, "step": 2.0, "default": 6.0},
    "UNDER_PROBABILITY_PENALTY": {"min": 0.0, "max": 0.25, "step": 0.03, "default": 0.12},
    "market_blend_weight": {"min": 0.15, "max": 0.50, "step": 0.05, "default": 0.30},
    "variance_multiplier": {"min": 1.2, "max": 2.0, "step": 0.1, "default": 1.50},
}


def load_predictions(days_back=CHECK_DAYS):
    """Load predictions from the last N days that have results."""
    if not PREDICTIONS_CSV.exists():
        print("❌ No predictions file found")
        return []
    
    predictions = []
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
    
    with open(PREDICTIONS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # Only include predictions with results
                if not row.get('result') or row['result'] not in ['✅ WIN', '❌ LOSS']:
                    continue
                
                # Parse prediction date
                pred_date_str = row.get('prediction_date', '')
                if not pred_date_str:
                    continue
                    
                pred_date = datetime.fromisoformat(pred_date_str.replace('Z', '+00:00'))
                
                if pred_date >= cutoff_date:
                    predictions.append({
                        'date': pred_date,
                        'fixture': row.get('fixture', ''),
                        'prediction': row.get('prediction', ''),
                        'line': float(row.get('line', 0)),
                        'expected': float(row.get('expected_total', 0)),
                        'probability': row.get('our_probability', '0%').replace('%', ''),
                        'result': row.get('result', ''),
                        'final_total': float(row.get('final_total', 0)) if row.get('final_total') else 0,
                        'margin': row.get('margin', '0'),
                        'league': row.get('fixture', '').split(' vs ')[0] if ' vs ' in row.get('fixture', '') else ''
                    })
            except Exception as e:
                continue
    
    return predictions


def calculate_accuracy(predictions):
    """Calculate win rate from predictions."""
    if not predictions:
        return 0.0, 0, 0
    
    wins = sum(1 for p in predictions if p['result'] == '✅ WIN')
    total = len(predictions)
    accuracy = wins / total if total > 0 else 0.0
    
    return accuracy, wins, total


def analyze_failures(predictions):
    """Analyze what's going wrong with failed predictions."""
    analysis = {
        "total": len(predictions),
        "wins": 0,
        "losses": 0,
        "under_picks": 0,
        "under_wins": 0,
        "over_picks": 0,
        "over_wins": 0,
        "avg_margin_loss": 0,
        "close_losses": 0,  # Lost by < 5 points
        "blowout_losses": 0,  # Lost by > 15 points
        "expected_vs_actual_diff": [],  # How far off our expected was
    }
    
    loss_margins = []
    
    for p in predictions:
        is_win = p['result'] == '✅ WIN'
        
        if is_win:
            analysis["wins"] += 1
        else:
            analysis["losses"] += 1
        
        # Track OVER vs UNDER performance
        if p['prediction'] == 'UNDER':
            analysis["under_picks"] += 1
            if is_win:
                analysis["under_wins"] += 1
        else:
            analysis["over_picks"] += 1
            if is_win:
                analysis["over_wins"] += 1
        
        # Track margins for losses
        if not is_win:
            try:
                margin_str = p.get('margin', '0').replace('+', '').replace('-', '')
                margin = abs(float(margin_str))
                loss_margins.append(margin)
                
                if margin < 5:
                    analysis["close_losses"] += 1
                elif margin > 15:
                    analysis["blowout_losses"] += 1
            except:
                pass
        
        # Track expected vs actual difference
        if p['expected'] > 0 and p['final_total'] > 0:
            diff = p['final_total'] - p['expected']
            analysis["expected_vs_actual_diff"].append(diff)
    
    if loss_margins:
        analysis["avg_margin_loss"] = sum(loss_margins) / len(loss_margins)
    
    return analysis


def get_current_param_value(param_name):
    """Read current value of a parameter from predictor.py."""
    with open(PREDICTOR_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match self.PARAM_NAME = VALUE or self.param_name = VALUE
    pattern = rf'self\.{param_name}\s*=\s*([\d.]+)'
    match = re.search(pattern, content)
    
    if match:
        return float(match.group(1))
    return TUNABLE_PARAMS.get(param_name, {}).get('default', 0)


def update_param_value(param_name, new_value):
    """Update a parameter value in predictor.py."""
    with open(PREDICTOR_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match and replace
    pattern = rf'(self\.{param_name}\s*=\s*)([\d.]+)'
    
    def replacer(match):
        return f"{match.group(1)}{new_value}"
    
    new_content, count = re.subn(pattern, replacer, content)
    
    if count > 0:
        with open(PREDICTOR_FILE, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False


def calculate_adjustments(analysis, current_accuracy):
    """Determine what parameter changes to make based on failure analysis."""
    adjustments = {}
    reasons = []
    
    # Calculate how far from target we are
    accuracy_gap = TARGET_ACCURACY - current_accuracy
    
    # ===== UNDER vs OVER ANALYSIS =====
    under_rate = analysis["under_wins"] / analysis["under_picks"] if analysis["under_picks"] > 0 else 0
    over_rate = analysis["over_wins"] / analysis["over_picks"] if analysis["over_picks"] > 0 else 0
    
    current_under_bias = get_current_param_value("UNDER_BIAS_ADJUSTMENT")
    current_under_penalty = get_current_param_value("UNDER_PROBABILITY_PENALTY")
    
    # If UNDER is performing badly
    if analysis["under_picks"] > 0 and under_rate < 0.5:
        # Increase bias adjustment (push toward OVER)
        new_bias = min(
            TUNABLE_PARAMS["UNDER_BIAS_ADJUSTMENT"]["max"],
            current_under_bias + TUNABLE_PARAMS["UNDER_BIAS_ADJUSTMENT"]["step"]
        )
        if new_bias != current_under_bias:
            adjustments["UNDER_BIAS_ADJUSTMENT"] = new_bias
            reasons.append(f"UNDER win rate only {under_rate:.0%} - increasing OVER bias")
        
        # Increase penalty
        new_penalty = min(
            TUNABLE_PARAMS["UNDER_PROBABILITY_PENALTY"]["max"],
            current_under_penalty + TUNABLE_PARAMS["UNDER_PROBABILITY_PENALTY"]["step"]
        )
        if new_penalty != current_under_penalty:
            adjustments["UNDER_PROBABILITY_PENALTY"] = new_penalty
            reasons.append(f"Penalizing UNDER picks more")
    
    # If OVER is performing badly but UNDER is good
    elif analysis["over_picks"] > 0 and over_rate < 0.5 and under_rate >= 0.6:
        # Decrease bias adjustment (push toward UNDER)
        new_bias = max(
            TUNABLE_PARAMS["UNDER_BIAS_ADJUSTMENT"]["min"],
            current_under_bias - TUNABLE_PARAMS["UNDER_BIAS_ADJUSTMENT"]["step"]
        )
        if new_bias != current_under_bias:
            adjustments["UNDER_BIAS_ADJUSTMENT"] = new_bias
            reasons.append(f"OVER win rate only {over_rate:.0%} but UNDER at {under_rate:.0%} - reducing OVER bias")
        
        # Decrease penalty
        new_penalty = max(
            TUNABLE_PARAMS["UNDER_PROBABILITY_PENALTY"]["min"],
            current_under_penalty - TUNABLE_PARAMS["UNDER_PROBABILITY_PENALTY"]["step"]
        )
        if new_penalty != current_under_penalty:
            adjustments["UNDER_PROBABILITY_PENALTY"] = new_penalty
            reasons.append(f"Reducing UNDER penalty")
    
    # ===== EXPECTED VS ACTUAL ANALYSIS =====
    if analysis["expected_vs_actual_diff"]:
        avg_diff = sum(analysis["expected_vs_actual_diff"]) / len(analysis["expected_vs_actual_diff"])
        
        # If actual is consistently higher than expected (games going OVER)
        if avg_diff > 5:
            current_bias = get_current_param_value("UNDER_BIAS_ADJUSTMENT")
            new_bias = min(
                TUNABLE_PARAMS["UNDER_BIAS_ADJUSTMENT"]["max"],
                current_bias + TUNABLE_PARAMS["UNDER_BIAS_ADJUSTMENT"]["step"]
            )
            if new_bias != current_bias and "UNDER_BIAS_ADJUSTMENT" not in adjustments:
                adjustments["UNDER_BIAS_ADJUSTMENT"] = new_bias
                reasons.append(f"Actual totals avg +{avg_diff:.1f} vs expected - boosting expected")
        
        # If actual is consistently lower than expected (games going UNDER)
        elif avg_diff < -5:
            current_bias = get_current_param_value("UNDER_BIAS_ADJUSTMENT")
            new_bias = max(
                TUNABLE_PARAMS["UNDER_BIAS_ADJUSTMENT"]["min"],
                current_bias - TUNABLE_PARAMS["UNDER_BIAS_ADJUSTMENT"]["step"]
            )
            if new_bias != current_bias and "UNDER_BIAS_ADJUSTMENT" not in adjustments:
                adjustments["UNDER_BIAS_ADJUSTMENT"] = new_bias
                reasons.append(f"Actual totals avg {avg_diff:.1f} vs expected - reducing expected")
    
    # ===== CLOSE LOSSES ANALYSIS =====
    if analysis["close_losses"] > analysis["losses"] * 0.5:
        # Many close losses - might need to adjust variance
        current_var = get_current_param_value("variance_multiplier")
        new_var = min(
            TUNABLE_PARAMS["variance_multiplier"]["max"],
            current_var + TUNABLE_PARAMS["variance_multiplier"]["step"]
        )
        if new_var != current_var:
            adjustments["variance_multiplier"] = round(new_var, 2)
            reasons.append(f"{analysis['close_losses']} close losses - increasing variance buffer")
    
    # ===== BLOWOUT LOSSES =====
    if analysis["blowout_losses"] >= 2:
        # Getting crushed - trust market more
        current_blend = get_current_param_value("market_blend_weight")
        new_blend = max(
            TUNABLE_PARAMS["market_blend_weight"]["min"],
            current_blend - TUNABLE_PARAMS["market_blend_weight"]["step"]
        )
        if new_blend != current_blend:
            adjustments["market_blend_weight"] = round(new_blend, 2)
            reasons.append(f"{analysis['blowout_losses']} blowout losses - trusting market more")
    
    return adjustments, reasons


def run_auto_improve(force=False, dry_run=False):
    """Main function to check and improve the system."""
    print("\n" + "="*60)
    print("🔄 AUTO-IMPROVE SYSTEM v1.0")
    print("="*60)
    print(f"📅 Checking last {CHECK_DAYS} days of predictions...")
    print(f"🎯 Target accuracy: {TARGET_ACCURACY:.0%}")
    print()
    
    # Load predictions
    predictions = load_predictions(CHECK_DAYS)
    
    if len(predictions) < MIN_PREDICTIONS_TO_ADJUST:
        print(f"⚠️  Only {len(predictions)} predictions with results (need {MIN_PREDICTIONS_TO_ADJUST}+)")
        print("    Not enough data to make adjustments. Run more predictions first.")
        return
    
    # Calculate accuracy
    accuracy, wins, total = calculate_accuracy(predictions)
    
    print(f"📊 Results: {wins}W - {total - wins}L ({accuracy:.1%} accuracy)")
    print()
    
    # Check if we're at target
    if accuracy >= TARGET_ACCURACY and not force:
        print(f"✅ ACCURACY AT OR ABOVE TARGET ({accuracy:.1%} >= {TARGET_ACCURACY:.0%})")
        print("   No changes needed. System is performing well!")
        print()
        print("   Current parameters:")
        for param in TUNABLE_PARAMS:
            val = get_current_param_value(param)
            print(f"   • {param}: {val}")
        return
    
    if force:
        print(f"⚠️  FORCE MODE - Analyzing even though accuracy is {accuracy:.1%}")
    else:
        print(f"❌ ACCURACY BELOW TARGET ({accuracy:.1%} < {TARGET_ACCURACY:.0%})")
    
    print()
    print("🔍 Analyzing failures...")
    
    # Analyze what went wrong
    analysis = analyze_failures(predictions)
    
    print(f"   • UNDER picks: {analysis['under_picks']} ({analysis['under_wins']}W)")
    print(f"   • OVER picks: {analysis['over_picks']} ({analysis['over_wins']}W)")
    print(f"   • Close losses (<5 pts): {analysis['close_losses']}")
    print(f"   • Blowout losses (>15 pts): {analysis['blowout_losses']}")
    
    if analysis["expected_vs_actual_diff"]:
        avg_diff = sum(analysis["expected_vs_actual_diff"]) / len(analysis["expected_vs_actual_diff"])
        print(f"   • Avg expected vs actual: {avg_diff:+.1f} pts")
    
    print()
    
    # Calculate adjustments
    adjustments, reasons = calculate_adjustments(analysis, accuracy)
    
    if not adjustments:
        print("🤔 No clear adjustments to make based on analysis.")
        print("   The failures may be due to variance rather than systematic bias.")
        return
    
    print("📝 PROPOSED ADJUSTMENTS:")
    for reason in reasons:
        print(f"   • {reason}")
    print()
    
    print("🔧 PARAMETER CHANGES:")
    for param, new_val in adjustments.items():
        old_val = get_current_param_value(param)
        direction = "↑" if new_val > old_val else "↓"
        print(f"   • {param}: {old_val} → {new_val} {direction}")
    print()
    
    if dry_run:
        print("🔍 DRY RUN - No changes applied")
        return
    
    # Apply adjustments
    print("⚙️  Applying changes...")
    for param, new_val in adjustments.items():
        success = update_param_value(param, new_val)
        if success:
            print(f"   ✅ Updated {param}")
        else:
            print(f"   ❌ Failed to update {param}")
    
    print()
    print("✅ AUTO-IMPROVEMENT COMPLETE")
    print("   Restart the Flask server to apply changes.")
    print("   Run 'python app.py' to start with new parameters.")


def show_status():
    """Show current system status and parameters."""
    print("\n" + "="*60)
    print("📊 CROWN PICKS - SYSTEM STATUS")
    print("="*60)
    
    # Load all-time predictions
    all_preds = load_predictions(days_back=30)
    last_3_days = load_predictions(days_back=3)
    
    print("\n📈 TOTAL POINTS MARKET:")
    if all_preds:
        acc_all, w_all, t_all = calculate_accuracy(all_preds)
        print(f"   Last 30 days: {w_all}W - {t_all - w_all}L ({acc_all:.1%})")
    
    if last_3_days:
        acc_3, w_3, t_3 = calculate_accuracy(last_3_days)
        print(f"   Last 3 days:  {w_3}W - {t_3 - w_3}L ({acc_3:.1%})")
    
    # Load team predictions
    print("\n🏀 TEAM POINTS MARKET:")
    team_stats = load_team_prediction_stats()
    if team_stats["total"] > 0:
        print(f"   Overall: {team_stats['wins']}W - {team_stats['losses']}L ({team_stats['accuracy']:.1%})")
        if team_stats["home_total"] > 0:
            print(f"   🏠 Home: {team_stats['home_wins']}W - {team_stats['home_total'] - team_stats['home_wins']}L ({team_stats['home_accuracy']:.1%})")
        if team_stats["away_total"] > 0:
            print(f"   ✈️ Away: {team_stats['away_wins']}W - {team_stats['away_total'] - team_stats['away_wins']}L ({team_stats['away_accuracy']:.1%})")
    else:
        print("   No completed team predictions yet")
    
    print(f"\n🎯 Target: {TARGET_ACCURACY:.0%}")
    
    print("\n⚙️  Current Parameters:")
    for param, config in TUNABLE_PARAMS.items():
        val = get_current_param_value(param)
        print(f"   • {param}: {val} (range: {config['min']}-{config['max']})")


def load_team_prediction_stats():
    """Load team prediction stats."""
    stats = {"total": 0, "wins": 0, "losses": 0, "home_wins": 0, "home_total": 0, "away_wins": 0, "away_total": 0, "accuracy": 0, "home_accuracy": 0, "away_accuracy": 0}
    
    if not TEAM_PREDICTIONS_CSV.exists():
        return stats
    
    with open(TEAM_PREDICTIONS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            result = row.get('result', '')
            team_type = row.get('team_type', '')
            
            if result == '✅ WIN':
                stats["wins"] += 1
                stats["total"] += 1
                if team_type == 'HOME':
                    stats["home_wins"] += 1
                    stats["home_total"] += 1
                else:
                    stats["away_wins"] += 1
                    stats["away_total"] += 1
            elif result == '❌ LOSS':
                stats["losses"] += 1
                stats["total"] += 1
                if team_type == 'HOME':
                    stats["home_total"] += 1
                else:
                    stats["away_total"] += 1
    
    stats["accuracy"] = (stats["wins"] / stats["total"]) if stats["total"] > 0 else 0
    stats["home_accuracy"] = (stats["home_wins"] / stats["home_total"]) if stats["home_total"] > 0 else 0
    stats["away_accuracy"] = (stats["away_wins"] / stats["away_total"]) if stats["away_total"] > 0 else 0
    
    return stats


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Auto-improve prediction system")
    parser.add_argument("--force", action="store_true", help="Force improvement even if >= 80%")
    parser.add_argument("--dry", action="store_true", help="Dry run - show changes without applying")
    parser.add_argument("--status", action="store_true", help="Show current status only")
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
    else:
        run_auto_improve(force=args.force, dry_run=args.dry)
