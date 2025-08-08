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
    print(f"[diag] Logged in as {bot.user} (id: {bot.user.id})")
    print(f"[diag] guilds: {[g.name for g in bot.guilds]}")
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

async def run_discord_bot():
    if not TOKEN:
        raise RuntimeError("Missing DISCORD_TOKEN secret")
    await bot.start(TOKEN)