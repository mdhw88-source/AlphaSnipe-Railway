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
import requests
import time

# ETH Runner Detection Helper Functions
MAX_MC = 500_000
MAX_AGE_MIN = 24*60
MIN_LP = 15_000

def ds_info(erc20_addr: str):
    """Get DexScreener info for token analysis"""
    try:
        r = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{erc20_addr}", timeout=10)
        if r.status_code != 200: 
            return None
        pairs = r.json().get("pairs") or []
        if not pairs: 
            return None
        # Pick newest EVM pair
        p = sorted(pairs, key=lambda x: x.get("pairCreatedAt") or 0, reverse=True)[0]
        fdv = float(p.get("fdv") or 0)
        lp = float((p.get("liquidity") or {}).get("usd") or 0)
        created = p.get("pairCreatedAt") or int(time.time()*1000)
        age_min = int((time.time()*1000 - created)/60000)
        return {
            "fdv": fdv, 
            "lp": lp, 
            "age_min": age_min,
            "symbol": (p.get("baseToken") or {}).get("symbol") or "?",
            "name": (p.get("baseToken") or {}).get("name") or "?",
            "chart": p.get("url") or p.get("pairUrl") or ""
        }
    except Exception as e:
        print(f"[ds_info] Error fetching token data: {e}")
        return None

def is_runner(meta):
    """Check if token qualifies as a runner based on criteria"""
    if not meta: 
        return False
    if meta["age_min"] > MAX_AGE_MIN: 
        return False
    if meta["fdv"] and meta["fdv"] > MAX_MC: 
        return False
    if meta["lp"] < MIN_LP: 
        return False
    return True

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
                
                # Enhanced whale alert with runner detection
                base_msg = (
                    f"🐋 **ETH Whale {direction}**\n"
                    f"Addr: `{whale_addr[:8]}...{whale_addr[-6:]}`\n"
                    f"Asset: {asset}  |  Amount: {display_value}\n{link}"
                )
                
                # Enhanced token detection for BUY transactions only
                if direction == "BUY":
                    # Extract token contract address from multiple possible locations
                    token_addr = (
                        a.get("rawContract", {}).get("address") 
                        or (a.get("erc20Metadata") or {}).get("contractAddress")
                        or (a.get("log", {}).get("address") if "log" in a else None)
                    )
                    
                    # Analyze token if we have an address
                    if token_addr:
                        meta = ds_info(token_addr)
                        if not is_runner(meta):
                            continue  # Skip low-signal whale transactions
                        
                        # High-signal runner whale alert
                        msg = (
                            f"🚨 **ETH Whale BUY - RUNNER DETECTED** 🚨\n\n"
                            f"🎯 **{meta['name']}** (${meta['symbol']})\n"
                            f"💰 MC: ${int(meta['fdv']):,} | 💧 LP: ${int(meta['lp']):,} | ⏰ Age: {meta['age_min']}m\n\n"
                            f"🐋 **Whale:** `{whale_addr[:8]}...{whale_addr[-6:]}`\n"
                            f"💵 **Amount:** {display_value}\n\n"
                            f"🔗 **Links**\n"
                            f"• [Chart]({meta['chart']})\n"
                            f"• [Transaction]({link})\n\n"
                            f"**Alert:** Fresh runner token with whale accumulation detected"
                        )
                        messages.append(msg)
                    else:
                        # Regular whale alert for transactions without token address
                        messages.append(base_msg)
                else:
                    # SELL transactions get standard whale alerts
                    messages.append(base_msg)
                
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
