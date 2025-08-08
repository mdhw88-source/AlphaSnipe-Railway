# scanner.py
import time, requests, os, re

DEX_API = "https://api.dexscreener.com/latest/dex/pairs"
CHAINS = ["solana", "ethereum"]  # extend later
MIN_LP = 10000      # USD
MAX_MC = 500_000    # USD
MAX_AGE_MIN = 30
MIN_HOLDERS = 100

NARRATIVE = re.compile(r"(pepe|simps?|simpson|bart|trump|ai|milady|remilio|doge|cat|popcat|wif)", re.I)

seen = set()

def _pairs(chain):
    # Dexscreener “latest pairs” by chain
    url = f"{DEX_API}/{chain}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json().get("pairs", [])[:200]
    except Exception as e:
        print("[scanner] fetch error:", e)
        return []

def pick_new_pairs():
    results = []
    for chain in CHAINS:
        for p in _pairs(chain):
            pair_id = p.get("pairAddress") or p.get("pairCreatedAt")
            if not pair_id or pair_id in seen:
                continue

            age_min = max(0, int((time.time()*1000 - (p.get("pairCreatedAt") or 0)) / 60000))
            liquidity_usd = float(p.get("liquidity", {}).get("usd", 0))
            fdv = float(p.get("fdv") or 0)  # proxy for MC
            holders = int(p.get("holders", 0)) if isinstance(p.get("holders", 0), (int,float)) else 0
            base_symbol = (p.get("baseToken", {}) or {}).get("symbol", "")
            name = (p.get("baseToken", {}) or {}).get("name", "")
            symbol = base_symbol or name

            # basic filters
            if age_min <= MAX_AGE_MIN and liquidity_usd >= MIN_LP and fdv <= MAX_MC:
                if holders < MIN_HOLDERS:
                    continue
                text = f"{name} {symbol}"
                if not NARRATIVE.search(text):
                    continue

                seen.add(pair_id)
                # craft alert data
                res = {
                    "chain": chain.title(),
                    "name": name or symbol,
                    "symbol": symbol,
                    "mc": f"${int(fdv):,}",
                    "lp": f"${int(liquidity_usd):,}",
                    "holders": holders,
                    "chart": p.get("url") or p.get("pairUrl"),
                    "token": (p.get("baseToken", {}) or {}).get("address", ""),
                }
                results.append(res)
    return results