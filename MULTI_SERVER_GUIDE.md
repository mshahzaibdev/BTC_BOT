# Multi-Server Support Guide

## 🎉 What Changed?

Your Discord bot now supports **multiple servers**! You can add it to as many Discord servers as you want, and each server can have its own signal channel.

## 🚀 Key Features

### Before (Single Server)
- ❌ Only worked with one hardcoded channel ID
- ❌ Had to edit `.env` file to change channels
- ❌ Couldn't be used in multiple servers

### After (Multi-Server)
- ✅ Works in unlimited Discord servers
- ✅ Each server configures its own channel
- ✅ Simple `/setup` command - no file editing
- ✅ Admins control their own settings
- ✅ Configurations saved automatically

## 📋 How to Use

### 1. Invite the Bot to Multiple Servers

Use the same invite link for all your servers:
1. Go to Discord Developer Portal
2. OAuth2 → URL Generator
3. Select: `bot` + `applications.commands`
4. Permissions: Send Messages, Embed Links, Use Slash Commands, Mention Everyone
5. Copy the URL and use it for each server

### 2. Configure Each Server

In each server where you want automatic signals:

```
/setup #your-signal-channel
```

**Example:**
```
/setup #trading-signals
```

The bot will:
- Start posting signals every 15 minutes to that channel
- Send @here notifications for new BUY/SHORT signals
- Post regular status updates

### 3. Manage Your Configuration

**Check current setup:**
```
/status
```

**Change the channel:**
```
/setup #new-channel
```

**Disable automatic signals:**
```
/remove
```

**Get signal anytime:**
```
/signal
```

## 🔧 New Commands

| Command | Description | Permission Required |
|---------|-------------|-------------------|
| `/setup #channel` | Configure automatic signals | Administrator |
| `/status` | Check if signals are enabled | Everyone |
| `/remove` | Disable automatic signals | Administrator |
| `/signal` | Get signal on-demand | Everyone |
| `/info` | Bot information | Everyone |
| `/ping` | Check latency | Everyone |

## 💾 Configuration Storage

Your server settings are stored in `server_config.json`:

```json
{
  "123456789012345678": 987654321098765432,
  "111222333444555666": 999888777666555444
}
```

This file is automatically created and updated when you use `/setup` or `/remove`.

## 🔒 Permissions

- **Anyone** can use `/signal`, `/info`, `/ping`, and `/status`
- **Only Administrators** can use `/setup` and `/remove`
- This prevents unauthorized users from changing your signal channel

## 📊 How Automatic Signals Work

Once configured:

1. Bot checks BTC/USDT every 15 minutes (configurable)
2. If signal changes to BUY or SHORT → sends alert with @here
3. Otherwise → sends regular status update (no ping)
4. All configured servers get the same signal simultaneously

## 🎯 Use Cases

### Personal Trading Servers
Set up in your private server for your own trading signals.

### Community Servers
Let your community members receive signals in a dedicated channel.

### Multiple Trading Groups
Run the bot in several servers, each with their own signal channel.

### Testing and Production
Use one server for testing and another for live signals.

## 🔍 Troubleshooting

### "This interaction failed"
- Make sure the bot has permissions in the target channel
- Verify you have Administrator permission

### No automatic signals
- Run `/status` to check configuration
- Run `/setup #channel` to configure
- Check bot is online and running

### Want to change channel
- Just run `/setup #new-channel` - it will update automatically

### Signals not posting
- Check bot has Send Messages permission in the channel
- Verify channel ID in `server_config.json` is correct
- Check bot console for error messages

## ⚙️ Configuration Options

Edit your `.env` file to customize:

```env
# How often to check for signals (in minutes)
CHECK_INTERVAL_MINUTES=15

# Swing detection length
SWING_LENGTH=15

# Config file location
SERVER_CONFIG_FILE=server_config.json
```

## 🚀 Migration from Old Version

If you were using the old single-server version:

1. Remove `SIGNAL_CHANNEL_ID` from your `.env` file (no longer needed)
2. Start the bot
3. Run `/setup #channel` in your server
4. Done! The bot will now use the new multi-server system

## 📝 Example Workflow

```
# Step 1: Invite bot to Server A
(Use Discord invite link)

# Step 2: Configure Server A
/setup #signals

✅ Setup Complete
Signal channel has been set to #signals

# Step 3: Invite bot to Server B
(Use same Discord invite link)

# Step 4: Configure Server B
/setup #crypto-alerts

✅ Setup Complete
Signal channel has been set to #crypto-alerts

# Now both servers receive signals automatically!
```

## 🎊 Benefits

1. **Scalable**: Add as many servers as you need
2. **Flexible**: Each server chooses its own channel
3. **Easy**: No file editing or configuration hassles
4. **Secure**: Only admins can change settings
5. **Persistent**: Settings saved even if bot restarts

## 📞 Support

If you have questions:
1. Run `/info` to see bot information
2. Run `/status` to check your configuration
3. Check the main README.md for detailed setup instructions

---

**Enjoy your multi-server trading bot! 🚀📈**
