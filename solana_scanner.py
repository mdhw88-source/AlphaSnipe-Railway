# solana_scanner.py
import requests
import time
import json

def get_pump_fun_tokens(limit=20):
    """
    Get fresh tokens from Pump.fun using alternative approach
    """
    try:
        # Use direct DexScreener search for pump.fun pairs
        url = "https://api.dexscreener.com/latest/dex/search?q=pump.fun"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            pairs = data.get('pairs', [])
            tokens = []
            
            for pair in pairs[:limit]:
                if pair.get('chainId') == 'solana':
                    # Calculate age in minutes
                    created_timestamp = pair.get('pairCreatedAt', 0)
                    current_time = time.time() * 1000
                    age_min = max(0, int((current_time - created_timestamp) / 60000))
                    
                    token_data = {
                        'chainId': 'solana',
                        'pairAddress': pair.get('pairAddress', ''),
                        'pairCreatedAt': created_timestamp,
                        'baseToken': pair.get('baseToken', {}),
                        'liquidity': pair.get('liquidity', {}),
                        'fdv': pair.get('fdv', 0),
                        'marketCap': pair.get('marketCap', 0),
                        'url': pair.get('url', ''),
                        'holders': 100,  # Estimate
                        'age_minutes': age_min,
                        'runner_score': calculate_runner_score_dex(pair)
                    }
                    tokens.append(token_data)
            
            print(f"[pump.fun] Got {len(tokens)} Solana tokens")
            return tokens
            
    except Exception as e:
        print(f"[pump.fun] Error: {e}")
        return []

def get_birdeye_trending_solana(limit=15):
    """
    Get trending Solana tokens using free endpoints
    """
    try:
        # Try Raydium pools for Solana tokens
        url = "https://api.dexscreener.com/latest/dex/search?q=raydium"
        
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            pairs = data.get('pairs', [])
            
            solana_pairs = []
            for pair in pairs[:limit]:
                if pair.get('chainId') == 'solana':
                    mc = pair.get('fdv', 0) or pair.get('marketCap', 0)
                    if mc < 5000000:  # Under $5M
                        current_time = time.time() * 1000
                        created_at = pair.get('pairCreatedAt', current_time - 3600000)
                        age_min = (current_time - created_at) / 60000
                        
                        pair['age_minutes'] = age_min
                        pair['runner_score'] = calculate_runner_score_dex(pair)
                        solana_pairs.append(pair)
            
            print(f"[raydium] Got {len(solana_pairs)} Solana pairs")
            return solana_pairs
            
    except Exception as e:
        print(f"[birdeye] Solana trending error: {e}")
        return []

def get_dexscreener_new_solana_pairs(limit=15):
    """
    Get newest Solana pairs from DexScreener trending
    """
    try:
        # Search for trending Solana tokens
        url = "https://api.dexscreener.com/latest/dex/search?q=solana"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            pairs = data.get('pairs', [])
            
            # Filter for Solana pairs and calculate scores
            solana_pairs = []
            current_time = time.time() * 1000
            
            for pair in pairs:
                if pair.get('chainId') == 'solana':
                    created_at = pair.get('pairCreatedAt', 0)
                    age_min = (current_time - created_at) / 60000 if created_at else 999999
                    
                    # Focus on tokens with good runner characteristics
                    mc = pair.get('fdv', 0) or pair.get('marketCap', 0)
                    liquidity = pair.get('liquidity', {}).get('usd', 0)
                    
                    if mc < 10000000 and liquidity > 5000:  # Under $10M MC, decent liquidity
                        pair['age_minutes'] = age_min
                        pair['runner_score'] = calculate_runner_score_dex(pair)
                        solana_pairs.append(pair)
            
            # Sort by runner score
            solana_pairs.sort(key=lambda x: x.get('runner_score', 0), reverse=True)
            
            print(f"[dexscreener] Got {len(solana_pairs[:limit])} Solana pairs")
            return solana_pairs[:limit]
            
    except Exception as e:
        print(f"[dexscreener] Solana error: {e}")
        return []

def calculate_runner_score(token):
    """
    Calculate potential runner score for Pump.fun tokens
    """
    score = 0
    
    # Market cap range (sweet spot for runners)
    mc = token.get('usd_market_cap', 0)
    if 10000 < mc < 100000:
        score += 3
    elif 100000 < mc < 500000:
        score += 2
    elif mc < 10000:
        score += 1
    
    # Activity indicators
    replies = token.get('reply_count', 0)
    if replies > 50:
        score += 2
    elif replies > 20:
        score += 1
    
    # Time factor (newer is better for catching runners early)
    created_timestamp = token.get('created_timestamp', 0)
    age_hours = (time.time() - created_timestamp / 1000) / 3600
    if age_hours < 1:
        score += 3
    elif age_hours < 6:
        score += 2
    elif age_hours < 24:
        score += 1
    
    return score

def calculate_runner_score_birdeye(token):
    """
    Calculate runner score for Birdeye tokens
    """
    score = 0
    
    # Price change indicators
    change_24h = token.get('v24hChangePercent', 0)
    if change_24h > 100:  # 100%+ gain
        score += 3
    elif change_24h > 50:
        score += 2
    elif change_24h > 20:
        score += 1
    
    # Volume to market cap ratio
    volume = token.get('v24hUSD', 0)
    mc = token.get('mc', 1)
    if volume / mc > 2:  # High volume relative to MC
        score += 2
    elif volume / mc > 1:
        score += 1
    
    return score

def calculate_runner_score_dex(pair):
    """
    Enhanced runner score with momentum, volume, and timing analysis
    """
    score = 0
    
    try:
        # Core metrics
        fdv = float(pair.get('fdv', 0) or pair.get('marketCap', 0))
        liquidity_usd = float(pair.get('liquidity', {}).get('usd', 0))
        volume_24h = float(pair.get('volume', {}).get('h24', 0))
        volume_6h = float(pair.get('volume', {}).get('h6', 0))
        
        # Price change analysis (enhanced)
        price_change = pair.get('priceChange', {})
        change_5m = float(price_change.get('m5', 0) or 0)
        change_1h = float(price_change.get('h1', 0) or 0)
        change_6h = float(price_change.get('h6', 0) or 0)
        change_24h = float(price_change.get('h24', 0) or 0)
        
        # Age calculation
        created_timestamp = pair.get('pairCreatedAt', 0)
        current_time = time.time() * 1000
        age_hours = (current_time - created_timestamp) / 3600000 if created_timestamp else 999
        
        # 1. Market Cap Scoring (optimized for runners)
        if 5000 <= fdv <= 300000:  # $5K-$300K prime runner zone
            score += 2.5
        elif 300000 < fdv <= 1000000:  # $300K-$1M good potential
            score += 2
        elif 1000000 < fdv <= 3000000:  # $1M-$3M still viable
            score += 1
        
        # 2. Liquidity Scoring (enhanced standards)
        if liquidity_usd >= 50000:  # $50K+ excellent liquidity
            score += 2
        elif liquidity_usd >= 20000:  # $20K+ good liquidity
            score += 1.5
        elif liquidity_usd >= 5000:  # $5K+ decent liquidity
            score += 1
        
        # 3. Fresh Token Age Bonus (critical for early detection)
        if age_hours <= 0.25:  # 15 minutes - ULTRA FRESH
            score += 2.5
        elif age_hours <= 1:  # 1 hour - VERY FRESH
            score += 2
        elif age_hours <= 6:  # 6 hours - FRESH
            score += 1.5
        elif age_hours <= 24:  # 24 hours - Recent
            score += 1
        
        # 4. Momentum Analysis (price action)
        momentum_score = 0
        if change_5m > 10:  # 10%+ in 5 minutes
            momentum_score += 1.5
        elif change_5m > 5:  # 5%+ in 5 minutes
            momentum_score += 1
        
        if change_1h > 25:  # 25%+ in 1 hour
            momentum_score += 1.5
        elif change_1h > 10:  # 10%+ in 1 hour
            momentum_score += 1
        
        if change_6h > 50:  # 50%+ in 6 hours
            momentum_score += 1
        elif change_6h > 20:  # 20%+ in 6 hours
            momentum_score += 0.5
        
        score += min(momentum_score, 2)  # Cap momentum bonus
        
        # 5. Volume Analysis
        if volume_24h > 0 and liquidity_usd > 0:
            vol_liq_ratio = volume_24h / liquidity_usd
            if vol_liq_ratio > 3:  # Very high activity
                score += 1.5
            elif vol_liq_ratio > 1:  # Good activity
                score += 1
            elif vol_liq_ratio > 0.3:  # Decent activity
                score += 0.5
        
        # 6. Volume Acceleration (6h trend vs 24h average)
        if volume_6h > 0 and volume_24h > 0:
            vol_acceleration = (volume_6h * 4) / volume_24h
            if vol_acceleration > 2:  # Accelerating volume
                score += 1
            elif vol_acceleration > 1.3:  # Growing volume
                score += 0.5
        
        # 7. Transaction Activity
        txns = pair.get('txns', {})
        if isinstance(txns, dict):
            h1_data = txns.get('h1', {})
            h6_data = txns.get('h6', {})
            
            h1_buys = h1_data.get('buys', 0) or 0
            h1_sells = h1_data.get('sells', 0) or 0
            
            # Buy pressure analysis
            if h1_buys > 0 and h1_sells > 0:
                buy_ratio = h1_buys / (h1_buys + h1_sells)
                if buy_ratio > 0.7:  # Strong buy pressure
                    score += 1
                elif buy_ratio > 0.6:  # Good buy pressure
                    score += 0.5
            
            # Transaction volume
            if h1_buys > 150:
                score += 1.5
            elif h1_buys > 75:
                score += 1
            elif h1_buys > 25:
                score += 0.5
        
        # Cap at 5
        score = min(5, score)
        
    except Exception as e:
        print(f"[enhanced_runner_score] Error: {e}")
        score = 0
    
    return round(score, 1)

def get_runner_candidates(max_tokens=25):
    """
    Enhanced multi-source runner detection with increased coverage
    """
    all_tokens = []
    
    sources = [
        ("pump.fun", get_pump_fun_tokens, 15),  # Increased for more early detection
        ("birdeye", get_birdeye_trending_solana, 12),  # More trending tokens
        ("dexscreener", get_dexscreener_new_solana_pairs, 10)  # More fresh pairs
    ]
    
    for source_name, source_func, limit in sources:
        try:
            tokens = source_func(limit)
            for token in tokens:
                token['source'] = source_name
            all_tokens.extend(tokens)
            print(f"[{source_name}] Added {len(tokens)} tokens")
        except Exception as e:
            print(f"[{source_name}] Failed: {e}")
            continue
    
    # Sort by runner score and remove duplicates
    seen_addresses = set()
    unique_tokens = []
    
    # Sort by runner score first
    all_tokens.sort(key=lambda x: x.get('runner_score', 0), reverse=True)
    
    for token in all_tokens:
        addr = token.get('baseToken', {}).get('address', '') or token.get('pairAddress', '')
        if addr not in seen_addresses and addr:
            seen_addresses.add(addr)
            unique_tokens.append(token)
    
    print(f"[runner_scanner] Found {len(unique_tokens)} unique runner candidates")
    return unique_tokens[:max_tokens]