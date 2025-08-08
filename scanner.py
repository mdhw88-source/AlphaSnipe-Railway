# scanner.py
import time, requests, os, re
from fresh_pairs_scraper import scrape_fresh_pairs, get_fresh_pairs_enhanced
from birdeye_scraper import get_combined_fresh_tokens

DEX_API = "https://api.dexscreener.com/latest/dex/search"
CHAINS = ["solana", "ethereum"]  # Temporary, will be updated to use token profiles
MIN_LP = 3000       # USD (sync with discord_bot.py)
MAX_MC = 1_500_000  # Back to original target (sync with discord_bot.py)
MAX_AGE_MIN = 60    # Fresh pairs should be within 1 hour (sync with discord_bot.py)
MIN_HOLDERS = 0     # (sync with discord_bot.py)

NARRATIVE = re.compile(r".*", re.I)  # Temporarily match all tokens for testing

def _pairs(chain):
    # Dexscreener “latest pairs” by chain
    url = f"{DEX_API}?q={chain}"
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        return r.json().get("pairs", [])[:50]  # reduced to be API-friendly
    except Exception as e:
        print("[scanner] fetch error:", e)
        return []

def pick_new_pairs():
    results = []
    total_pairs = 0
    filtered_pairs = 0
    seen = set()  # Reset for each scan to allow fresh alerts
    
    # Try multiple fresh data sources
    try:
        # First try combined alternative sources (Birdeye, Solscan, CoinGecko)
        fresh_pairs = get_combined_fresh_tokens(25)
        if fresh_pairs:
            print(f"[scanner] Using alternative sources: {len(fresh_pairs)} pairs")
            pairs_to_process = [('fresh', fresh_pairs)]
        else:
            # Fallback to DexScreener scraper
            fresh_pairs = get_fresh_pairs_enhanced()
            if fresh_pairs:
                print(f"[scanner] Using DexScreener scraper: {len(fresh_pairs)} pairs")
                pairs_to_process = [('fresh', fresh_pairs)]
            else:
                print("[scanner] All fresh sources failed, using API")
                pairs_to_process = [(chain, _pairs(chain)) for chain in CHAINS]
    except Exception as e:
        print(f"[scanner] Fresh sources failed: {e}, using API")
        pairs_to_process = [(chain, _pairs(chain)) for chain in CHAINS]
    
    for source, pairs in pairs_to_process:
        total_pairs += len(pairs)
        print(f"[scanner] {source}: fetched {len(pairs)} pairs")
        
        for p in pairs:
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

            # Debug: show first few pairs
            if filtered_pairs < 3:
                print(f"[scanner] pair: {name} {symbol}, age: {age_min}min, lp: ${liquidity_usd}, mc: ${fdv}, holders: {holders}")

            # basic filters (relaxed for testing)
            print(f"[scanner] checking {name}: age={age_min}<={MAX_AGE_MIN}? {age_min <= MAX_AGE_MIN}, lp=${liquidity_usd}>={MIN_LP}? {liquidity_usd >= MIN_LP}, mc=${fdv}<={MAX_MC}? {fdv <= MAX_MC}")
            if age_min <= MAX_AGE_MIN and liquidity_usd >= MIN_LP and fdv <= MAX_MC:
                if holders < MIN_HOLDERS:
                    print(f"[scanner] ❌ {name}: holders {holders} < {MIN_HOLDERS}")
                    continue
                text = f"{name} {symbol}"
                if not NARRATIVE.search(text):
                    print(f"[scanner] ❌ {name}: narrative filter failed")
                    continue

                seen.add(pair_id)
                filtered_pairs += 1
                print(f"[scanner] ✅ MATCH: {name} {symbol}")
                
                # craft alert data
                res = {
                    "chain": p.get("chainId", source).title(),
                    "name": name or symbol,
                    "symbol": symbol,
                    "mc": f"${int(fdv):,}",
                    "lp": f"${int(liquidity_usd):,}",
                    "holders": holders,
                    "chart": p.get("url") or p.get("pairUrl"),
                    "token": (p.get("baseToken", {}) or {}).get("address", ""),
                }
                results.append(res)
            else:
                print(f"[scanner] ❌ {name}: basic filters failed")
    
    print(f"[scanner] Summary: {total_pairs} total pairs, {filtered_pairs} passed filters, {len(results)} new alerts")
    return results