# Discord Bot Setup Guide

Complete step-by-step guide to get your ICT Trading Signal Bot running.

## 📦 Step 1: Install Dependencies

Open terminal in the `discord_bot` folder and run:

```bash
pip install -r requirements_bot.txt
```

This will install:
- `discord.py` - Discord bot framework
- `python-binance` - Binance API client
- `pandas`, `numpy` - Data processing
- `scikit-learn` - ML models
- `smartmoneyconcepts` - ICT indicators
- `python-dotenv` - Environment variables

## 🤖 Step 2: Create Discord Bot

### 2.1 Go to Discord Developer Portal

Visit: https://discord.com/developers/applications

### 2.2 Create New Application

1. Click **"New Application"** (top right)
2. Enter name: `ICT Signal Bot` (or whatever you want)
3. Click **"Create"**

### 2.3 Create Bot User

1. Click **"Bot"** tab (left sidebar)
2. Click **"Add Bot"** button
3. Click **"Yes, do it!"** to confirm

### 2.4 Get Bot Token

1. Under the bot's name, click **"Reset Token"**
2. Click **"Yes, do it!"**
3. **Copy the token** (you'll need this in Step 3)
   - ⚠️ **IMPORTANT:** Never share this token!
   - If exposed, reset it immediately

### 2.5 Enable Required Intents

Scroll down to **"Privileged Gateway Intents"**:
- ✅ Enable **"Message Content Intent"**
- Click **"Save Changes"**

### 2.6 Invite Bot to Your Server

1. Click **"OAuth2"** tab → **"URL Generator"**
2. Select **SCOPES**:
   - ✅ `bot`
   - ✅ `applications.commands`
3. Select **BOT PERMISSIONS**:
   - ✅ Send Messages
   - ✅ Embed Links
   - ✅ Read Message History
   - ✅ Use Slash Commands
4. Copy the **Generated URL** at the bottom
5. Open the URL in your browser
6. Select your server from the dropdown
7. Click **"Authorize"**
8. Complete the captcha

Your bot should now appear **offline** in your server!

## ⚙️ Step 3: Configure Environment

### 3.1 Create .env File

In the `discord_bot` folder, create a file named `.env`:

```bash
# Copy the example
cp .env.example .env
```

Or create it manually with this content:

```env
DISCORD_BOT_TOKEN=your_token_here
SCALER_PATH=../scaler.pkl
KMEANS_PATH=../kmeans.pkl
SWING_LENGTH=7
```

### 3.2 Add Your Bot Token

Edit `.env` and replace `your_token_here` with the token you copied in Step 2.4:

```env
DISCORD_BOT_TOKEN=MTIzNDU2Nzg5MDEyMzQ1Njc4OQ.AbCdEf.GhIjKlMnOpQrStUvWxYz123456789
```

### 3.3 Verify Model Files

Make sure these files exist:
```
ict-backend/
├── scaler.pkl       ✅
├── kmeans.pkl       ✅
├── feature_engineering.py  ✅
└── discord_bot/
    └── bot.py
```

The bot looks for models in the parent directory (`../`).

## 🚀 Step 4: Run the Bot

From the `discord_bot` folder:

```bash
python bot.py
```

You should see:

```
🚀 Starting ICT Trading Signal Bot...
📁 Scaler path: ../scaler.pkl
📁 KMeans path: ../kmeans.pkl
🤖 Bot logged in as ICT Signal Bot#1234
📊 Connected to 1 server(s)
✅ Models loaded successfully
   - Scaler: ../scaler.pkl
   - KMeans: ../kmeans.pkl
✅ Services initialized successfully
✅ Synced 3 slash command(s)
```

The bot is now **online** in your Discord server! ✅

## 🎮 Step 5: Test the Bot

In your Discord server, try these commands:

### Test 1: Check if bot is responsive
```
/ping
```
Should respond with latency (e.g., "Bot latency: 45ms")

### Test 2: Get bot information
```
/info
```
Should show details about how the bot works

### Test 3: Get a trading signal
```
/signal
```

Should return something like:

```
📊 BTC/USDT Signal Analysis
Timeframe: 15 minutes
Signal: BUY

🟢 Signal: BUY
🎯 Cluster: Cluster 4
💰 Current Price: $42,350.25

📍 Smart Money Concepts
FVG Zone: $42,100.00 - $42,200.00
Order Block: $41,800.00 - $42,000.00
Swing Low: $41,500.00

💡 Explanation
Cluster 4 detected - Bullish pattern identified

📖 Pattern Info
Bullish Pattern
Smart Money Concepts indicate buying pressure
Action: Consider LONG positions

⚠️ This is not financial advice. Trade at your own risk.
```

## ✅ Success Checklist

- [ ] Python 3.8+ installed
- [ ] All dependencies installed (`pip install -r requirements_bot.txt`)
- [ ] Discord bot created on Developer Portal
- [ ] Bot token copied and added to `.env`
- [ ] Message Content Intent enabled
- [ ] Bot invited to your server
- [ ] Model files exist (`scaler.pkl`, `kmeans.pkl`)
- [ ] `feature_engineering.py` exists in parent directory
- [ ] Bot starts without errors
- [ ] Bot shows as online in Discord
- [ ] `/ping` command works
- [ ] `/signal` command returns data

## 🔧 Troubleshooting

### Bot won't start

**Error:** `DISCORD_BOT_TOKEN must be set`
```bash
# Make sure .env exists and has your token
cat .env
# Should show: DISCORD_BOT_TOKEN=MTIzNDU2...
```

**Error:** `Error loading models`
```bash
# Check if files exist
ls -la ../scaler.pkl
ls -la ../kmeans.pkl

# If not found, check your directory structure
pwd  # Should end with /discord_bot
```

**Error:** `ModuleNotFoundError: No module named 'discord'`
```bash
# Install dependencies again
pip install -r requirements_bot.txt
```

### Slash commands not showing

**Issue:** Commands don't appear in Discord

**Solutions:**
1. Wait 1-5 minutes (Discord caches commands)
2. Restart Discord app
3. Kick bot and re-invite with correct permissions
4. Check bot has `applications.commands` scope

### Binance API errors

**Error:** `Error fetching data from Binance`

**Solutions:**
1. Check internet connection
2. Try again (Binance might be rate limiting)
3. Visit https://www.binance.com/en/binance-api to check API status

### `/signal` returns error

**Error:** `Failed to generate signal: No module named 'feature_engineering'`

**Solution:**
```bash
# Make sure feature_engineering.py is in parent directory
ls -la ../feature_engineering.py

# And that services can import it
python -c "import sys; sys.path.append('..'); import feature_engineering; print('✅ Import works')"
```

## 🌐 Deployment (Optional)

### Keep Bot Running 24/7

**Option 1: Your Computer**
```bash
# Linux/Mac
nohup python bot.py &

# Windows (PowerShell)
Start-Process python -ArgumentList "bot.py" -WindowStyle Hidden
```

**Option 2: PythonAnywhere (FREE)**

1. Sign up: https://www.pythonanywhere.com
2. Go to "Files" → Upload `discord_bot` folder
3. Open Bash console
4. Install dependencies: `pip install -r discord_bot/requirements_bot.txt`
5. Go to "Tasks" → Add new task
6. Command: `cd discord_bot && python bot.py`
7. Schedule: Daily at 00:00 (will run continuously until restart)

**Option 3: Railway.app ($5/month)**

1. Sign up: https://railway.app
2. "New Project" → "Deploy from GitHub"
3. Select your repo
4. Add environment variable: `DISCORD_BOT_TOKEN`
5. Deploy!

## 📚 Next Steps

1. ✅ Bot is running
2. Test with real market conditions
3. Track signal accuracy
4. Consider adding more features (see README.md)

## ⚠️ Important Reminders

- **Never share your bot token**
- **This is educational - not financial advice**
- **Always test signals before trading real money**
- **Past performance ≠ future results**

---

**Questions?** Check README.md or review the code comments in `bot.py`

**Enjoy your ICT Signal Bot! 🚀**
