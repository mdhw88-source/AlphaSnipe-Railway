import threading
import asyncio
import logging
from app import app
from discord_bot import run_discord_bot

def start_discord_bot():
    """Start the Discord bot in a separate thread"""
    try:
        asyncio.run(run_discord_bot())
    except Exception as e:
        logging.error(f"Discord bot error: {e}")

if __name__ == "__main__":
    # Start Discord bot in a separate thread
    bot_thread = threading.Thread(target=start_discord_bot, daemon=True)
    bot_thread.start()
    
    # Production server configuration with dynamic port
    import os
    app_port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=app_port, debug=False, use_reloader=False)
