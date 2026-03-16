"""
⏰ SCHEDULER - Auto-run improvement check every 3 days
======================================================
This script can be:
1. Run manually: python scripts/scheduler.py
2. Set up as Windows Task Scheduler task
3. Run as a background daemon

It checks if 3 days have passed since last improvement check,
and runs auto_improve.py if needed.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import json
import subprocess

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

SCHEDULE_FILE = Path(__file__).parent.parent / "data" / "scheduler_state.json"
CHECK_INTERVAL_DAYS = 3


def load_state():
    """Load scheduler state from file."""
    if SCHEDULE_FILE.exists():
        try:
            with open(SCHEDULE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"last_check": None, "checks_run": 0}


def save_state(state):
    """Save scheduler state to file."""
    SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SCHEDULE_FILE, 'w') as f:
        json.dump(state, f, indent=2, default=str)


def should_run_check():
    """Determine if it's time to run the improvement check."""
    state = load_state()
    
    if state["last_check"] is None:
        return True
    
    try:
        last_check = datetime.fromisoformat(state["last_check"])
        next_check = last_check + timedelta(days=CHECK_INTERVAL_DAYS)
        return datetime.now() >= next_check
    except:
        return True


def run_improvement_check():
    """Run the auto-improvement script."""
    script_path = Path(__file__).parent / "auto_improve.py"
    python_exe = sys.executable
    
    print(f"🚀 Running auto-improvement check...")
    print(f"   Script: {script_path}")
    print()
    
    result = subprocess.run(
        [python_exe, str(script_path)],
        capture_output=False,
        text=True
    )
    
    # Update state
    state = load_state()
    state["last_check"] = datetime.now().isoformat()
    state["checks_run"] = state.get("checks_run", 0) + 1
    save_state(state)
    
    return result.returncode == 0


def main():
    """Main scheduler function."""
    print("\n" + "="*60)
    print("⏰ CROWN PICKS - SCHEDULER")
    print("="*60)
    
    state = load_state()
    
    if state["last_check"]:
        last = datetime.fromisoformat(state["last_check"])
        next_run = last + timedelta(days=CHECK_INTERVAL_DAYS)
        print(f"📅 Last check: {last.strftime('%Y-%m-%d %H:%M')}")
        print(f"📅 Next check: {next_run.strftime('%Y-%m-%d %H:%M')}")
        print(f"📊 Total checks run: {state.get('checks_run', 0)}")
    else:
        print("📅 No previous checks recorded")
    
    print()
    
    if should_run_check():
        print("✅ Time to run improvement check!")
        print()
        run_improvement_check()
    else:
        last = datetime.fromisoformat(state["last_check"])
        next_run = last + timedelta(days=CHECK_INTERVAL_DAYS)
        days_left = (next_run - datetime.now()).days
        hours_left = int((next_run - datetime.now()).total_seconds() / 3600) % 24
        print(f"⏳ Next check in {days_left} days, {hours_left} hours")
        print("   Run with --force to check now anyway")


def setup_windows_task():
    """Print instructions for setting up Windows Task Scheduler."""
    script_path = Path(__file__).absolute()
    python_exe = sys.executable
    
    print("\n" + "="*60)
    print("📋 WINDOWS TASK SCHEDULER SETUP")
    print("="*60)
    print("""
To run this automatically every 3 days:

1. Open Task Scheduler (taskschd.msc)
2. Click "Create Basic Task"
3. Name: "Crown Picks Auto-Improve"
4. Trigger: Daily (it will self-check if 3 days passed)
5. Action: Start a program
6. Program/script: """ + str(python_exe) + """
7. Arguments: """ + str(script_path) + """
8. Start in: """ + str(script_path.parent.parent) + """

Or run this PowerShell command (as Admin):
""")
    
    ps_command = f'''
$action = New-ScheduledTaskAction -Execute "{python_exe}" -Argument "{script_path}" -WorkingDirectory "{script_path.parent.parent}"
$trigger = New-ScheduledTaskTrigger -Daily -At 9am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName "CrownPicksAutoImprove" -Action $action -Trigger $trigger -Settings $settings -Description "Auto-improve basketball predictor every 3 days"
'''
    print(ps_command)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Scheduler for auto-improvement")
    parser.add_argument("--force", action="store_true", help="Force run check now")
    parser.add_argument("--setup", action="store_true", help="Show Windows Task Scheduler setup")
    
    args = parser.parse_args()
    
    if args.setup:
        setup_windows_task()
    elif args.force:
        print("\n⚡ FORCE MODE - Running check now...")
        run_improvement_check()
    else:
        main()
