import os
import asyncio
import logging
import discord
from discord.ext import commands
from datetime import datetime
from app import app, db
from models import Alert, BotStatus, ActivityLog

# Global bot instance
bot = None
bot_status = None

class AlphaBotClient(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        super().__init__(command_prefix='!', intents=intents)

    async def on_ready(self):
        global bot_status
        logging.info(f'{self.user} has connected to Discord!')
        
        with app.app_context():
            # Update bot status
            bot_status = BotStatus.query.first()
            if not bot_status:
                bot_status = BotStatus()
                db.session.add(bot_status)
            
            bot_status.is_online = True
            bot_status.last_heartbeat = datetime.utcnow()
            bot_status.guild_count = len(self.guilds)
            bot_status.latency = self.latency * 1000  # Convert to ms
            bot_status.uptime_start = datetime.utcnow()
            
            # Log activity
            log = ActivityLog(
                action="Bot Connected",
                details=f"Connected to {len(self.guilds)} guilds",
                status="success"
            )
            db.session.add(log)
            db.session.commit()

    async def on_disconnect(self):
        global bot_status
        logging.warning('Bot disconnected from Discord!')
        
        with app.app_context():
            if bot_status:
                bot_status.is_online = False
                log = ActivityLog(
                    action="Bot Disconnected",
                    details="Lost connection to Discord",
                    status="error"
                )
                db.session.add(log)
                db.session.commit()

async def send_alert(alert_id):
    """Send a specific alert to Discord"""
    global bot
    
    if not bot or not bot.is_ready():
        logging.error("Bot is not ready")
        return False
    
    with app.app_context():
        alert = Alert.query.get(alert_id)
        if not alert:
            logging.error(f"Alert {alert_id} not found")
            return False
        
        try:
            channel = bot.get_channel(int(alert.channel_id))
            if not channel:
                logging.error(f"Channel {alert.channel_id} not found")
                alert.status = 'failed'
                alert.error_message = f"Channel {alert.channel_id} not found"
                db.session.commit()
                return False
            
            # Create embed for the alert
            embed = discord.Embed(
                title=f"🚨 {alert.title}",
                description=alert.message,
                color=0x00ff00,
                timestamp=datetime.utcnow()
            )
            
            if alert.symbol and alert.price:
                embed.add_field(name="Symbol", value=alert.symbol, inline=True)
                embed.add_field(name="Price", value=f"${alert.price:.4f}", inline=True)
            
            embed.set_footer(text="Alpha Sniper Bot")
            
            await channel.send(embed=embed)
            
            # Update alert status
            alert.status = 'sent'
            alert.sent_at = datetime.utcnow()
            
            # Log activity
            log = ActivityLog(
                action="Alert Sent",
                details=f"Alert '{alert.title}' sent to channel {alert.channel_id}",
                status="success"
            )
            db.session.add(log)
            db.session.commit()
            
            logging.info(f"Alert {alert_id} sent successfully")
            return True
            
        except Exception as e:
            logging.error(f"Error sending alert {alert_id}: {e}")
            alert.status = 'failed'
            alert.error_message = str(e)
            
            log = ActivityLog(
                action="Alert Failed",
                details=f"Failed to send alert '{alert.title}': {str(e)}",
                status="error"
            )
            db.session.add(log)
            db.session.commit()
            return False

async def update_bot_status():
    """Update bot status periodically"""
    global bot, bot_status
    
    while True:
        if bot and bot.is_ready():
            with app.app_context():
                if not bot_status:
                    bot_status = BotStatus.query.first()
                    if not bot_status:
                        bot_status = BotStatus()
                        db.session.add(bot_status)
                
                bot_status.is_online = True
                bot_status.last_heartbeat = datetime.utcnow()
                bot_status.guild_count = len(bot.guilds)
                bot_status.latency = bot.latency * 1000
                db.session.commit()
        
        await asyncio.sleep(30)  # Update every 30 seconds

async def run_discord_bot():
    """Main function to run the Discord bot"""
    global bot
    
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logging.error("DISCORD_TOKEN environment variable not set!")
        return
    
    bot = AlphaBotClient()
    
    # Start status update task
    asyncio.create_task(update_bot_status())
    
    try:
        await bot.start(token)
    except Exception as e:
        logging.error(f"Failed to start bot: {e}")

def get_bot_instance():
    """Get the global bot instance"""
    return bot
