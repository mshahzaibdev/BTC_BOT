"""
ICT Trading Signal Discord Bot
Simple on-demand signal generation for BTCUSDT
"""
import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
from services.binance_service import BinanceService
from services.prediction_service import PredictionService

# Load environment variables
load_dotenv()

# Configuration
DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
SIGNAL_CHANNEL_ID = int(os.getenv('SIGNAL_CHANNEL_ID', '0'))  # Channel where signals will be posted
CHECK_INTERVAL_MINUTES = int(os.getenv('CHECK_INTERVAL_MINUTES', '15'))  # How often to check for signals
SCALER_PATH = os.getenv('SCALER_PATH', './scaler.pkl')
KMEANS_PATH = os.getenv('KMEANS_PATH', './kmeans.pkl')
SWING_LENGTH = int(os.getenv('SWING_LENGTH', '15'))  # Length for swing high/low detection

# Validate token
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN not found in .env file")

# Initialize bot
intents = discord.Intents.default()
# Note: message_content intent removed - enable in Discord Developer Portal if needed
# intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize services (will be set in on_ready)
binance_service = None
prediction_service = None
last_signal = None  # Track the last signal to avoid duplicate alerts


@tasks.loop(minutes=CHECK_INTERVAL_MINUTES)
async def check_signals():
    """
    Background task that runs every 15 minutes to send signal status updates
    Sends regular updates about current signal status
    """
    global last_signal

    try:
        # Fetch latest data
        df, latest_candle = binance_service.get_signal_data(
            symbol='BTCUSDT',
            interval='15m',
            limit=100,
            swing_length=SWING_LENGTH
        )

        # Get prediction
        prediction = prediction_service.predict_signal(latest_candle)
        current_signal = prediction['signal']

        # Get the channel to post in
        try:
            channel = await bot.fetch_channel(SIGNAL_CHANNEL_ID)
        except discord.NotFound:
            print(f'❌ Could not find channel with ID {SIGNAL_CHANNEL_ID}')
            return
        except discord.Forbidden:
            print(f'❌ Bot does not have permission to access channel {SIGNAL_CHANNEL_ID}')
            return

        # Build the status embed
        current_price = float(latest_candle['close'])
        features = prediction['features']

        # Determine if this is a new signal or status update
        is_new_signal = current_signal != last_signal and current_signal in ['buy', 'short']
        last_signal = current_signal

        if is_new_signal:
            # NEW SIGNAL ALERT
            embed = discord.Embed(
                title="🚨 NEW TRADING SIGNAL 🚨",
                description=f"**{current_signal.upper()}** signal detected on BTC/USDT!",
                color=get_signal_color(current_signal)
            )
            ping_message = "@here"
        else:
            # REGULAR STATUS UPDATE
            embed = discord.Embed(
                title="📊 SIGNAL STATUS UPDATE 📊",
                description=f"Current signal status for BTC/USDT",
                color=get_signal_color(current_signal)
            )
            ping_message = ""  # No ping for regular updates

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

        cluster_info = prediction_service.get_cluster_info(prediction['cluster'])
        embed.add_field(
            name="📖 Pattern",
            value=f"**{cluster_info['name']}** - {cluster_info['action']}",
            inline=False
        )

        embed.set_footer(text="⚠️ Not financial advice. DYOR.")
        embed.timestamp = discord.utils.utcnow()

        # Send the update
        await channel.send(content=ping_message, embed=embed)
        if is_new_signal:
            print(f'🚨 NEW {current_signal.upper()} signal sent to channel {SIGNAL_CHANNEL_ID}')
        else:
            print(f'📊 Status update sent to channel {SIGNAL_CHANNEL_ID} - Signal: {current_signal.upper()}')

    except Exception as e:
        print(f'❌ Error in check_signals: {e}')


@bot.event
async def on_ready():
    """Bot startup event"""
    global binance_service, prediction_service

    print(f'🤖 Bot logged in as {bot.user}')
    print(f'📊 Connected to {len(bot.guilds)} server(s)')

    # Initialize services
    try:
        binance_service = BinanceService()
        prediction_service = PredictionService(
            scaler_path=SCALER_PATH,
            kmeans_path=KMEANS_PATH
        )
        print('✅ Services initialized successfully')
    except Exception as e:
        print(f'❌ Error initializing services: {e}')
        return

    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f'✅ Synced {len(synced)} slash command(s)')
    except Exception as e:
        print(f'❌ Error syncing commands: {e}')

    # Start automatic signal monitoring if channel ID is configured
    if SIGNAL_CHANNEL_ID > 0:
        check_signals.start()
        print(f'✅ Auto-signal monitoring started (every {CHECK_INTERVAL_MINUTES} minutes)')
        print(f'📢 Signals will be posted to channel ID: {SIGNAL_CHANNEL_ID}')
    else:
        print('⚠️  Auto-signals disabled (SIGNAL_CHANNEL_ID not set)')


@bot.tree.command(name="signal", description="Get ICT trading signal for BTCUSDT")
async def signal(interaction: discord.Interaction):
    """
    Slash command: /signal
    Fetches latest data and returns trading signal
    """
    await interaction.response.defer(thinking=True)

    try:
        # Fetch data and calculate features
        df, latest_candle = binance_service.get_signal_data(
            symbol='BTCUSDT',
            interval='15m',
            limit=100,
            swing_length=SWING_LENGTH
        )

        # Get prediction
        prediction = prediction_service.predict_signal(latest_candle)

        # Get current price
        current_price = float(latest_candle['close'])

        # Extract features
        features = prediction['features']

        # Build response embed
        embed = discord.Embed(
            title="📊 BTC/USDT Signal Analysis",
            description=f"**Timeframe:** 15 minutes\n**Signal:** {prediction['signal'].upper()}",
            color=get_signal_color(prediction['signal'])
        )

        # Signal emoji
        signal_emoji = {
            'buy': '🟢',
            'short': '🔴',
            'neutral': '⚪'
        }

        # Add fields
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

        # Fair Value Gap
        if features['FVG_flag'] == 1:
            fvg_top = features['FVG_Top']
            fvg_bottom = features['FVG_Bottom']
            smc_info.append(f"**FVG Zone:** ${fvg_bottom:,.2f} - ${fvg_top:,.2f}")
        else:
            smc_info.append("**FVG:** No active gap")

        # Order Block
        if features['OB_flag'] == 1:
            ob_top = features['OB_Top']
            ob_bottom = features['OB_Bottom']
            smc_info.append(f"**Order Block:** ${ob_bottom:,.2f} - ${ob_top:,.2f}")
        else:
            smc_info.append("**Order Block:** None detected")

        # Swing Level
        if features['Swing_Level'] > 0:
            swing_type = "High" if features['Swing_HighLow'] == 1 else "Low" if features['Swing_HighLow'] == -1 else "None"
            if swing_type != "None":
                smc_info.append(f"**Swing {swing_type}:** ${features['Swing_Level']:,.2f}")

        embed.add_field(
            name="📍 Smart Money Concepts",
            value="\n".join(smc_info) if smc_info else "No active levels",
            inline=False
        )

        # Explanation
        embed.add_field(
            name="💡 Explanation",
            value=prediction['explanation'],
            inline=False
        )

        # Get cluster info
        cluster_info = prediction_service.get_cluster_info(prediction['cluster'])
        embed.add_field(
            name="📖 Pattern Info",
            value=f"**{cluster_info['name']}**\n{cluster_info['description']}\n*Action: {cluster_info['action']}*",
            inline=False
        )

        # Footer with disclaimer
        embed.set_footer(text="⚠️ This is not financial advice. Trade at your own risk.")
        embed.timestamp = discord.utils.utcnow()

        await interaction.followup.send(embed=embed)

    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Error",
            description=f"Failed to generate signal: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=error_embed)


@bot.tree.command(name="info", description="Get information about the bot and how it works")
async def info(interaction: discord.Interaction):
    """
    Slash command: /info
    Displays information about the bot
    """
    embed = discord.Embed(
        title="🤖 ICT Trading Signal Bot",
        description="AI-powered Smart Money Concepts signal generator for BTC/USDT",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="📚 What is ICT?",
        value="Inner Circle Trader (ICT) methodology focuses on Smart Money Concepts like Fair Value Gaps, Order Blocks, and Swing Highs/Lows to identify institutional trading patterns.",
        inline=False
    )

    embed.add_field(
        name="🧠 How It Works",
        value="The bot uses K-Means clustering (ML) trained on historical BTC data to classify current market patterns into 5 clusters:\n"
              "• **Cluster 4** = Bullish (BUY signal)\n"
              "• **Cluster 3** = Bearish (SHORT signal)\n"
              "• **Clusters 0, 1, 2** = Neutral (no trade)",
        inline=False
    )

    embed.add_field(
        name="🔧 Commands",
        value="`/signal` - Get current trading signal\n"
              "`/info` - Show this information\n"
              "`/ping` - Check bot latency",
        inline=False
    )

    embed.add_field(
        name="📊 Features Analyzed",
        value="• Fair Value Gaps (FVG)\n• Order Blocks (OB)\n• Swing Highs & Lows\n• 15-minute timeframe\n• 100 candles lookback",
        inline=False
    )

    embed.set_footer(text="⚠️ Educational purposes only. Not financial advice.")

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    """
    Slash command: /ping
    Shows bot latency
    """
    latency = round(bot.latency * 1000)

    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Bot latency: **{latency}ms**",
        color=discord.Color.green()
    )

    await interaction.response.send_message(embed=embed)


def get_signal_color(signal):
    """Get embed color based on signal type"""
    colors = {
        'buy': discord.Color.green(),
        'short': discord.Color.red(),
        'neutral': discord.Color.light_gray()
    }
    return colors.get(signal, discord.Color.blue())


# Error handler
@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        return
    print(f'Error: {error}')


# Run bot
if __name__ == '__main__':
    print('🚀 Starting ICT Trading Signal Bot...')
    print(f'📁 Scaler path: {SCALER_PATH}')
    print(f'📁 KMeans path: {KMEANS_PATH}')
    bot.run(DISCORD_TOKEN)
