# Railway Deployment Guide

## Quick Deploy Steps

1. **Create Railway Project**
   - Go to railway.app → New Project → Deploy from GitHub → pick your repo

2. **Configure Environment Variables**
   After the initial build, go to Variables and add:
   - `DISCORD_TOKEN` - Your Discord bot token
   - `DISCORD_CHANNEL_ID` - Target Discord channel ID for alerts
   - `WEBHOOK_URL` - Discord webhook URL (optional, fallback method)
   - `ALCHEMY_API_KEY` - For Ethereum whale tracking
   - `HELIUS_API_KEY` - For Solana whale tracking
   - `SESSION_SECRET` - Flask session secret (generate random string)

3. **Set Start Command**
   In Settings → Deployments, set the Start Command to:
   ```
   python main.py
   ```

4. **Database Configuration**
   Railway will automatically provide a PostgreSQL database. The `DATABASE_URL` environment variable will be set automatically.

## Environment Variables Details

### Required
- `DISCORD_TOKEN`: Get from Discord Developer Portal → Applications → Your Bot → Bot → Token
- `DISCORD_CHANNEL_ID`: Right-click your Discord channel → Copy ID (Enable Developer Mode first)

### API Keys (For Enhanced Features)
- `ALCHEMY_API_KEY`: Sign up at alchemy.com for Ethereum webhook alerts
- `HELIUS_API_KEY`: Sign up at helius.dev for Solana webhook alerts

### Optional
- `WEBHOOK_URL`: Discord webhook URL for backup message delivery
- `SESSION_SECRET`: Random string for Flask sessions (Railway can generate this)

## Webhook Setup (Post-Deploy)

After deployment, configure webhooks:

1. **Alchemy Webhook** (Ethereum)
   - URL: `https://your-app.railway.app/alchemy`
   - Add your whale addresses to webhook filters

2. **Helius Webhook** (Solana) 
   - URL: `https://your-app.railway.app/helius`
   - Configure for tracked Solana wallet addresses

## Post-Deploy Commands

Use these Discord commands to manage whale tracking:

**Ethereum Whales:**
- `!whaleadd 0x123...` - Add ETH whale
- `!whaledel 0x123...` - Remove ETH whale  
- `!whalelist` - List all ETH whales

**Solana Whales:**
- `!swhaleadd 9Wz...` - Add SOL whale
- `!swhaledel 9Wz...` - Remove SOL whale
- `!swhalelist` - List all SOL whales

## Monitoring

- Dashboard: `https://your-app.railway.app/`
- Health Check: `https://your-app.railway.app/alchemy` (should return "OK")
- Logs: Available in Railway dashboard

## Support

The bot includes comprehensive error handling and logging. Monitor the Railway logs for any issues during operation.