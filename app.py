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
import json

@app.route('/alchemy', methods=['GET', 'POST'])
def alchemy_webhook():
    """Webhook endpoint for Alchemy ETH whale tracking with health check"""
    # Health check for browser/Alchemy "Test URL"
    if request.method == "GET":
        return "OK (alchemy)", 200

    try:
        payload = request.get_json(force=True, silent=True) or {}
        # Log small snippet for debugging
        print(f"[alchemy] payload: {json.dumps(payload)[:600]}")

        # Support multiple shapes Alchemy may send
        event = payload.get("event") or {}
        activity = (
            event.get("activity")
            or payload.get("activity")
            or payload.get("events")
            or []
        )

        # Load tracked whales from simplified system
        from discord_bot import _load_eth
        watched = _load_eth()
        messages = []

        # Handle both single activity and list of activities
        activity_list = activity if isinstance(activity, list) else ([activity] if activity else [])
        
        for a in activity_list:
            if not a:  # Skip empty activities
                continue
                
            from_addr = (a.get("fromAddress") or "").lower()
            to_addr = (a.get("toAddress") or "").lower()

            # Token/amount extraction with better fallbacks
            asset = (
                a.get("asset") 
                or (a.get("erc20Metadata") or {}).get("symbol")
                or (a.get("erc20Metadata") or {}).get("name")
                or "ETH"
            )
            
            # Extract value from various possible locations
            value = (
                a.get("value") 
                or a.get("amount")
                or (a.get("rawContract") or {}).get("value")
                or (a.get("rawContract") or {}).get("rawValue")
                or ""
            )
            
            # Convert hex values to readable format if needed
            if isinstance(value, str) and value.startswith("0x"):
                try:
                    value = str(int(value, 16))
                except:
                    pass
            
            tx = a.get("hash") or a.get("transactionHash") or ""

            # Only process if we have addresses and they're not empty
            if not from_addr or not to_addr:
                continue

            # Alert only if a watched address is involved (check both systems)
            if (from_addr in watched or to_addr in watched or 
                is_tracked_whale("ethereum", from_addr) or is_tracked_whale("ethereum", to_addr)):
                
                direction = "BUY" if (to_addr in watched or is_tracked_whale("ethereum", to_addr)) else "SELL"
                whale_addr = to_addr if direction == "BUY" else from_addr
                link = f"https://etherscan.io/tx/{tx}" if tx else ""
                
                # Format value for display
                display_value = str(value)[:20] + "..." if len(str(value)) > 20 else str(value)
                
                msg = (
                    f"🐋 **ETH Whale {direction}**\n"
                    f"Addr: `{whale_addr[:8]}...{whale_addr[-6:]}`\n"
                    f"Asset: {asset}  |  Amount: {display_value}\n{link}"
                )
                messages.append(msg)
                print(f"[alchemy] Generated whale alert: {direction} {asset} by {whale_addr[:8]}...")

        # Send messages to Discord via webhook
        for m in messages:
            try:
                from discord_bot import webhook_send
                webhook_send(m)
            except Exception as e:
                print(f"[alchemy_webhook] Error sending alert: {e}")

        return jsonify({"ok": True, "count": len(messages)}), 200

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"[alchemy error] {e}")
        print(f"[alchemy error details] {error_details}")
        # Return 200 so Alchemy doesn't spam retries
        return jsonify({"ok": False, "error": str(e), "details": error_details[:500]}), 200
