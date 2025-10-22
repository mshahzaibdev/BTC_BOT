"""
ICT Trading Signal Discord Bot - INTEGRATED VERSION
Feature engineering built-in to eliminate import issues
"""
import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
import json
import traceback
import pandas as pd
import numpy as np
import joblib
from datetime import datetime
from dotenv import load_dotenv
from binance.client import Client

# Load environment variables
load_dotenv()

# Configuration
DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
CHECK_INTERVAL_MINUTES = int(os.getenv('CHECK_INTERVAL_MINUTES', '15'))
SCALER_PATH = os.getenv('SCALER_PATH', './scaler.pkl')
KMEANS_PATH = os.getenv('KMEANS_PATH', './kmeans.pkl')
SWING_LENGTH = int(os.getenv('SWING_LENGTH', '15'))
SERVER_CONFIG_FILE = os.getenv('SERVER_CONFIG_FILE', 'server_config.json')

# Validate token
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN not found in .env file")

# Initialize bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

# Global state
binance_client = None
scaler = None
kmeans = None
last_signal = None
server_configs = {}

# Feature columns (must match training)
FEATURE_COLUMNS = [
    'FVG_flag',
    'FVG_Top',
    'FVG_Bottom',
    'OB_flag',
    'OB_Top',
    'OB_Bottom',
    'Swing_HighLow',
    'Swing_Level'
]


# ============================================================================
# FEATURE ENGINEERING - INTEGRATED
# ============================================================================

def engineer_features_inline(df: pd.DataFrame, swing_length=7):
    """
    Engineer ICT/SMC features from OHLCV data - INLINE VERSION

    Args:
        df: DataFrame with OHLCV columns
        swing_length: Length for swing detection

    Returns:
        DataFrame with engineered features
    """
    print(f"[FEATURE_ENG] 🔧 Starting feature engineering...")
    print(f"[FEATURE_ENG] Input: {len(df)} candles, swing_length={swing_length}")

    try:
        # Import SMC library
        print("[FEATURE_ENG] Importing smartmoneyconcepts library...")
        from smartmoneyconcepts import smc
        print("[FEATURE_ENG] ✅ SMC library imported successfully")

        # Calculate swing highs/lows
        print("[FEATURE_ENG] Calculating swing highs/lows...")
        swings = smc.swing_highs_lows(df, swing_length=swing_length)
        print(f"[FEATURE_ENG] ✅ Swings: {len(swings)} rows")

        # Calculate Fair Value Gaps
        print("[FEATURE_ENG] Calculating Fair Value Gaps (FVG)...")
        fvg = smc.fvg(df)
        print(f"[FEATURE_ENG] ✅ FVG: {len(fvg)} rows")

        # Calculate Order Blocks
        print("[FEATURE_ENG] Calculating Order Blocks (OB)...")
        ob = smc.ob(df, swings)
        print(f"[FEATURE_ENG] ✅ OB: {len(ob)} rows")

        # Rename columns to match model training
        print("[FEATURE_ENG] Renaming and merging columns...")
        fvg_renamed = fvg.rename(columns={
            'FVG': 'FVG_flag',
            'Top': 'FVG_Top',
            'Bottom': 'FVG_Bottom',
            'MitigatedIndex': 'FVG_MitigatedIndex'
        })

        ob_renamed = ob.rename(columns={
            'OB': 'OB_flag',
            'Top': 'OB_Top',
            'Bottom': 'OB_Bottom',
            'OBVolume': 'OB_Volume',
            'MitigatedIndex': 'OB_MitigatedIndex',
            'Percentage': 'OB_Percentage'
        })

        swings_renamed = swings.rename(columns={
            'HighLow': 'Swing_HighLow',
            'Level': 'Swing_Level'
        })

        # Merge all features
        feat = pd.concat([
            df.reset_index(drop=True),
            fvg_renamed,
            ob_renamed,
            swings_renamed
        ], axis=1)

        # Fill NaNs
        feat = feat.fillna(0)

        print(f"[FEATURE_ENG] ✅ Feature engineering complete: {len(feat)} rows, {len(feat.columns)} columns")
        return feat

    except ImportError as e:
        print(f"[FEATURE_ENG] ❌ IMPORT ERROR: {e}")
        print("[FEATURE_ENG] Make sure 'smartmoneyconcepts' package is installed!")
        traceback.print_exc()
        raise
    except Exception as e:
        print(f"[FEATURE_ENG] ❌ ERROR during feature engineering: {e}")
        traceback.print_exc()
        raise


# ============================================================================
# BINANCE DATA FETCHING - INTEGRATED
# ============================================================================

def fetch_binance_data(symbol='BTCUSDT', interval='15m', limit=100):
    """Fetch candlestick data from Binance"""
    print(f"[BINANCE] Fetching {limit} candles for {symbol} ({interval})...")

    try:
        klines = binance_client.get_klines(
            symbol=symbol,
            interval=interval,
            limit=limit
        )

        if not klines:
            raise ValueError("No data received from Binance")

        # Convert to DataFrame
        df = pd.DataFrame(klines, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])

        # Convert types
        df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
        df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')

        for col in ['open', 'high', 'low', 'close', 'volume',
                   'quote_asset_volume', 'taker_buy_base_asset_volume',
                   'taker_buy_quote_asset_volume']:
            df[col] = df[col].astype(float)

        df['number_of_trades'] = df['number_of_trades'].astype(int)
        df = df.drop('ignore', axis=1)
        df.set_index('open_time', inplace=True)

        print(f"[BINANCE] ✅ Fetched {len(df)} candles successfully")
        return df

    except Exception as e:
        print(f"[BINANCE] ❌ ERROR fetching data: {e}")
        traceback.print_exc()
        raise


def get_signal_data(symbol='BTCUSDT', interval='15m', limit=100, swing_length=15):
    """Fetch data and engineer features"""
    print(f"\n[PIPELINE] ========== STARTING SIGNAL PIPELINE ==========")
    print(f"[PIPELINE] Symbol: {symbol}, Interval: {interval}, Limit: {limit}")

    try:
        # Step 1: Fetch data
        df = fetch_binance_data(symbol, interval, limit)

        # Step 2: Engineer features
        df_with_features = engineer_features_inline(df, swing_length=swing_length)

        # Step 3: Get latest candle
        latest = df_with_features.iloc[-1]

        print(f"[PIPELINE] ✅ Pipeline complete!")
        print(f"[PIPELINE] Latest candle features:")
        for col in FEATURE_COLUMNS:
            value = latest.get(col, 0)
            print(f"[PIPELINE]   - {col}: {value}")
        print(f"[PIPELINE] ========================================\n")

        return df_with_features, latest

    except Exception as e:
        print(f"[PIPELINE] ❌ PIPELINE FAILED: {e}")
        traceback.print_exc()
        raise


# ============================================================================
# PREDICTION - INTEGRATED
# ============================================================================

def predict_signal(candle_data):
    """Predict trading signal from candle data"""
    print(f"[PREDICTION] Starting prediction...")

    try:
        # Extract features
        features = []
        feature_dict = {}

        for col in FEATURE_COLUMNS:
            value = candle_data[col] if col in candle_data else 0
            if pd.isna(value):
                value = 0
            features.append(value)
            feature_dict[col] = float(value)

        print(f"[PREDICTION] Feature vector: {features}")

        # Scale features
        features_array = np.array(features).reshape(1, -1)
        features_scaled = scaler.transform(features_array)
        print(f"[PREDICTION] Features scaled")

        # Predict cluster
        cluster = int(kmeans.predict(features_scaled)[0])
        print(f"[PREDICTION] Cluster predicted: {cluster}")

        # Map cluster to signal
        if cluster == 4:
            signal = 'buy'
            explanation = "Cluster 4 detected - Bullish pattern identified"
        elif cluster == 3:
            signal = 'short'
            explanation = "Cluster 3 detected - Bearish pattern identified"
        else:
            signal = 'neutral'
            explanation = f"Cluster {cluster} detected - No clear directional bias"

        print(f"[PREDICTION] ✅ Signal: {signal.upper()}")

        return {
            'signal': signal,
            'cluster': cluster,
            'explanation': explanation,
            'features': feature_dict
        }

    except Exception as e:
        print(f"[PREDICTION] ❌ ERROR during prediction: {e}")
        traceback.print_exc()
        raise


def get_cluster_info(cluster_id):
    """Get information about a specific cluster"""
    cluster_descriptions = {
        0: {
            'name': 'Neutral Zone A',
            'description': 'No strong directional indicators',
            'action': 'Wait for clearer signal'
        },
        1: {
            'name': 'Neutral Zone B',
            'description': 'Mixed signals, uncertain market structure',
            'action': 'Avoid trading'
        },
        2: {
            'name': 'Neutral Zone C',
            'description': 'Choppy price action',
            'action': 'Stay on sidelines'
        },
        3: {
            'name': 'Bearish Pattern',
            'description': 'Smart Money Concepts indicate selling pressure',
            'action': 'Consider SHORT positions'
        },
        4: {
            'name': 'Bullish Pattern',
            'description': 'Smart Money Concepts indicate buying pressure',
            'action': 'Consider LONG positions'
        }
    }

    return cluster_descriptions.get(cluster_id, {
        'name': 'Unknown',
        'description': 'Invalid cluster ID',
        'action': 'Error'
    })


# ============================================================================
# SERVER CONFIGURATION
# ============================================================================

def load_server_configs():
    """Load server configurations from JSON file"""
    global server_configs
    try:
        if os.path.exists(SERVER_CONFIG_FILE):
            with open(SERVER_CONFIG_FILE, 'r') as f:
                server_configs = json.load(f)
            server_configs = {int(k): v for k, v in server_configs.items()}
            print(f'✅ Loaded configurations for {len(server_configs)} server(s)')
        else:
            server_configs = {}
            print('ℹ️  No server configurations found, starting fresh')
    except Exception as e:
        print(f'❌ Error loading server configs: {e}')
        server_configs = {}


def save_server_configs():
    """Save server configurations to JSON file"""
    try:
        with open(SERVER_CONFIG_FILE, 'w') as f:
            json.dump(server_configs, f, indent=2)
        print(f'✅ Saved configurations for {len(server_configs)} server(s)')
    except Exception as e:
        print(f'❌ Error saving server configs: {e}')


# ============================================================================
# DISCORD BOT EVENTS & COMMANDS
# ============================================================================

@tasks.loop(minutes=CHECK_INTERVAL_MINUTES)
async def check_signals():
    """Background task that runs every X minutes to send signal updates"""
    global last_signal

    if not server_configs:
        return

    try:
        print(f"\n{'='*60}")
        print(f"[CHECK_SIGNALS] Running scheduled check at {datetime.now()}")
        print(f"{'='*60}")

        # Fetch data and get signal
        df, latest_candle = get_signal_data(
            symbol='BTCUSDT',
            interval='15m',
            limit=100,
            swing_length=SWING_LENGTH
        )

        # Get prediction
        prediction = predict_signal(latest_candle)
        current_signal = prediction['signal']

        # Build embed
        current_price = float(latest_candle['close'])
        features = prediction['features']

        # Determine if new signal
        is_new_signal = current_signal != last_signal and current_signal in ['buy', 'short']
        last_signal = current_signal

        if is_new_signal:
            embed = discord.Embed(
                title="🚨 NEW TRADING SIGNAL 🚨",
                description=f"**{current_signal.upper()}** signal detected on BTC/USDT!",
                color=get_signal_color(current_signal)
            )
            ping_message = "@here"
        else:
            embed = discord.Embed(
                title="📊 SIGNAL STATUS UPDATE 📊",
                description=f"Current signal status for BTC/USDT",
                color=get_signal_color(current_signal)
            )
            ping_message = ""

        signal_emoji = {'buy': '🟢', 'short': '🔴', 'neutral': '🟡'}

        embed.add_field(
            name=f"{signal_emoji[current_signal]} Current Signal",
            value=f"**{current_signal.upper()}**",
            inline=True
        )

        embed.add_field(
            name="💰 Price",
            value=f"${current_price:,.2f}",
            inline=True
        )

        embed.add_field(
            name="🎯 Cluster",
            value=f"Cluster {prediction['cluster']}",
            inline=True
        )

        # Smart Money Concepts
        smc_info = []
        if features['FVG_flag'] == 1:
            smc_info.append(f"**FVG:** ${features['FVG_Bottom']:,.2f} - ${features['FVG_Top']:,.2f}")
        if features['OB_flag'] == 1:
            smc_info.append(f"**OB:** ${features['OB_Bottom']:,.2f} - ${features['OB_Top']:,.2f}")
        if features['Swing_Level'] > 0:
            swing_type = "High" if features['Swing_HighLow'] == 1 else "Low"
            smc_info.append(f"**Swing {swing_type}:** ${features['Swing_Level']:,.2f}")

        if smc_info:
            embed.add_field(name="📍 Key Levels", value="\n".join(smc_info), inline=False)

        embed.add_field(name="💡 Analysis", value=prediction['explanation'], inline=False)

        cluster_info = get_cluster_info(prediction['cluster'])
        embed.add_field(
            name="📖 Pattern",
            value=f"**{cluster_info['name']}** - {cluster_info['action']}",
            inline=False
        )

        embed.set_footer(text="⚠️ Not financial advice. DYOR.")
        embed.timestamp = discord.utils.utcnow()

        # Send to all configured channels
        success_count = 0
        for guild_id, channel_id in server_configs.items():
            try:
                channel = await bot.fetch_channel(channel_id)
                await channel.send(content=ping_message, embed=embed)
                success_count += 1
            except Exception as e:
                print(f'❌ Error sending to channel {channel_id}: {e}')

        if is_new_signal:
            print(f'🚨 NEW {current_signal.upper()} signal sent to {success_count}/{len(server_configs)} server(s)')
        else:
            print(f'📊 Status update sent to {success_count}/{len(server_configs)} server(s) - Signal: {current_signal.upper()}')

    except Exception as e:
        print(f'❌ Error in check_signals: {e}')
        traceback.print_exc()


@bot.event
async def on_ready():
    """Bot startup event"""
    global binance_client, scaler, kmeans

    print(f'\n{"="*60}')
    print(f'🤖 Bot logged in as {bot.user}')
    print(f'📊 Connected to {len(bot.guilds)} server(s)')
    print(f'{"="*60}\n')

    for guild in bot.guilds:
        print(f'   └─ {guild.name} (ID: {guild.id})')

    # Load server configurations
    load_server_configs()

    # Initialize services
    try:
        print(f'\n[INIT] Loading models...')
        print(f'[INIT] Scaler path: {SCALER_PATH}')
        print(f'[INIT] KMeans path: {KMEANS_PATH}')

        # Initialize Binance client without API keys (public data only)
        # Use testnet=True to avoid rate limit issues on production API
        binance_client = Client(None, None, testnet=True)
        print('[INIT] ✅ Binance client initialized (testnet mode)')

        scaler = joblib.load(SCALER_PATH)
        kmeans = joblib.load(KMEANS_PATH)

        print('[INIT] ✅ All services initialized successfully')
    except Exception as e:
        print(f'[INIT] ❌ Error initializing services: {e}')
        traceback.print_exc()
        return

    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f'✅ Synced {len(synced)} slash command(s)')
    except Exception as e:
        print(f'❌ Error syncing commands: {e}')

    # Start automatic signal monitoring
    if server_configs:
        check_signals.start()
        print(f'✅ Auto-signal monitoring started (every {CHECK_INTERVAL_MINUTES} minutes)')
        print(f'📢 Signals will be posted to {len(server_configs)} configured server(s)')
    else:
        print('⚠️  Auto-signals disabled (no servers configured yet)')
        print('💡 Use /setup command in your server to configure signal channel')


@bot.tree.command(name="signal", description="Get ICT trading signal for BTCUSDT")
async def signal(interaction: discord.Interaction):
    """Slash command: /signal - Get current trading signal"""
    try:
        await interaction.response.defer(thinking=True)
        
        # Fetch data and calculate features (use less data for faster response)
        df, latest_candle = get_signal_data(
            symbol='BTCUSDT',
            interval='15m',
            limit=100,  # Reduced from 100 for faster response
            swing_length=SWING_LENGTH
        )

        # Get prediction
        prediction = predict_signal(latest_candle)
        current_price = float(latest_candle['close'])
        features = prediction['features']

        # Build response embed
        embed = discord.Embed(
            title="📊 BTC/USDT Signal Analysis",
            description=f"**Timeframe:** 15 minutes\n**Signal:** {prediction['signal'].upper()}",
            color=get_signal_color(prediction['signal'])
        )

        signal_emoji = {
            'buy': '🟢',
            'short': '🔴',
            'neutral': '⚪'
        }

        embed.add_field(
            name=f"{signal_emoji[prediction['signal']]} Signal",
            value=f"**{prediction['signal'].upper()}**",
            inline=True
        )

        embed.add_field(
            name="🎯 Cluster",
            value=f"Cluster {prediction['cluster']}",
            inline=True
        )

        embed.add_field(
            name="💰 Current Price",
            value=f"${current_price:,.2f}",
            inline=True
        )

        # Smart Money Concepts levels
        smc_info = []

        if features['FVG_flag'] == 1:
            smc_info.append(f"**FVG Zone:** ${features['FVG_Bottom']:,.2f} - ${features['FVG_Top']:,.2f}")
        else:
            smc_info.append("**FVG:** No active gap")

        if features['OB_flag'] == 1:
            smc_info.append(f"**Order Block:** ${features['OB_Bottom']:,.2f} - ${features['OB_Top']:,.2f}")
        else:
            smc_info.append("**Order Block:** None detected")

        if features['Swing_Level'] > 0:
            swing_type = "High" if features['Swing_HighLow'] == 1 else "Low" if features['Swing_HighLow'] == -1 else "None"
            if swing_type != "None":
                smc_info.append(f"**Swing {swing_type}:** ${features['Swing_Level']:,.2f}")

        embed.add_field(
            name="📍 Smart Money Concepts",
            value="\n".join(smc_info) if smc_info else "No active levels",
            inline=False
        )

        embed.add_field(
            name="💡 Explanation",
            value=prediction['explanation'],
            inline=False
        )

        cluster_info = get_cluster_info(prediction['cluster'])
        embed.add_field(
            name="📖 Pattern Info",
            value=f"**{cluster_info['name']}**\n{cluster_info['description']}\n*Action: {cluster_info['action']}*",
            inline=False
        )

        embed.set_footer(text="⚠️ This is not financial advice. Trade at your own risk.")
        embed.timestamp = discord.utils.utcnow()

        await interaction.followup.send(embed=embed)
        print(f"[/signal] ✅ Signal sent successfully to {interaction.user.name}")

    except Exception as e:
        print(f"[/signal] ❌ ERROR: {e}")
        traceback.print_exc()
        error_embed = discord.Embed(
            title="❌ Error",
            description=f"Failed to generate signal. This could be due to:\n• Network issues with Binance\n• Data processing error\n\nPlease try again in a moment.",
            color=discord.Color.red()
        )
        
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=error_embed, ephemeral=True)
        except:
            pass  # If we can't send error message, just log it


@bot.tree.command(name="info", description="Get information about the bot")
async def info(interaction: discord.Interaction):
    """Show bot information"""
    embed = discord.Embed(
        title="🤖 ICT Trading Signal Bot",
        description="AI-powered Smart Money Concepts signal generator for BTC/USDT",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="📚 What is ICT?",
        value="Inner Circle Trader (ICT) methodology focuses on Smart Money Concepts like Fair Value Gaps, Order Blocks, and Swing Highs/Lows.",
        inline=False
    )

    embed.add_field(
        name="🧠 How It Works",
        value="Uses K-Means clustering trained on historical BTC data:\n"
              "• **Cluster 4** = Bullish (BUY)\n"
              "• **Cluster 3** = Bearish (SHORT)\n"
              "• **Clusters 0-2** = Neutral",
        inline=False
    )

    embed.add_field(
        name="🔧 Commands",
        value="`/signal` - Get trading signal\n"
              "`/info` - This information\n"
              "`/ping` - Check latency\n"
              "`/setup` - Configure (Admin)\n"
              "`/status` - Check config\n"
              "`/remove` - Disable (Admin)",
        inline=False
    )

    embed.set_footer(text="⚠️ Educational purposes only. Not financial advice.")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Bot latency: **{latency}ms**",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="setup", description="Configure signal channel (Admin only)")
@app_commands.describe(channel="The channel where signals will be posted")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction, channel: discord.TextChannel):
    """Configure signal channel for server"""
    try:
        guild_id = interaction.guild_id
        channel_id = channel.id

        server_configs[guild_id] = channel_id
        save_server_configs()

        if not check_signals.is_running():
            check_signals.start()
            print(f'✅ Auto-signal monitoring started')

        embed = discord.Embed(
            title="✅ Setup Complete",
            description=f"Signal channel has been set to {channel.mention}",
            color=discord.Color.green()
        )

        embed.add_field(
            name="What's Next?",
            value=f"• Automatic signals every {CHECK_INTERVAL_MINUTES} minutes\n"
                  "• Use `/signal` for on-demand signals\n"
                  "• Use `/status` to check configuration",
            inline=False
        )

        embed.set_footer(text="Only administrators can change this configuration")
        await interaction.response.send_message(embed=embed)
        print(f'✅ Server {interaction.guild.name} configured with channel #{channel.name}')
    except Exception as e:
        print(f"[/setup] ❌ ERROR: {e}")
        traceback.print_exc()
        if not interaction.response.is_done():
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Error",
                    description=f"Failed to setup: {str(e)}",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )


@bot.tree.command(name="remove", description="Remove signal configuration (Admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def remove(interaction: discord.Interaction):
    """Remove signal channel configuration"""
    guild_id = interaction.guild_id

    if guild_id in server_configs:
        del server_configs[guild_id]
        save_server_configs()

        embed = discord.Embed(
            title="✅ Configuration Removed",
            description="Automatic signals have been disabled for this server.",
            color=discord.Color.orange()
        )

        embed.add_field(
            name="Note",
            value="You can still use `/signal` for on-demand signals.\n"
                  "Use `/setup` to re-enable automatic signals.",
            inline=False
        )

        await interaction.response.send_message(embed=embed)
        print(f'🗑️  Configuration removed for server {interaction.guild.name}')

        if not server_configs and check_signals.is_running():
            check_signals.stop()
            print('⏸️  Auto-signal monitoring stopped')
    else:
        embed = discord.Embed(
            title="ℹ️ Not Configured",
            description="This server doesn't have automatic signals configured.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="status", description="Check current bot configuration")
async def status(interaction: discord.Interaction):
    """Show current configuration status"""
    guild_id = interaction.guild_id

    embed = discord.Embed(
        title="📊 Server Configuration Status",
        color=discord.Color.blue()
    )

    if guild_id in server_configs:
        channel_id = server_configs[guild_id]
        try:
            channel = await bot.fetch_channel(channel_id)
            embed.description = "✅ Automatic signals are **enabled**"
            embed.add_field(name="Signal Channel", value=f"{channel.mention}", inline=False)
            embed.add_field(name="Update Frequency", value=f"Every {CHECK_INTERVAL_MINUTES} minutes", inline=True)
            embed.add_field(name="Status", value="🟢 Active" if check_signals.is_running() else "🔴 Inactive", inline=True)
            embed.color = discord.Color.green()
        except:
            embed.description = "⚠️ Configuration exists but channel is invalid"
            embed.add_field(name="Action Required", value="Use `/setup` to reconfigure", inline=False)
            embed.color = discord.Color.orange()
    else:
        embed.description = "❌ Automatic signals are **not configured**"
        embed.add_field(name="To Enable", value="Use `/setup #channel` to configure", inline=False)
        embed.color = discord.Color.red()

    embed.add_field(name="Manual Signals", value="Use `/signal` anytime for on-demand signals", inline=False)
    await interaction.response.send_message(embed=embed)


def get_signal_color(signal):
    """Get embed color based on signal type"""
    colors = {
        'buy': discord.Color.green(),
        'short': discord.Color.red(),
        'neutral': discord.Color.light_gray()
    }
    return colors.get(signal, discord.Color.blue())


@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        return
    print(f'Error: {error}')


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handle slash command errors"""
    if isinstance(error, app_commands.MissingPermissions):
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="You need **Administrator** permission to use this command.",
            color=discord.Color.red()
        )
        embed.set_footer(text="Ask a server administrator for help.")
        
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)
    elif isinstance(error, app_commands.CommandInvokeError):
        print(f'❌ Command invoke error: {error}')
        print(f'   Original error: {error.original}')
        
        # Only respond if we haven't already
        if not interaction.response.is_done():
            embed = discord.Embed(
                title="❌ Command Error",
                description="An error occurred while executing the command. Please try again.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        print(f'❌ Unhandled app command error: {error}')


# ============================================================================
# RUN BOT
# ============================================================================

if __name__ == '__main__':
    print('='*60)
    print('🚀 Starting ICT Trading Signal Bot (INTEGRATED VERSION)')
    print('='*60)
    print(f'📁 Scaler path: {SCALER_PATH}')
    print(f'📁 KMeans path: {KMEANS_PATH}')
    print(f'⏱️  Check interval: {CHECK_INTERVAL_MINUTES} minutes')
    print(f'📊 Swing length: {SWING_LENGTH}')
    print('='*60)

    bot.run(DISCORD_TOKEN)
