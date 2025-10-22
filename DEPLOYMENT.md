# Deploying ICT Discord Bot to Render

This guide will walk you through deploying your Discord trading bot to Render.

## Prerequisites

1. A GitHub account
2. A Render account (sign up at https://render.com)
3. Your Discord bot token
4. The model files (`scaler.pkl` and `kmeans.pkl`) committed to your repository

## Step 1: Push Code to GitHub

1. **Create a new GitHub repository** (if you haven't already):
   - Go to https://github.com/new
   - Name it something like `ict-discord-bot`
   - Choose Public or Private
   - Don't initialize with README (we already have files)

2. **Update the render.yaml file** with your GitHub repository URL:
   ```yaml
   repo: https://github.com/YOUR_USERNAME/YOUR_REPO_NAME
   ```

3. **Push your code to GitHub**:
   ```bash
   # If you haven't set up remote yet
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

   # Add all files
   git add .

   # Commit changes
   git commit -m "Prepare for Render deployment"

   # Push to GitHub
   git push -u origin main
   ```

## Step 2: Deploy on Render

### Option A: Using Blueprint (render.yaml) - RECOMMENDED

1. **Log in to Render** at https://dashboard.render.com

2. **Click "New" → "Blueprint"**

3. **Connect your GitHub repository**:
   - Click "Connect a repository"
   - Select your repository
   - Click "Connect"

4. **Configure the service**:
   - Render will automatically detect the `render.yaml` file
   - Review the configuration
   - Click "Apply"

5. **Set your environment variables**:
   - In the Render dashboard, go to your service
   - Click "Environment"
   - Set `DISCORD_BOT_TOKEN` to your actual Discord bot token
   - The other environment variables are already set in render.yaml

6. **Deploy**:
   - Render will automatically build and deploy your bot
   - Wait for the build to complete (5-10 minutes)

### Option B: Manual Deployment

1. **Log in to Render** at https://dashboard.render.com

2. **Click "New" → "Web Service"**

3. **Connect your GitHub repository**

4. **Configure the service**:
   - **Name**: `ict-discord-bot`
   - **Runtime**: Docker
   - **Plan**: Free
   - **Branch**: main
   - **Dockerfile Path**: `./Dockerfile`

5. **Set environment variables**:
   - `DISCORD_BOT_TOKEN`: Your Discord bot token
   - `SCALER_PATH`: `./scaler.pkl`
   - `KMEANS_PATH`: `./kmeans.pkl`
   - `SWING_LENGTH`: `15`
   - `CHECK_INTERVAL_MINUTES`: `15`
   - `SERVER_CONFIG_FILE`: `server_config.json`

6. **Click "Create Web Service"**

7. **Important**: After creation, go to Settings and change:
   - Service Type: **Background Worker** (not Web Service)
   - This is because the bot doesn't serve HTTP requests

## Step 3: Verify Deployment

1. **Check the logs** in Render dashboard:
   - Look for "Bot logged in as [BOT_NAME]"
   - Check for "Synced X slash command(s)"
   - Verify no errors appear

2. **Test in Discord**:
   - Type `/signal` in your Discord server
   - Type `/info` to see bot information
   - Type `/ping` to check latency

3. **Configure automatic signals** (admin only):
   - Type `/setup #channel-name` to set up automatic signals
   - Type `/status` to verify configuration

## Step 4: Monitor Your Bot

1. **View logs** in Render dashboard to troubleshoot issues
2. **Check metrics** to monitor bot performance
3. **Enable notifications** for deployment failures

## Important Notes

### Free Tier Limitations
- Render's free tier spins down after 15 minutes of inactivity
- The bot will restart when needed, but there may be brief delays
- For 24/7 uptime, upgrade to a paid plan ($7/month)

### Model Files
- Make sure `scaler.pkl` and `kmeans.pkl` are committed to your repository
- These files are required for the bot to make predictions
- They should be in the root directory of your project

### Environment Variables
- **NEVER** commit your `.env` file or Discord token to GitHub
- Always use Render's environment variable settings for sensitive data
- The `.gitignore` file is configured to exclude `.env`

### Server Configuration
- The `server_config.json` file stores which Discord servers and channels to use
- It's created automatically when you use `/setup`
- This file persists across restarts on Render

## Troubleshooting

### Bot not responding
- Check Render logs for errors
- Verify `DISCORD_BOT_TOKEN` is set correctly
- Make sure the bot has proper permissions in your Discord server

### "Model file not found" error
- Ensure `scaler.pkl` and `kmeans.pkl` are in your GitHub repository
- Check the file paths in environment variables match the actual locations

### Automatic signals not working
- Run `/setup #channel-name` in your Discord server
- Run `/status` to verify configuration
- Check Render logs for scheduled task execution

### Build failures
- Check that all dependencies in `requirements.txt` are correct
- Verify the Dockerfile syntax is correct
- Look at Render build logs for specific error messages

## Updating Your Bot

To deploy updates:

1. **Make changes locally**
2. **Commit changes**: `git commit -am "Description of changes"`
3. **Push to GitHub**: `git push`
4. **Auto-deploy**: Render will automatically rebuild and redeploy (if autoDeploy is enabled)

## Support

For issues specific to:
- **Discord.py**: https://discordpy.readthedocs.io/
- **Render**: https://render.com/docs
- **This bot**: Check the logs and verify your configuration

## Security Best Practices

1. Never share your Discord bot token
2. Use environment variables for all sensitive data
3. Keep your GitHub repository private if it contains any sensitive information
4. Regularly update dependencies for security patches
5. Monitor your bot's activity and logs for unusual behavior
