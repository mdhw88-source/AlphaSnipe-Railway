import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Set up logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///alpha_bot.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

with app.app_context():
    # Import models to ensure tables are created
    import models
    db.create_all()

# Start Discord bot in a separate thread when app initializes
import threading
import asyncio
from discord_bot import run_discord_bot

def start_discord_bot():
    """Start the Discord bot in a separate thread"""
    try:
        asyncio.run(run_discord_bot())
    except Exception as e:
        logging.error(f"Discord bot error: {e}")

# Start Discord bot thread
bot_thread = threading.Thread(target=start_discord_bot, daemon=True)
bot_thread.start()
logging.info("Discord bot thread started")

# Import routes after app initialization
from routes import *

# Whale tracking webhook endpoints
from whale_tracker import whale_tracker, is_tracked_whale
from flask import request, jsonify

@app.route("/alchemy", methods=["POST"])
def alchemy_webhook():
    """Alchemy webhook endpoint for Ethereum whale tracking"""
    payload = request.get_json(force=True, silent=True) or {}
    event = payload.get("event", {})
    activity = event.get("activity", []) or []
    
    msgs = []
    for a in activity:
        # Common Alchemy fields
        from_addr = (a.get("fromAddress") or "").lower()
        to_addr   = (a.get("toAddress") or "").lower()
        asset     = a.get("asset") or a.get("erc20Symbol") or "ETH"
        value     = a.get("value") or a.get("rawContract", {}).get("value")
        hash_     = a.get("hash") or a.get("transactionHash")

        # Alert only if a watched address is involved
        if is_tracked_whale("ethereum", to_addr) or is_tracked_whale("ethereum", from_addr):
            direction = "BUY" if is_tracked_whale("ethereum", to_addr) else "SELL"
            whale_addr = to_addr if direction == "BUY" else from_addr
            
            alert_msg = whale_tracker.format_whale_alert(
                chain="ethereum",
                direction=direction,
                address=whale_addr,
                asset=asset,
                amount=str(value),
                tx_hash=hash_
            )
            msgs.append(alert_msg)

    # Send alerts to Discord via webhook
    for msg in msgs:
        try:
            from discord_bot import webhook_send
            webhook_send(msg)
        except Exception as e:
            print(f"[alchemy_webhook] Error sending alert: {e}")

    return jsonify({"ok": True, "count": len(msgs)})
