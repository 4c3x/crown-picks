# 👑 Crown Picks - Elite Basketball Predictor

![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![Flask](https://img.shields.io/badge/flask-3.0-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

**Elite basketball predictions with 80%+ accuracy. Find the best bets from every game on the planet.**

🔗 **Live Demo:** [Coming Soon]

## 🎯 Features

- 🏀 **All Leagues Worldwide** - Scans every basketball game globally
- 🎯 **80% Minimum Probability** - Only elite predictions pass our filters
- 📊 **Two Market Types**:
  - **Total Points** - Over/Under for combined game score (Top 2 picks)
  - **Team Points** - Individual team scoring predictions (Top 5 picks)
- 🏆 **Quality Over Quantity** - No picks if nothing meets standards
- 📱 **Progressive Web App** - Install on Android like a native app
- ⚡ **Real-time Streaming** - Live scan progress with SSE
- 📈 **Performance Tracking** - Automatic result updates and statistics

## 🚀 Quick Start

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/4c3x/crown-picks.git
   cd crown-picks
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Mac/Linux
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up API key**
   
   Get a free API key from [API-Sports Basketball](https://api-sports.io/documentation/basketball/v1)
   
   Create `config/settings.py`:
   ```python
   API_SPORTS_KEY = "your_api_key_here"
   ```

5. **Run the app**
   ```bash
   python app.py
   ```

6. **Open your browser**
   
   Visit: `http://localhost:5000`

## 📱 Mobile App (PWA)

Crown Picks can be installed as a mobile app on Android devices!

### Installation Steps:

1. Visit the live URL in Chrome browser
2. Tap menu (⋮) → "Add to Home Screen"
3. Tap "Add"
4. Open the app from your home screen!

**Full guide:** See [ANDROID_INSTALL.md](ANDROID_INSTALL.md)

## 🌐 Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com)

1. Fork this repository
2. Sign up at [Render.com](https://render.com)
3. Click "New +" → "Web Service"
4. Connect your GitHub repository
5. Use these settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
6. Add environment variable:
   - Key: `API_SPORTS_KEY`
   - Value: Your API key
7. Click "Create Web Service"

Your app will be live in minutes!

## 📊 How It Works

### Prediction Engine

1. **Data Collection** - Fetches live games from Basketball API
2. **Feature Engineering** - Calculates 20+ statistical features
3. **ML Prediction** - XGBoost model trained on historical data
4. **Confidence Filtering** - Only predictions ≥80% pass
5. **Result Tracking** - Auto-updates game outcomes

### Quality Gates

✅ Minimum 80% probability  
✅ Sufficient historical data (5+ H2H games)  
✅ Recent form analysis  
✅ Home/away performance splits  
✅ Odds validation from bookmakers  

## 📁 Project Structure

```
crown-picks/
├── app.py                    # Flask application
├── basketball/               # Basketball prediction engine
│   ├── api_client.py        # API integration
│   ├── predictor.py         # ML prediction model
│   └── prediction_tracker.py # Result tracking
├── templates/
│   └── index.html           # Web interface
├── static/                  # PWA assets
│   ├── manifest.json
│   ├── service-worker.js
│   └── icons/
├── output/                  # Prediction results (CSV)
└── requirements.txt         # Python dependencies
```

## 🎨 Tech Stack

- **Backend:** Python 3.11, Flask
- **ML:** Scikit-learn, XGBoost
- **Data:** Basketball API (API-Sports)
- **Frontend:** Vanilla JS, SSE streaming
- **Deployment:** Gunicorn, Render
- **PWA:** Service Workers, Web Manifest

## 📈 Performance

**Current Record (Team Points):**
- 13 Wins - 3 Losses
- **81.2% Accuracy** ✅

**Tracked in:** `output/team_predictions.csv`

## 🔧 Configuration

Edit `config/settings.py`:

```python
# API Configuration
API_SPORTS_KEY = "your_key"

# Prediction Thresholds
MIN_PROBABILITY = 0.80  # 80% minimum
MIN_H2H_GAMES = 5       # Minimum head-to-head games

# Bias Adjustments
UNDER_BIAS_ADJUSTMENT = 6.0
UNDER_PROBABILITY_PENALTY = 0.12
```

## 📖 Documentation

- [PWA Setup Guide](PWA_SETUP.md)
- [Android Installation](ANDROID_INSTALL.md)
- [GitHub Push Guide](GITHUB_PUSH.md)
- [Tracking Guide](TRACKING_GUIDE.md)

## 🤝 Contributing

Contributions welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests

## 📄 License

MIT License - Use freely!

## 🙏 Credits

- Basketball data powered by [API-Sports](https://api-sports.io)
- Built with ❤️ by [4c3x](https://github.com/4c3x)

## ⚠️ Disclaimer

This tool is for educational and entertainment purposes only. Always gamble responsibly.

---

⭐ **Star this repo if you find it useful!**

🏀 Happy betting with Crown Picks! 👑
