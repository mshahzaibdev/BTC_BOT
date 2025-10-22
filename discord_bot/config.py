import os
from dotenv import load_dotenv

load_dotenv()

# Discord Configuration
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
DISCORD_GUILD_ID = os.getenv('DISCORD_GUILD_ID')

# Binance API
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET', '')

# Model Paths
MODEL_PATH = os.getenv('MODEL_PATH', '../models')
SCALER_PATH = os.getenv('SCALER_PATH', '../scaler.pkl')
KMEANS_PATH = os.getenv('KMEANS_PATH', '../kmeans.pkl')

# Trading Configuration
DEFAULT_SYMBOL = os.getenv('DEFAULT_SYMBOL', 'BTCUSDT')
DEFAULT_TIMEFRAME = os.getenv('DEFAULT_TIMEFRAME', '15m')
DEFAULT_LIMIT = int(os.getenv('DEFAULT_LIMIT', '60'))
SWING_LENGTH = int(os.getenv('SWING_LENGTH', '7'))

# Alert Configuration
ALERT_CHECK_INTERVAL = int(os.getenv('ALERT_CHECK_INTERVAL', '60'))
MAX_ALERTS_PER_USER = int(os.getenv('MAX_ALERTS_PER_USER', '10'))

# Database
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///./ict_bot.db')

# Risk Management
DEFAULT_LEVERAGE = int(os.getenv('DEFAULT_LEVERAGE', '10'))
DEFAULT_RISK_PERCENTAGE = float(os.getenv('DEFAULT_RISK_PERCENTAGE', '2.0'))

# Validation
if not DISCORD_BOT_TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN must be set in .env file")
