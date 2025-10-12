"""
ICT Trading Signal Discord Bot
Simple on-demand signal generation for BTCUSDT
"""
import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
import json
from dotenv import load_dotenv
from services.binance_service import BinanceService
from services.prediction_service import PredictionService

# Load environment variables
load_dotenv()

# Configuration
DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
CHECK_INTERVAL_MINUTES = int(os.getenv('CHECK_INTERVAL_MINUTES', '15'))  # How often to check for signals
SCALER_PATH = os.getenv('SCALER_PATH', './scaler.pkl')
KMEANS_PATH = os.getenv('KMEANS_PATH', './kmeans.pkl')
SWING_LENGTH = int(os.getenv('SWING_LENGTH', '15'))  # Length for swing high/low detection
SERVER_CONFIG_FILE = os.getenv('SERVER_CONFIG_FILE', 'server_config.json')

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
server_configs = {}  # Store channel configurations per server: {guild_id: channel_id}


def load_server_configs():
    """Load server configurations from JSON file"""
    global server_configs
    try:
        if os.path.exists(SERVER_CONFIG_FILE):
            with open(SERVER_CONFIG_FILE, 'r') as f:
                server_configs = json.load(f)
            # Convert string keys to int
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


@tasks.loop(minutes=CHECK_INTERVAL_MINUTES)
async def check_signals():
    """
    Background task that runs every 15 minutes to send signal status updates
    Sends regular updates about current signal status to all configured channels
    """
    global last_signal

    if not server_configs:
        return  # No servers configured

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

        # Send to all configured channels
        success_count = 0
        for guild_id, channel_id in server_configs.items():
            try:
                channel = await bot.fetch_channel(channel_id)
                await channel.send(content=ping_message, embed=embed)
                success_count += 1
            except discord.NotFound:
                print(f'❌ Channel {channel_id} not found (Server ID: {guild_id})')
            except discord.Forbidden:
                print(f'❌ No permission for channel {channel_id} (Server ID: {guild_id})')
            except Exception as e:
                print(f'❌ Error sending to channel {channel_id}: {e}')

        if is_new_signal:
            print(f'🚨 NEW {current_signal.upper()} signal sent to {success_count}/{len(server_configs)} server(s)')
        else:
            print(f'📊 Status update sent to {success_count}/{len(server_configs)} server(s) - Signal: {current_signal.upper()}')

    except Exception as e:
        print(f'❌ Error in check_signals: {e}')


@bot.event
async def on_ready():
    """Bot startup event"""
    global binance_service, prediction_service

    print(f'🤖 Bot logged in as {bot.user}')
    print(f'📊 Connected to {len(bot.guilds)} server(s)')
    
    # List all servers
    for guild in bot.guilds:
        print(f'   └─ {guild.name} (ID: {guild.id})')

    # Load server configurations
    load_server_configs()

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

    # Start automatic signal monitoring if any server is configured
    if server_configs:
        check_signals.start()
        print(f'✅ Auto-signal monitoring started (every {CHECK_INTERVAL_MINUTES} minutes)')
        print(f'📢 Signals will be posted to {len(server_configs)} configured server(s)')
    else:
        print('⚠️  Auto-signals disabled (no servers configured yet)')
        print('💡 Use /setup command in your server to configure signal channel')


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
              "`/ping` - Check bot latency\n"
              "`/setup` - Configure signal channel (Admin)\n"
              "`/status` - Check server configuration\n"
              "`/remove` - Disable automatic signals (Admin)",
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


@bot.tree.command(name="setup", description="Configure signal channel for this server (Admin only)")
@app_commands.describe(channel="The channel where signals will be posted")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction, channel: discord.TextChannel):
    """
    Slash command: /setup
    Configure the signal channel for the current server
    Requires administrator permission
    """
    guild_id = interaction.guild_id
    channel_id = channel.id
    
    # Save configuration
    server_configs[guild_id] = channel_id
    save_server_configs()
    
    # Start monitoring if not already running
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
        value=f"• Automatic signals will be posted every {CHECK_INTERVAL_MINUTES} minutes\n"
              "• Use `/signal` to get a signal on-demand\n"
              "• Use `/status` to check current configuration",
        inline=False
    )
    
    embed.set_footer(text="Only administrators can change this configuration")
    
    await interaction.response.send_message(embed=embed)
    print(f'✅ Server {interaction.guild.name} (ID: {guild_id}) configured with channel #{channel.name} (ID: {channel_id})')


@bot.tree.command(name="remove", description="Remove signal configuration from this server (Admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def remove(interaction: discord.Interaction):
    """
    Slash command: /remove
    Remove the signal channel configuration for the current server
    Requires administrator permission
    """
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
            value="You can still use `/signal` to get signals on-demand.\n"
                  "Use `/setup` to re-enable automatic signals.",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
        print(f'🗑️  Configuration removed for server {interaction.guild.name} (ID: {guild_id})')
        
        # Stop monitoring if no servers configured
        if not server_configs and check_signals.is_running():
            check_signals.stop()
            print('⏸️  Auto-signal monitoring stopped (no servers configured)')
    else:
        embed = discord.Embed(
            title="ℹ️ Not Configured",
            description="This server doesn't have automatic signals configured.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="status", description="Check current bot configuration for this server")
async def status(interaction: discord.Interaction):
    """
    Slash command: /status
    Show current configuration status for the server
    """
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
            embed.add_field(
                name="Signal Channel",
                value=f"{channel.mention}",
                inline=False
            )
            embed.add_field(
                name="Update Frequency",
                value=f"Every {CHECK_INTERVAL_MINUTES} minutes",
                inline=True
            )
            embed.add_field(
                name="Status",
                value="🟢 Active" if check_signals.is_running() else "🔴 Inactive",
                inline=True
            )
            embed.color = discord.Color.green()
        except:
            embed.description = "⚠️ Configuration exists but channel is invalid"
            embed.add_field(
                name="Action Required",
                value="Use `/setup` to reconfigure the signal channel",
                inline=False
            )
            embed.color = discord.Color.orange()
    else:
        embed.description = "❌ Automatic signals are **not configured**"
        embed.add_field(
            name="To Enable",
            value="Use `/setup #channel` to configure automatic signals",
            inline=False
        )
        embed.color = discord.Color.red()
    
    embed.add_field(
        name="Manual Signals",
        value="Use `/signal` anytime to get a signal on-demand",
        inline=False
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
