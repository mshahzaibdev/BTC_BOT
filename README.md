# ICT Trading Signal Discord Bot

AI-powered Smart Money Concepts signal generator for BTC/USDT using K-Means clustering.

## 🌟 Features

- **On-demand signals** - Get trading signals with `/signal` command
- **Smart Money Concepts** - Analyzes FVG, Order Blocks, and Swing levels
- **ML-powered** - Uses K-Means clustering trained on historical data
- **Simple & Fast** - No database, just instant signal generation
- **15-minute timeframe** - Optimized for swing trading

## 📋 Prerequisites

- Python 3.8 or higher
- Discord Bot Token ([Get one here](#setting-up-discord-bot))
- Internet connection (for Binance API)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd discord_bot
pip install -r requirements_bot.txt
```

### 2. Setup Environment Variables

Create a `.env` file in the `discord_bot` directory:

```bash
cp .env.example .env
```

Edit `.env` and add your Discord bot token:

```env
DISCORD_BOT_TOKEN=your_discord_bot_token_here
```

### 3. Verify Model Files

Make sure these files exist in the parent directory:
- `../scaler.pkl`
- `../kmeans.pkl`

These should already be in your project root.

### 4. Run the Bot

```bash
python bot.py
```

You should see:
```
🚀 Starting ICT Trading Signal Bot...
🤖 Bot logged in as YourBot#1234
✅ Models loaded successfully
✅ Services initialized successfully
✅ Synced 3 slash command(s)
```

## 🎮 Discord Commands

| Command | Description |
|---------|-------------|
| `/signal` | Get current BTC/USDT trading signal |
| `/info` | Learn how the bot works |
| `/ping` | Check bot latency |

## 🔧 Setting Up Discord Bot

### Step 1: Create Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"**
3. Name it (e.g., "ICT Signal Bot")
4. Click **"Create"**

### Step 2: Create Bot User

1. Go to **"Bot"** tab on the left
2. Click **"Add Bot"**
3. Click **"Reset Token"** and copy the token
4. Paste this token in your `.env` file

### Step 3: Enable Intents

In the **"Bot"** tab:
1. Scroll down to **"Privileged Gateway Intents"**
2. Enable **"Message Content Intent"**
3. Save changes

### Step 4: Invite Bot to Server

1. Go to **"OAuth2"** → **"URL Generator"**
2. Select scopes:
   - ✅ `bot`
   - ✅ `applications.commands`
3. Select bot permissions:
   - ✅ Send Messages
   - ✅ Embed Links
   - ✅ Use Slash Commands
4. Copy the generated URL
5. Open in browser and invite to your server

## 📊 How It Works

```
User types /signal
    ↓
Bot fetches last 100 candles (15m) from Binance
    ↓
Calculates Smart Money Concepts indicators:
  • Fair Value Gaps (FVG)
  • Order Blocks (OB)
  • Swing Highs/Lows
    ↓
Extracts 8 features from latest candle
    ↓
Normalizes features with StandardScaler
    ↓
Predicts cluster with K-Means (0-4)
    ↓
Maps cluster to signal:
  • Cluster 4 → 🟢 BUY
  • Cluster 3 → 🔴 SHORT
  • Others → ⚪ NEUTRAL
    ↓
Sends formatted response with levels
```

## 🏗️ Project Structure

```
discord_bot/
├── bot.py                    # Main bot file
├── config.py                 # Configuration
├── .env                      # Environment variables (create this)
├── .env.example             # Environment template
├── requirements_bot.txt     # Dependencies
├── services/
│   ├── __init__.py
│   ├── binance_service.py   # Binance API client
│   └── prediction_service.py # ML prediction
└── README.md                # This file
```

## 🌐 Deployment Options

### Option 1: Run on Your Computer

**Pros:** Free, easy, instant
**Cons:** Computer must stay on

```bash
python bot.py
# Keep terminal open
```

### Option 2: PythonAnywhere (FREE)

**Pros:** Always-on, free tier available
**Cons:** Daily restart (auto-restarts)

1. Sign up at [pythonanywhere.com](https://www.pythonanywhere.com)
2. Upload your files
3. Install requirements: `pip install -r requirements_bot.txt`
4. Create "Always-on task" to run `python bot.py`

### Option 3: Railway.app ($5/month)

**Pros:** Professional, no restarts, easy deploy
**Cons:** $5/month

1. Sign up at [railway.app](https://railway.app)
2. Create new project
3. Connect GitHub repo
4. Add environment variables
5. Deploy!

### Option 4: VPS (DigitalOcean, AWS, etc.)

**Pros:** Full control
**Cons:** More setup required

```bash
# SSH into your VPS
git clone your-repo
cd discord_bot
pip install -r requirements_bot.txt
nohup python bot.py &
```

## 🔍 Troubleshooting

### Bot won't start

**Error:** `DISCORD_BOT_TOKEN must be set`
- **Fix:** Add your token to `.env` file

**Error:** `Error loading models`
- **Fix:** Make sure `scaler.pkl` and `kmeans.pkl` are in parent directory

### Commands not showing

**Issue:** Slash commands don't appear in Discord
- **Fix:** Wait 1-5 minutes after bot starts
- **Fix:** Kick and re-invite bot
- **Fix:** Make sure you enabled `applications.commands` scope

### Binance API errors

**Error:** `Connection error` or `API timeout`
- **Fix:** Check internet connection
- **Fix:** Binance might be down (check status.binance.com)

### Model prediction errors

**Error:** `Error predicting signal`
- **Fix:** Make sure you have all 8 features in your model
- **Fix:** Check if `feature_engineering.py` is in parent directory

## 📈 Understanding Signals

### 🟢 BUY Signal (Cluster 4)
- Bullish Smart Money pattern detected
- FVG/OB zones suggest upward movement
- Consider long positions

### 🔴 SHORT Signal (Cluster 3)
- Bearish Smart Money pattern detected
- FVG/OB zones suggest downward movement
- Consider short positions

### ⚪ NEUTRAL Signal (Clusters 0, 1, 2)
- No clear directional bias
- Wait for better setup
- Avoid trading

## ⚠️ Disclaimer

**This bot is for EDUCATIONAL PURPOSES ONLY.**

- Not financial advice
- Past performance ≠ future results
- Crypto trading is risky
- Only trade with money you can afford to lose
- Do your own research (DYOR)
- Test signals thoroughly before trading real money

## 🛠️ Customization

### Change Symbol

Currently hardcoded to BTCUSDT. To support other symbols, modify:

```python
# In bot.py, line ~85
df, latest_candle = binance_service.get_signal_data(
    symbol='ETHUSDT',  # Change here
    interval='15m',
    limit=100,
    swing_length=SWING_LENGTH
)
```

### Change Timeframe

```python
# In config.py or .env
DEFAULT_TIMEFRAME=5m  # or 1h, 4h, etc.
```

**Note:** Model was trained on 15m data, other timeframes may reduce accuracy.

### Adjust Swing Length

```python
# In .env
SWING_LENGTH=10  # default is 7
```

## 📞 Support

Issues? Questions?
- Check [Troubleshooting](#troubleshooting) section
- Review code comments in `bot.py`
- Test with `/ping` and `/info` commands first

## 📜 License

This project is for educational purposes. Use at your own risk.

---

**Made with ❤️ for the crypto trading community**
