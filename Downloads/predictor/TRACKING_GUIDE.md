# 📊 Prediction Tracking System

## Overview
The prediction tracking system automatically logs all predictions and updates final scores after games complete.

## Files

### Basketball Predictions
- **File**: `output/basketball_predictions.csv`
- **Tracker**: `basketball/prediction_tracker.py`

### Football Predictions  
- **File**: `output/football_predictions.csv`
- **Tracker**: `data/prediction_tracker.py`

## CSV Structure

### Basketball CSV Columns
1. **prediction_date** - When the prediction was made (UTC timestamp)
2. **game_date** - Scheduled game date/time
3. **game_id** - Unique game ID from API
4. **fixture** - Full fixture name (e.g., "Lakers vs Celtics")
5. **home_team** - Home team name
6. **away_team** - Away team name
7. **market** - Type of bet (e.g., "TOTAL POINTS", "Home POINTS")
8. **prediction** - Our prediction (e.g., "OVER", "UNDER")
9. **line** - The betting line (e.g., 227.5)
10. **expected_total** - Our expected total points
11. **expected_home** - Our expected home points
12. **expected_away** - Our expected away points
13. **our_probability** - Our calculated probability (e.g., "69.2%")
14. **confidence_tier** - Confidence level (GOLD/SILVER/BRONZE)
15. **final_total** - Actual total points (updated after game)
16. **final_home** - Actual home points (updated after game)
17. **final_away** - Actual away points (updated after game)
18. **result** - ✅ WIN or ❌ LOSS (updated after game)
19. **updated_date** - When results were updated

### Football CSV Columns
1. **prediction_date** - When the prediction was made
2. **game_date** - Scheduled game date/time
3. **fixture_id** - Unique fixture ID
4. **fixture** - Full fixture name
5. **home_team** - Home team name
6. **away_team** - Away team name
7. **market** - Type of bet (BTTS, Over/Under, 1X2)
8. **prediction** - Our prediction
9. **line** - The betting line/odds
10. **expected_home_goals** - Our expected home goals
11. **expected_away_goals** - Our expected away goals
12. **our_probability** - Our calculated probability
13. **bookmaker_probability** - Bookmaker's implied probability
14. **edge** - Our edge percentage
15. **confidence_tier** - Confidence level
16. **final_home_goals** - Actual home goals (updated after game)
17. **final_away_goals** - Actual away goals (updated after game)
18. **result** - ✅ WIN or ❌ LOSS (updated after game)
19. **updated_date** - When results were updated

## How It Works

### 1. Making Predictions
When you run a test (e.g., `python test_basketball.py`), the system:
- Analyzes the upcoming game
- Generates predictions with confidence levels
- **Automatically logs all predictions to the CSV file**

### 2. Updating Results (Automatic)
Every time you run the test script, the system:
- **Checks all previous predictions** that don't have final scores yet
- **Fetches game results** from the API for games that finished (4+ hours ago for basketball, 3+ hours for football)
- **Updates the CSV** with final scores and WIN/LOSS results
- **Shows statistics** (total predictions, win rate, accuracy)

### 3. Viewing Statistics
The system automatically displays stats at the start of each test run:
```
📊 PREDICTION TRACKER STATISTICS
======================================================================
Total Predictions: 15
Completed Games: 8
Pending Games: 7

Wins: 6 ✅
Losses: 2 ❌
Accuracy: 75.0%
======================================================================
```

## Example Workflow

### Basketball Example
```bash
# Day 1: Make predictions for today's games
python test_basketball.py
# CSV is created/updated with predictions (final scores empty)

# Day 2: Run again to check new games
python test_basketball.py
# System automatically:
# 1. Updates yesterday's games with final scores
# 2. Marks predictions as WIN/LOSS
# 3. Shows updated statistics
# 4. Makes predictions for new games
```

### Football Example
```bash
# Before the game
python elite_predictor.py
# Predictions logged to football_predictions.csv

# After the game (next day)
python elite_predictor.py
# Results automatically updated from API
```

## Key Features

### Automatic Updates
- No manual intervention needed
- Results update automatically when you run tests
- Only updates games that have finished (3-4 hours after scheduled time)

### Smart Detection
- **Basketball**: Checks for status "FT" (Full Time) or "AOT" (After Overtime)
- **Football**: Checks for status "FT", "AET", or "PEN"
- Waits sufficient time after scheduled start before checking

### Result Validation
The tracker accurately determines WIN/LOSS by:
- Comparing predicted OVER/UNDER to actual totals
- Checking BTTS (Both Teams To Score) outcomes
- Validating 1X2 (Home/Draw/Away) predictions
- Accounting for lines (e.g., Over 227.5 needs 228+ to win)

## Data Persistence

### CSV Files Location
```
predictor/
├── output/
│   ├── basketball_predictions.csv  ← All basketball predictions
│   └── football_predictions.csv    ← All football predictions
```

### CSV Format
- Standard CSV format (comma-separated)
- UTF-8 encoding
- Can be opened in Excel, Google Sheets, or any CSV viewer
- Safe to view/analyze while system is running

## Tracking Statistics

### Accuracy Calculation
```python
Accuracy = (Wins / Completed Games) × 100%
```

### Key Metrics
- **Total Predictions**: All predictions ever made
- **Completed**: Games that have finished and been verified
- **Pending**: Games that haven't finished yet
- **Wins**: Predictions that were correct
- **Losses**: Predictions that were wrong

## Integration

### Basketball
The tracker is integrated into `test_basketball.py`:
```python
from basketball.prediction_tracker import prediction_tracker

# Update results automatically
prediction_tracker.update_results(basketball_api)

# Show stats
prediction_tracker.print_stats()

# Log new predictions
prediction_tracker.log_prediction(...)
```

### Football
To integrate into football predictor (`elite_predictor.py`):
```python
from data.prediction_tracker import football_prediction_tracker

# Update results automatically
football_prediction_tracker.update_results(api_client)

# Show stats  
football_prediction_tracker.print_stats()

# Log new predictions
football_prediction_tracker.log_prediction(...)
```

## Benefits

1. **Historical Record**: Every prediction is permanently logged
2. **Performance Tracking**: See your accuracy over time
3. **Data Analysis**: Export to Excel for deeper analysis
4. **Accountability**: Can't cherry-pick results - everything is tracked
5. **Learning**: Identify which markets/confidence levels perform best
6. **Automation**: No manual tracking needed

## Tips

### Viewing in Excel
1. Open the CSV file in Excel
2. Use "Text to Columns" if needed
3. Sort by confidence_tier to see best predictions
4. Filter by result to analyze wins/losses
5. Calculate ROI if you track stakes

### Analyzing Performance
```python
# In Python:
import pandas as pd

# Load data
df = pd.read_csv('output/basketball_predictions.csv')

# Filter completed games
completed = df[df['result'].notna()]

# Accuracy by confidence tier
print(completed.groupby('confidence_tier')['result'].value_counts())

# Accuracy by market type
print(completed.groupby('market')['result'].value_counts())
```

### Backup
The CSV files are your permanent record. Back them up regularly:
```bash
# Windows
copy output\*.csv backup\
```

## Troubleshooting

### "No games to update"
- Normal message when no pending games have finished yet
- Games must be 3-4 hours past scheduled time to update

### Missing final scores
- Game may not have finished yet
- API may not have updated the result
- Check game status manually on API-Sports website

### Incorrect WIN/LOSS
- Ensure the line interpretation is correct
- Some markets have special rules (e.g., overtime counts)
- Check the prediction and actual scores manually

## Future Enhancements

Potential improvements:
- ROI tracking (if stakes are logged)
- Confidence tier performance analysis
- Time-based performance (weekday vs weekend)
- League-specific accuracy
- Graphical performance dashboard
- Email alerts for completed games
- Automatic reporting (daily/weekly summaries)
