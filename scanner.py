# scanner.py
import time, requests, os, re
from fresh_pairs_scraper import scrape_fresh_pairs, get_fresh_pairs_enhanced
from birdeye_scraper import get_combined_fresh_tokens
from solana_scanner import get_runner_candidates
from ethereum_scanner import get_ethereum_runner_candidates

DEX_API = "https://api.dexscreener.com/latest/dex/search"
CHAINS = ["solana", "ethereum"]  # Temporary, will be updated to use token profiles
MIN_LP = 2000       # USD - Lowered to catch earlier opportunities
MAX_MC = 2_500_000  # Increased for potential runners (sync with discord_bot.py)
MAX_AGE_MIN = 120   # Extended to 2 hours for early detection (sync with discord_bot.py)
MIN_HOLDERS = 0     # (sync with discord_bot.py)

NARRATIVE = re.compile(r".*", re.I)  # Temporarily match all tokens for testing

# Global storage for already seen tokens (persists across scans)
sent_tokens = set()
last_reset = time.time()

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
    global sent_tokens, last_reset
    results = []
    total_pairs = 0
    filtered_pairs = 0
    seen = set()  # Prevent duplicates within this single scan
    
    # Reset sent tokens every hour to allow fresh alerts
    current_time = time.time()
    if current_time - last_reset > 3600:  # 1 hour
        sent_tokens.clear()
        last_reset = current_time
        print("[scanner] Cleared sent tokens cache (1 hour passed)")
    
    # Try multi-chain runner candidates (Solana + Ethereum)
    try:
        all_candidates = []
        
        # Get Solana runner candidates
        sol_candidates = get_runner_candidates(15)
        if sol_candidates:
            all_candidates.extend(sol_candidates)
            print(f"[scanner] Got {len(sol_candidates)} Solana runner candidates")
        
        # Get Ethereum runner candidates
        eth_candidates = get_ethereum_runner_candidates(15)
        if eth_candidates:
            all_candidates.extend(eth_candidates)
            print(f"[scanner] Got {len(eth_candidates)} Ethereum runner candidates")
        
        if all_candidates:
            print(f"[scanner] Using multi-chain runner scanner: {len(all_candidates)} total candidates")
            pairs_to_process = [('multi_chain_runners', all_candidates)]
        else:
            # Fallback to combined alternative sources
            fresh_pairs = get_combined_fresh_tokens(15)
            if fresh_pairs:
                print(f"[scanner] Using alternative sources: {len(fresh_pairs)} pairs")
                pairs_to_process = [('fresh', fresh_pairs)]
            else:
                print("[scanner] All fresh sources failed, using API")
                pairs_to_process = [(chain, _pairs(chain)) for chain in CHAINS]
    except Exception as e:
        print(f"[scanner] Multi-chain runner scanner failed: {e}, trying alternatives")
        try:
            fresh_pairs = get_combined_fresh_tokens(15)
            if fresh_pairs:
                pairs_to_process = [('fresh', fresh_pairs)]
            else:
                pairs_to_process = [(chain, _pairs(chain)) for chain in CHAINS]
        except:
            pairs_to_process = [(chain, _pairs(chain)) for chain in CHAINS]
    
    for source, pairs in pairs_to_process:
        total_pairs += len(pairs)
        print(f"[scanner] {source}: fetched {len(pairs)} pairs")
        
        for p in pairs:
            pair_addr = p.get("pairAddress", "")
            pair_id = pair_addr or p.get("pairCreatedAt")
            if not pair_id or pair_id in seen:
                continue
            
            # Create unique identifier for this token
            token_name = (p.get("baseToken", {}) or {}).get("name", "")
            token_symbol = (p.get("baseToken", {}) or {}).get("symbol", "")
            token_id = f"{token_name}_{token_symbol}".lower().replace(" ", "_")
            
            # Skip if we've already sent this token recently
            if token_id in sent_tokens:
                continue

            age_min = max(0, int((time.time()*1000 - (p.get("pairCreatedAt") or 0)) / 60000))
            liquidity_usd = float(p.get("liquidity", {}).get("usd", 0))
            fdv = float(p.get("fdv") or 0)  # proxy for MC
            holders = int(p.get("holders", 0)) if isinstance(p.get("holders", 0), (int,float)) else 0
            base_symbol = (p.get("baseToken", {}) or {}).get("symbol", "")
            name = (p.get("baseToken", {}) or {}).get("name", "")
            symbol = base_symbol or name

            # Runner score bonus for prioritization
            runner_score = p.get('runner_score', 0)
            
            # Debug: show first few pairs with runner scores
            if filtered_pairs < 3:
                print(f"[scanner] pair: {name} {symbol}, age: {age_min}min, lp: ${liquidity_usd}, mc: ${fdv}, runner_score: {runner_score}")

            # Chain-specific filtering for different networks
            chain_id = p.get('chainId', '').lower()
            
            # Enhanced filters for runner potential with chain-specific adjustments
            if chain_id == 'ethereum':
                # Ethereum has higher costs, so different thresholds
                base_age_limit = 180  # 3 hours for ETH (faster initial moves)
                base_lp_limit = 10000  # $10K minimum liquidity for ETH
                base_mc_limit = 10000000  # $10M max market cap for ETH
                
                if runner_score >= 3:
                    age_limit = 1440  # 24 hours for high-score ETH tokens
                    lp_limit = 5000  # Lower liquidity for runners
                    mc_limit = 20000000  # Higher market cap for ETH runners
                else:
                    age_limit = base_age_limit
                    lp_limit = base_lp_limit
                    mc_limit = base_mc_limit
            else:
                # Solana (default) - original thresholds
                if runner_score >= 3:
                    age_limit = 2880  # 48 hours for high-score tokens
                    lp_limit = 1000  # Lower liquidity requirement
                    mc_limit = 5000000  # Higher market cap allowed for runners
                else:
                    age_limit = MAX_AGE_MIN
                    lp_limit = MIN_LP
                    mc_limit = MAX_MC
            
            age_ok = age_min <= age_limit
            lp_ok = liquidity_usd >= lp_limit
            mc_ok = fdv <= mc_limit
            
            print(f"[scanner] checking {name}: age={age_min}≤{age_limit}? {age_ok}, lp=${liquidity_usd}≥{lp_limit}? {lp_ok}, mc=${fdv}≤{mc_limit}? {mc_ok}, score={runner_score}")
            
            if age_ok and lp_ok and mc_ok:
                if holders < MIN_HOLDERS:
                    print(f"[scanner] ❌ {name}: holders {holders} < {MIN_HOLDERS}")
                    continue
                text = f"{name} {symbol}"
                if not NARRATIVE.search(text):
                    print(f"[scanner] ❌ {name}: narrative filter failed")
                    continue

                seen.add(pair_id)
                sent_tokens.add(token_id)  # Mark as sent
                filtered_pairs += 1
                print(f"[scanner] ✅ MATCH: {name} {symbol}")
                
                # craft enhanced alert data with detailed information
                base_token = p.get("baseToken", {}) or {}
                token_address = base_token.get("address", "") or pair_addr
                
                res = {
                    "chain": p.get("chainId", source).title(),
                    "name": name or symbol,
                    "symbol": symbol,
                    "mc": f"${int(fdv):,}",
                    "lp": f"${int(liquidity_usd):,}",
                    "holders": holders,
                    "chart": p.get("url") or p.get("pairUrl"),
                    "token": token_address,
                    "pair_address": pair_addr,
                    "age_minutes": age_min,
                    "runner_score": runner_score,
                    "market_cap": fdv,
                    "liquidity": liquidity_usd,
                    "price_change_1h": p.get("priceChange", {}).get("h1", 0) if isinstance(p.get("priceChange"), dict) else 0,
                    "price_change_24h": p.get("priceChange", {}).get("h24", 0) if isinstance(p.get("priceChange"), dict) else 0,
                    "volume_24h": p.get("volume", {}).get("h24", 0) if isinstance(p.get("volume"), dict) else 0,
                    "dex_url": p.get("url", ""),
                    "source": p.get("source", source),
                }
                results.append(res)
            else:
                print(f"[scanner] ❌ {name}: basic filters failed")
    
    print(f"[scanner] Summary: {total_pairs} total pairs, {filtered_pairs} passed filters, {len(results)} new alerts")
    return results