# discord_bot.py (diagnostic)
import os, requests, discord
from discord.ext import commands
import asyncio

TOKEN = os.getenv("DISCORD_TOKEN")
# accept either name to avoid mismatch
CHAN_ENV = os.getenv("DISCORD_CHANNEL_ID") or os.getenv("CHANNEL_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

# Scanner configuration constants
MIN_LP = 3000
MAX_MC = 1_500_000
MAX_AGE_MIN = 60
MIN_HOLDERS = 0
BANKROLL = float(os.getenv("BANKROLL_DEFAULT", "5000"))
BANKROLL = float(os.getenv("BANKROLL_DEFAULT", "5000"))

def n(x): return "✅" if x else "❌"

async def scanner_loop():
    """Background task to scan for crypto opportunities"""
    from scanner import pick_new_pairs
    
    await bot.wait_until_ready()
    ch = bot.get_channel(CHANNEL_ID) if CHANNEL_ID else None
    print(f"[diag] Scanner loop started with criteria: MIN_LP={MIN_LP}, MAX_MC={MAX_MC:,}, MAX_AGE_MIN={MAX_AGE_MIN}, MIN_HOLDERS={MIN_HOLDERS}")
    print(f"[diag] BANKROLL set to ${int(BANKROLL):,}")
    
    while not bot.is_closed():
        try:
            for hit in pick_new_pairs():
                # Enhanced message with much more detail
                runner_score = hit.get('runner_score', 0)
                age_min = hit.get('age_minutes', 0)
                
                # Format age properly
                if age_min < 60:
                    age_str = f"{int(age_min)}m"
                elif age_min < 1440:
                    age_str = f"{int(age_min/60)}h {int(age_min%60)}m"
                else:
                    age_str = f"{int(age_min/1440)}d {int((age_min%1440)/60)}h"
                
                # Runner potential indicators
                if runner_score >= 4:
                    potential = "🔥 HIGH RUNNER POTENTIAL"
                elif runner_score >= 3:
                    potential = "⚡ GOOD RUNNER POTENTIAL"
                elif runner_score >= 2:
                    potential = "📈 MODERATE POTENTIAL"
                else:
                    potential = "👀 MONITORING"
                
                # Enhanced market data formatting
                def format_dollars(amount):
                    if amount >= 1000000:
                        return f"${amount/1000000:.2f}M"
                    elif amount >= 1000:
                        return f"${amount/1000:.1f}K"
                    else:
                        return f"${amount:.0f}"
                
                mc_formatted = format_dollars(hit.get('market_cap', 0))
                lp_formatted = format_dollars(hit.get('liquidity', 0))
                
                # Chain-specific formatting
                chain = hit['chain'].upper()
                is_solana = chain == 'SOLANA'
                is_ethereum = chain == 'ETHEREUM'
                
                # Chain-specific links and formatting
                if is_solana:
                    explorer_link = f"[Token: `{hit['token'][:8]}...`](https://solscan.io/token/{hit['token']})"
                    pump_link = f"• [Pump.fun](https://pump.fun/{hit['token']})\n"
                    chain_emoji = "☀️"
                elif is_ethereum:
                    explorer_link = f"[Token: `{hit['token'][:8]}...`](https://etherscan.io/token/{hit['token']})"
                    pump_link = f"• [Etherscan](https://etherscan.io/token/{hit['token']})\n"
                    chain_emoji = "⛽"
                else:
                    explorer_link = f"Token: `{hit['token'][:8]}...`"
                    pump_link = ""
                    chain_emoji = "🔗"
                
                # Add paper trading and sentiment suggestions
                paper_trade_msg = f"\n\n💡 **Paper Trade**: `!enter {hit['token']} 1000` ($1000 position)"
                sentiment_msg = f"\n📊 **React to share sentiment**: 🚀 Bullish • 📉 Bearish • 🤔 Uncertain"
                
                text = (
                    f"🚨 **{chain_emoji} {chain} RUNNER ALERT** 🚨\n\n"
                    f"🎯 **{hit['name']}** (${hit['symbol']})\n"
                    f"**Score:** {runner_score}/5 ⭐\n"
                    f"{potential}\n\n"
                    f"💰 **MARKET DATA**\n"
                    f"• Market Cap: {mc_formatted}\n"
                    f"• Liquidity: {lp_formatted}\n"
                    f"• Holders: {hit['holders']:,}\n"
                    f"• Age: {age_str}\n\n"
                    f"🔗 **LINKS**\n"
                    f"• [Chart]({hit['chart']})\n"
                    f"• {explorer_link}\n"
                    f"{pump_link}\n"
                    f"**Chain:** {chain}\n"
                    f"**Why This Matters:** Fresh {chain.lower()} token with runner characteristics detected by multi-source analysis{paper_trade_msg}{sentiment_msg}"
                )
                if ch: 
                    message = await ch.send(text)
                    # Register alert for sentiment tracking
                    try:
                        from sentiment_tracker import register_runner_alert
                        register_runner_alert(
                            str(message.id),
                            hit['token'],
                            hit['symbol'],
                            hit['chain'].lower(),
                            runner_score
                        )
                        # Add initial reaction options for users
                        await message.add_reaction("🚀")  # Bullish
                        await message.add_reaction("📉")  # Bearish  
                        await message.add_reaction("🤔")  # Uncertain
                        
                        # Enhanced data for Solana tokens using Helius
                        if hit['chain'].lower() == 'solana':
                            try:
                                from helius_integration import get_enhanced_solana_data
                                enhanced_data = get_enhanced_solana_data(hit['token'])
                                if enhanced_data and enhanced_data.get('risk_flags'):
                                    risk_flags = enhanced_data['risk_flags']
                                    print(f"[helius] Risk flags for {hit['symbol']}: {risk_flags}")
                                    
                                    # Add risk warning to message if critical risks detected
                                    if any(flag in ['HIGH_WHALE_CONCENTRATION', 'LOW_HOLDER_COUNT'] for flag in risk_flags):
                                        warning_msg = f"\n⚠️ **Risk Warning**: {', '.join(risk_flags).replace('_', ' ').lower()}"
                                        # Send follow-up message with risk analysis
                                        await ch.send(f"🔍 **Helius Risk Analysis for {hit['symbol']}**{warning_msg}")
                                        
                                if enhanced_data and enhanced_data.get('holder_count'):
                                    holder_count = enhanced_data['holder_count']
                                    whale_conc = enhanced_data.get('whale_concentration', 0)
                                    print(f"[helius] {hit['symbol']}: {holder_count} holders, whale concentration: {whale_conc:.1f}%")
                                    
                                    # Add Helius insights to the main alert message
                                    if holder_count > 0:
                                        helius_insight = f"\n🔍 **Helius**: {holder_count:,} holders, {whale_conc:.1f}% whale concentration"
                                        if risk_flags:
                                            helius_insight += f" | ⚠️ {len(risk_flags)} risk flags"
                                        await ch.send(f"📊 **Enhanced Analysis for {hit['symbol']}**{helius_insight}")
                            except Exception as e:
                                print(f"[helius] Error getting enhanced data: {e}")
                        
                        # Enhanced data for Ethereum tokens using Alchemy
                        elif hit['chain'].lower() == 'ethereum':
                            try:
                                from alchemy_integration import get_enhanced_ethereum_data
                                enhanced_data = get_enhanced_ethereum_data(hit['token'])
                                if enhanced_data and enhanced_data.get('risk_flags'):
                                    risk_flags = enhanced_data['risk_flags']
                                    print(f"[alchemy] Risk flags for {hit['symbol']}: {risk_flags}")
                                    
                                    # Add risk warning to message if critical risks detected
                                    if any(flag in ['LOW_ACTIVITY', 'ZERO_SUPPLY'] for flag in risk_flags):
                                        warning_msg = f"\n⚠️ **Risk Warning**: {', '.join(risk_flags).replace('_', ' ').lower()}"
                                        # Send follow-up message with risk analysis
                                        await ch.send(f"🔍 **Alchemy Risk Analysis for {hit['symbol']}**{warning_msg}")
                                
                                if enhanced_data and enhanced_data.get('transaction_count'):
                                    tx_count = enhanced_data['transaction_count']
                                    activity_score = enhanced_data.get('activity_score', 0)
                                    print(f"[alchemy] {hit['symbol']}: {tx_count} recent transactions, activity score: {activity_score:.1f}")
                                    
                                    # Add Alchemy insights to the main alert message
                                    if tx_count > 0:
                                        alchemy_insight = f"\n⚗️ **Alchemy**: {tx_count} recent transactions, activity score: {activity_score:.1f}/5.0"
                                        if enhanced_data.get('risk_flags'):
                                            alchemy_insight += f" | ⚠️ {len(enhanced_data['risk_flags'])} risk flags"
                                        await ch.send(f"📊 **Enhanced Analysis for {hit['symbol']}**{alchemy_insight}")
                            except Exception as e:
                                print(f"[alchemy] Error getting enhanced data: {e}")
                    except Exception as e:
                        print(f"[sentiment_tracker] Error registering alert or adding reactions: {e}")
                webhook_send(text)
        except Exception as e:
            print("[scanner_loop]", e)
        
        await asyncio.sleep(20)  # gentle poll for free tier
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
    
    # Start scanner loop
    bot.loop.create_task(scanner_loop())
    
    # Bot is ready and connected
    
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

@bot.command()
async def scan(ctx):
    """Raw test: fetch recent pairs via DexScreener search (no filters)."""
    import requests

    total = 0
    for chain in ["solana", "ethereum"]:
        url = f"https://api.dexscreener.com/latest/dex/search?q={chain}"
        try:
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            await ctx.send(f"{chain} HTTP {r.status_code}")
            if r.status_code != 200:
                continue

            data = r.json()
            pairs = data.get("pairs", [])[:3]   # just show first 3 results
            total += len(pairs)

            for p in pairs:
                base = (p.get("baseToken") or {})
                symbol = base.get("symbol") or base.get("name") or "?"
                name = base.get("name") or symbol
                fdv = p.get("fdv")
                lp = (p.get("liquidity") or {}).get("usd")
                link = p.get("url") or p.get("pairUrl") or "N/A"

                mc_txt = "n/a" if not fdv else f"${int(fdv):,}"
                lp_txt = "n/a" if not lp else f"${int(lp):,}"

                await ctx.send(
                    f"🧪 {chain.title()}: {name} ({symbol})\n"
                    f"MC: {mc_txt} | LP: {lp_txt}\n"
                    f"{link}"
                )
        except Exception as e:
            await ctx.send(f"{chain} error: {e}")

    await ctx.send(f"🔎 Raw scan returned {total} pairs")

# Paper Trading Commands
@bot.command(name='enter')
async def paper_enter(ctx, token_address: str = None, size: str = None):
    """Enter a paper trading position: !enter <token_address> <size_usd>"""
    from paper_trading import paper_engine
    
    if not token_address or not size:
        await ctx.send("Usage: `!enter <token_address> <size_usd>`")
        return
    
    try:
        size_usd = float(size)
        # Determine chain based on token address length (rough heuristic)
        chain = "ethereum" if len(token_address) == 42 and token_address.startswith("0x") else "solana"
        symbol = token_address[:8] + "..." if len(token_address) > 8 else token_address
        
        result = paper_engine.enter_position(token_address, symbol, chain, size_usd)
        await ctx.send(result["message"])
    except ValueError:
        await ctx.send("Invalid size amount")
    except Exception as e:
        await ctx.send(f"Error entering position: {e}")

@bot.command(name='exit')
async def paper_exit(ctx, token_identifier: str = None):
    """Exit a paper trading position: !exit <token_address_or_symbol>"""
    from paper_trading import paper_engine
    
    if not token_identifier:
        await ctx.send("Usage: `!exit <token_address_or_symbol>`")
        return
    
    try:
        result = paper_engine.exit_position(token_identifier)
        await ctx.send(result["message"])
    except Exception as e:
        await ctx.send(f"Error exiting position: {e}")

@bot.command(name='pnl')
async def paper_pnl(ctx):
    """Show paper trading P/L summary: !pnl"""
    from paper_trading import paper_engine
    
    try:
        summary = paper_engine.get_pnl_summary()
        
        response = f"📊 **Paper Trading Summary**\n\n"
        response += f"💰 **P/L Overview**\n"
        response += f"• Open P/L: ${summary['open_pnl']:+.2f}\n"
        response += f"• Closed P/L: ${summary['closed_pnl']:+.2f}\n"
        response += f"• **Total P/L: ${summary['total_pnl']:+.2f}**\n\n"
        
        response += f"📈 **Stats**\n"
        response += f"• Open Positions: {summary['open_positions']}\n"
        response += f"• Closed Trades: {summary['closed_positions']}\n"
        response += f"• Win Rate: {summary['win_rate']:.1f}%\n"
        
        if summary['open_positions_data']:
            response += f"\n🔓 **Open Positions**\n"
            for pos in summary['open_positions_data']:
                response += f"• {pos['symbol']} ({pos['chain']}): {pos['pnl_percent']:+.2f}% (${pos['pnl_usd']:+.2f})\n"
        
        if summary['recent_closed']:
            response += f"\n📝 **Recent Closed**\n"
            for pos in summary['recent_closed']:
                response += f"• {pos.token_symbol}: {pos.pnl_percent:+.2f}% (${pos.pnl_usd:+.2f})\n"
        
        await ctx.send(response)
        
    except Exception as e:
        await ctx.send(f"Error getting P/L summary: {e}")

# Sentiment Tracking Commands
@bot.command(name='sentiment')
async def sentiment_analysis(ctx, token: str = None):
    """Show sentiment analysis: !sentiment or !sentiment <token>"""
    from sentiment_tracker import get_sentiment_command_response
    
    try:
        if token:
            command = f"!sentiment {token}"
        else:
            command = "!sentiment"
        
        response = get_sentiment_command_response(command)
        await ctx.send(response)
        
    except Exception as e:
        await ctx.send(f"Error getting sentiment analysis: {e}")

@bot.command(name='analyze')
async def enhanced_analyze(ctx, token_address: str = None, chain: str = "auto"):
    """Deep analysis using premium APIs: !analyze <token_address> [solana|ethereum|auto]"""
    if not token_address:
        await ctx.send("Usage: `!analyze <token_address> [solana|ethereum|auto]`")
        return
    
    try:
        # Auto-detect chain based on address format
        if chain == "auto":
            if len(token_address) == 42 and token_address.startswith("0x"):
                chain = "ethereum"
            elif len(token_address) >= 32 and not token_address.startswith("0x"):
                chain = "solana"
            else:
                await ctx.send("Could not detect chain. Please specify: `!analyze <address> solana` or `!analyze <address> ethereum`")
                return
        
        if chain.lower() == "solana":
            from helius_integration import get_enhanced_solana_data, is_helius_available
            
            if not is_helius_available():
                await ctx.send("Helius API not available for Solana analysis")
                return
            
            await ctx.send(f"🔍 Analyzing Solana token {token_address[:8]}... (using Helius)")
            
            enhanced_data = get_enhanced_solana_data(token_address)
            
            if not enhanced_data:
                await ctx.send("Could not retrieve enhanced data for this token")
                return
            
            # Format Solana analysis
            response = f"🔬 **Helius Deep Analysis (Solana)**\n\n"
            
            if enhanced_data.get('metadata'):
                response += f"🏷️ **Token Info**\n"
                response += f"• Name: {enhanced_data.get('name', 'Unknown')}\n"
                response += f"• Symbol: {enhanced_data.get('symbol', 'UNK')}\n"
                response += f"• Verified: {'✅' if enhanced_data.get('verified', False) else '❌'}\n\n"
            
            response += f"👥 **Holder Analysis**\n"
            response += f"• Total Holders: {enhanced_data.get('holder_count', 0):,}\n"
            response += f"• Whale Concentration: {enhanced_data.get('whale_concentration', 0):.1f}%\n\n"
            
            risk_flags = enhanced_data.get('risk_flags', [])
            if risk_flags:
                response += f"⚠️ **Risk Flags**\n"
                for flag in risk_flags:
                    response += f"• {flag.replace('_', ' ').title()}\n"
            else:
                response += f"✅ **Risk Assessment**: No major flags detected\n"
            
            response += f"\n🎯 **Investment Signal**: "
            if enhanced_data.get('whale_concentration', 0) > 80:
                response += "🔴 High Risk (Whale Dominated)"
            elif enhanced_data.get('holder_count', 0) < 50:
                response += "🟡 Medium Risk (Low Holders)"
            elif len(risk_flags) == 0:
                response += "🟢 Low Risk (Good Distribution)"
            else:
                response += "🟡 Medium Risk (Some Concerns)"
                
        elif chain.lower() == "ethereum":
            from alchemy_integration import get_enhanced_ethereum_data, is_alchemy_available
            
            if not is_alchemy_available():
                await ctx.send("Alchemy API not available for Ethereum analysis")
                return
            
            await ctx.send(f"🔍 Analyzing Ethereum token {token_address[:8]}... (using Alchemy)")
            
            enhanced_data = get_enhanced_ethereum_data(token_address)
            
            if not enhanced_data:
                await ctx.send("Could not retrieve enhanced data for this token")
                return
            
            # Format Ethereum analysis
            response = f"🔬 **Alchemy Deep Analysis (Ethereum)**\n\n"
            
            if enhanced_data.get('metadata'):
                response += f"🏷️ **Token Info**\n"
                response += f"• Name: {enhanced_data.get('name', 'Unknown')}\n"
                response += f"• Symbol: {enhanced_data.get('symbol', 'UNK')}\n"
                response += f"• Decimals: {enhanced_data.get('decimals', 18)}\n"
                response += f"• Total Supply: {enhanced_data.get('total_supply', 0):,}\n\n"
            
            response += f"📊 **Activity Analysis**\n"
            response += f"• Recent Transactions: {enhanced_data.get('transaction_count', 0):,}\n"
            response += f"• Activity Score: {enhanced_data.get('activity_score', 0):.1f}/5.0\n\n"
            
            risk_flags = enhanced_data.get('risk_flags', [])
            if risk_flags:
                response += f"⚠️ **Risk Flags**\n"
                for flag in risk_flags:
                    response += f"• {flag.replace('_', ' ').title()}\n"
            else:
                response += f"✅ **Risk Assessment**: No major flags detected\n"
            
            response += f"\n🎯 **Investment Signal**: "
            if 'ZERO_SUPPLY' in risk_flags:
                response += "🔴 High Risk (Zero Supply)"
            elif enhanced_data.get('transaction_count', 0) < 10:
                response += "🟡 Medium Risk (Low Activity)"
            elif len(risk_flags) == 0 and enhanced_data.get('activity_score', 0) > 2:
                response += "🟢 Low Risk (Good Activity)"
            else:
                response += "🟡 Medium Risk (Some Concerns)"
        else:
            await ctx.send("Invalid chain. Use 'solana' or 'ethereum'")
            return
        
        await ctx.send(response)
        
    except Exception as e:
        await ctx.send(f"Error analyzing token: {e}")

# Whale Tracking Commands
@bot.command(name='whale')
async def whale_management(ctx, action: str = None, chain: str = None, address: str = None):
    """Whale tracking: !whale [add|remove|list] [ethereum|solana] [address]"""
    from whale_tracker import add_whale_address, remove_whale_address, whale_tracker
    
    if not action:
        await ctx.send("Usage: `!whale [add|remove|list] [ethereum|solana] [address]`\n"
                      "Examples:\n"
                      "`!whale add ethereum 0x742d35Cc6634C0532925a3b8D1E5d9E4C42d31E`\n"
                      "`!whale list ethereum`\n"
                      "`!whale remove solana 7VmWs8w...`")
        return
    
    try:
        if action.lower() == "list":
            if not chain:
                await ctx.send("Please specify chain: `!whale list [ethereum|solana]`")
                return
            
            if chain.lower() == "ethereum":
                whales = whale_tracker.get_eth_whales()
                if whales:
                    whale_list = "\n".join([f"• `{addr[:8]}...{addr[-6:]}`" for addr in whales[:20]])
                    await ctx.send(f"🐋 **Ethereum Whales Tracked** ({len(whales)} total)\n{whale_list}")
                else:
                    await ctx.send("No Ethereum whale addresses tracked")
            
            elif chain.lower() == "solana":
                whales = whale_tracker.get_sol_whales()
                if whales:
                    whale_list = "\n".join([f"• `{addr[:8]}...{addr[-6:]}`" for addr in whales[:20]])
                    await ctx.send(f"🐋 **Solana Whales Tracked** ({len(whales)} total)\n{whale_list}")
                else:
                    await ctx.send("No Solana whale addresses tracked")
            
        elif action.lower() == "add":
            if not chain or not address:
                await ctx.send("Usage: `!whale add [ethereum|solana] <address>`")
                return
            
            success = add_whale_address(chain.lower(), address)
            if success:
                await ctx.send(f"✅ Added {chain.lower()} whale address `{address[:8]}...{address[-6:]}`")
            else:
                await ctx.send(f"❌ Address already tracked or invalid format")
        
        elif action.lower() == "remove":
            if not chain or not address:
                await ctx.send("Usage: `!whale remove [ethereum|solana] <address>`")
                return
            
            success = remove_whale_address(chain.lower(), address)
            if success:
                await ctx.send(f"✅ Removed {chain.lower()} whale address `{address[:8]}...{address[-6:]}`")
            else:
                await ctx.send(f"❌ Address not found in tracking list")
        
        else:
            await ctx.send("Invalid action. Use: `add`, `remove`, or `list`")
    
    except Exception as e:
        await ctx.send(f"Error managing whale addresses: {e}")

@bot.event
async def on_reaction_add(reaction, user):
    """Track reactions on runner alert messages"""
    if user.bot:
        return  # Ignore bot reactions
    
    try:
        from sentiment_tracker import handle_reaction_update
        message_id = str(reaction.message.id)
        emoji = str(reaction.emoji)
        count = reaction.count
        
        # Update sentiment tracking
        success = handle_reaction_update(message_id, emoji, count)
        if success:
            print(f"[sentiment_tracker] Updated reaction {emoji} (count: {count}) for message {message_id}")
        
    except Exception as e:
        print(f"[sentiment_tracker] Error handling reaction add: {e}")

@bot.event  
async def on_reaction_remove(reaction, user):
    """Track reaction removals on runner alert messages"""
    if user.bot:
        return  # Ignore bot reactions
    
    try:
        from sentiment_tracker import handle_reaction_update
        message_id = str(reaction.message.id)
        emoji = str(reaction.emoji)
        count = reaction.count
        
        # Update sentiment tracking
        success = handle_reaction_update(message_id, emoji, count)
        if success:
            print(f"[sentiment_tracker] Updated reaction {emoji} (count: {count}) for message {message_id}")
        
    except Exception as e:
        print(f"[sentiment_tracker] Error handling reaction remove: {e}")

# Simplified ETH whale commands for quick management
import json
WHALES_ETH_FILE = "whales_eth.json"

def _load_eth():
    try: return set(json.load(open(WHALES_ETH_FILE)))
    except: return set()

def _save_eth(s):
    try: json.dump(list(s), open(WHALES_ETH_FILE, "w"))
    except: pass

@bot.command()
async def whaleadd(ctx, addr: str):
    """Quick add ETH whale: !whaleadd 0x123..."""
    s = _load_eth(); s.add(addr.lower()); _save_eth(s)
    await ctx.send(f"✅ Added ETH whale: `{addr}`")

@bot.command()
async def whaledel(ctx, addr: str):
    """Quick remove ETH whale: !whaledel 0x123..."""
    s = _load_eth(); s.discard(addr.lower()); _save_eth(s)
    await ctx.send(f"✅ Removed ETH whale: `{addr}`")

@bot.command()
async def whalelist(ctx):
    """List all tracked ETH whales: !whalelist"""
    s = _load_eth()
    if s:
        whale_list = "\n".join(f"- `{a[:8]}...{a[-6:]}`" for a in sorted(s))
        await ctx.send(f"🐋 **ETH Whales Tracked** ({len(s)} total):\n{whale_list}")
    else:
        await ctx.send("No ETH whales tracked yet.")

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