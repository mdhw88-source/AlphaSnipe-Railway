# discord_bot.py (diagnostic)
import os, requests, discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
# accept either name to avoid mismatch
CHAN_ENV = os.getenv("DISCORD_CHANNEL_ID") or os.getenv("CHANNEL_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

def n(x): return "✅" if x else "❌"

print(f"[diag] TOKEN present: {n(bool(TOKEN))}")
print(f"[diag] CHANNEL env (DISCORD_CHANNEL_ID or CHANNEL_ID) present: {n(bool(CHAN_ENV))}")
print(f"[diag] WEBHOOK_URL present: {n(bool(WEBHOOK_URL))}")

CHANNEL_ID = int(CHAN_ENV) if CHAN_ENV else 0

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def webhook_send(text: str):
    if WEBHOOK_URL:
        try:
            r = requests.post(WEBHOOK_URL, json={"content": text}, timeout=10)
            print(f"[diag] webhook status: {r.status_code}")
        except Exception as e:
            print(f"[diag] webhook failed: {e}")

@bot.event
async def on_ready():
    from datetime import datetime
    print(f"[diag] Logged in as {bot.user} (id: {bot.user.id})")
    print(f"[diag] guilds: {[g.name for g in bot.guilds]}")
    
    # Update bot status in database
    try:
        from models import BotStatus
        from app import db, app
        
        with app.app_context():
            bot_status = BotStatus.query.first()
            if not bot_status:
                bot_status = BotStatus()
                db.session.add(bot_status)
            
            bot_status.is_online = True
            bot_status.last_heartbeat = datetime.utcnow()
            bot_status.guild_count = len(bot.guilds)
            bot_status.latency = round(bot.latency * 1000, 2)  # Convert to ms
            bot_status.uptime_start = datetime.utcnow()
            
            db.session.commit()
            print("[diag] Updated bot status in database")
    except Exception as e:
        print(f"[diag] Error updating bot status: {e}")
    
    msg = "✅ **Alpha Sniper Bot Online** (diag)"
    if CHANNEL_ID:
        ch = bot.get_channel(CHANNEL_ID)
        print(f"[diag] get_channel → {ch}")
        if ch:
            try:
                await ch.send(msg)
                print("[diag] sent via API")
            except Exception as e:
                print(f"[diag] send error: {e}")
        else:
            print("[diag] channel not found – check ID and that bot is in this server")
    else:
        print("[diag] CHANNEL_ID missing")
    webhook_send(msg)

@bot.command()
async def alert(ctx, token: str="SIMPS", chain: str="Solana",
                mc: str="$120K", lp: str="$17K", holders: str="312"):
    text = f"🚨 **Alpha Alert**\n${token} | {chain}\nMC: {mc} | LP: {lp} | Holders: {holders}"
    await ctx.send(text)
    webhook_send(text)

def get_bot_instance():
    """Get the bot instance for use in Flask routes"""
    return bot

async def send_alert(alert_id):
    """Send an alert via Discord bot"""
    from models import Alert, ActivityLog
    from app import db
    from datetime import datetime
    
    alert = Alert.query.get(alert_id)
    if not alert:
        return False
    
    try:
        # Format the alert message
        message = f"🚨 **{alert.title}**\n{alert.message}"
        if alert.symbol:
            message += f"\nSymbol: {alert.symbol}"
        if alert.price:
            message += f"\nPrice: ${alert.price:,.2f}"
        
        # Send via Discord API
        if CHANNEL_ID and bot.is_ready():
            channel = bot.get_channel(int(alert.channel_id) if alert.channel_id.isdigit() else CHANNEL_ID)
            if channel:
                await channel.send(message)
                
                # Update alert status
                alert.status = 'sent'
                alert.sent_at = datetime.utcnow()
                
                # Log activity
                log = ActivityLog(
                    action=f"Alert sent: {alert.title}",
                    details=f"Sent to channel {alert.channel_id}",
                    status='success'
                )
                db.session.add(log)
                db.session.commit()
                
                print(f"[diag] Alert {alert_id} sent successfully")
                return True
            else:
                raise Exception(f"Channel {alert.channel_id} not found")
        
        # Fallback to webhook
        if WEBHOOK_URL:
            webhook_send(message)
            alert.status = 'sent'
            alert.sent_at = datetime.utcnow()
            
            log = ActivityLog(
                action=f"Alert sent via webhook: {alert.title}",
                details="Sent via webhook fallback",
                status='success'
            )
            db.session.add(log)
            db.session.commit()
            
            print(f"[diag] Alert {alert_id} sent via webhook")
            return True
        
        raise Exception("No valid sending method available")
        
    except Exception as e:
        # Update alert with error
        alert.status = 'failed'
        alert.error_message = str(e)
        
        # Log error
        log = ActivityLog(
            action=f"Alert failed: {alert.title}",
            details=str(e),
            status='error'
        )
        db.session.add(log)
        db.session.commit()
        
        print(f"[diag] Alert {alert_id} failed: {e}")
        return False

async def run_discord_bot():
    if not TOKEN:
        raise RuntimeError("Missing DISCORD_TOKEN secret")
    await bot.start(TOKEN)