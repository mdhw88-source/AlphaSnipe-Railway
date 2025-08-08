# ethereum_scanner.py
import requests
import time
import json

def get_ethereum_runner_candidates(limit=25):
    """
    Enhanced Ethereum runner detection with broader coverage
    """
    candidates = []
    
    # Source 1: Uniswap V3 pairs from DexScreener (increased coverage)
    uniswap_tokens = get_uniswap_tokens(15)  # More Uniswap tokens
    candidates.extend(uniswap_tokens)
    
    # Source 2: General Ethereum search (expanded)
    eth_tokens = get_ethereum_dex_tokens(12)  # More general ETH tokens
    candidates.extend(eth_tokens)
    
    # Remove duplicates and add runner scoring
    unique_candidates = {}
    for token in candidates:
        token_addr = token.get('baseToken', {}).get('address', '')
        if token_addr and token_addr not in unique_candidates:
            token['runner_score'] = calculate_eth_runner_score(token)
            unique_candidates[token_addr] = token
    
    final_candidates = list(unique_candidates.values())
    print(f"[eth_runner_scanner] Found {len(final_candidates)} unique ETH runner candidates")
    return final_candidates

def get_uniswap_tokens(limit=10):
    """
    Get fresh Uniswap V3 tokens
    """
    try:
        url = "https://api.dexscreener.com/latest/dex/search?q=uniswap"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            pairs = data.get('pairs', [])
            tokens = []
            
            for pair in pairs[:limit]:
                if pair.get('chainId') == 'ethereum':
                    # Calculate age in minutes
                    created_timestamp = pair.get('pairCreatedAt', 0)
                    current_time = time.time() * 1000
                    age_min = max(0, int((current_time - created_timestamp) / 60000))
                    
                    token_data = {
                        'chainId': 'ethereum',
                        'pairAddress': pair.get('pairAddress', ''),
                        'pairCreatedAt': created_timestamp,
                        'baseToken': pair.get('baseToken', {}),
                        'liquidity': pair.get('liquidity', {}),
                        'fdv': pair.get('fdv', 0),
                        'marketCap': pair.get('marketCap', 0),
                        'url': pair.get('url', ''),
                        'priceChange': pair.get('priceChange', {}),
                        'volume': pair.get('volume', {}),
                        'holders': 150,  # Estimate for ETH
                        'age_minutes': age_min,
                        'source': 'uniswap'
                    }
                    tokens.append(token_data)
            
            print(f"[uniswap] Got {len(tokens)} Ethereum tokens")
            return tokens
            
    except Exception as e:
        print(f"[uniswap] Error: {e}")
        return []

def get_ethereum_dex_tokens(limit=10):
    """
    Get fresh Ethereum tokens from general search
    """
    try:
        url = "https://api.dexscreener.com/latest/dex/search?q=ethereum"
        
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            pairs = data.get('pairs', [])
            
            eth_pairs = []
            for pair in pairs[:limit]:
                if pair.get('chainId') == 'ethereum':
                    mc = pair.get('fdv', 0) or pair.get('marketCap', 0)
                    if mc < 10000000:  # Under $10M for ETH (higher than Solana due to gas costs)
                        current_time = time.time() * 1000
                        created_at = pair.get('pairCreatedAt', current_time - 3600000)
                        age_min = (current_time - created_at) / 60000
                        
                        pair['age_minutes'] = age_min
                        pair['source'] = 'ethereum_dex'
                        pair['holders'] = 200  # Higher estimate for ETH
                        eth_pairs.append(pair)
            
            print(f"[ethereum] Added {len(eth_pairs)} tokens")
            return eth_pairs
            
    except Exception as e:
        print(f"[ethereum] Error: {e}")
        return []

def calculate_eth_runner_score(token_data):
    """
    Enhanced Ethereum runner scoring with momentum and gas efficiency analysis
    """
    score = 0
    
    try:
        # Get token metrics
        fdv = float(token_data.get('fdv', 0) or token_data.get('marketCap', 0))
        liquidity_usd = float(token_data.get('liquidity', {}).get('usd', 0))
        age_min = token_data.get('age_minutes', 0)
        volume_24h = float(token_data.get('volume', {}).get('h24', 0))
        volume_6h = float(token_data.get('volume', {}).get('h6', 0))
        
        # Price change analysis for ETH
        price_change = token_data.get('priceChange', {})
        change_5m = float(price_change.get('m5', 0) or 0)
        change_1h = float(price_change.get('h1', 0) or 0)
        change_6h = float(price_change.get('h6', 0) or 0)
        change_24h = float(price_change.get('h24', 0) or 0)
        
        # 1. Market Cap Scoring (adjusted for ETH gas costs)
        if 25000 <= fdv <= 1000000:  # $25K-$1M prime ETH runner zone
            score += 2.5
        elif 1000000 < fdv <= 3000000:  # $1M-$3M good potential
            score += 2
        elif 3000000 < fdv <= 8000000:  # $3M-$8M still viable for ETH
            score += 1
        
        # 2. Enhanced Liquidity Scoring (ETH requires higher liquidity)
        if liquidity_usd >= 100000:  # $100K+ excellent for ETH
            score += 2.5
        elif liquidity_usd >= 50000:  # $50K+ very good
            score += 2
        elif liquidity_usd >= 20000:  # $20K+ decent
            score += 1.5
        elif liquidity_usd >= 10000:  # $10K+ minimum viable
            score += 1
        
        # 3. Age Scoring (ETH tokens need more time due to gas costs)
        age_hours = age_min / 60
        if age_hours <= 0.5:  # 30 minutes - ULTRA FRESH
            score += 2
        elif age_hours <= 2:  # 2 hours - VERY FRESH
            score += 1.5
        elif age_hours <= 8:  # 8 hours - FRESH
            score += 1.2
        elif age_hours <= 24:  # 24 hours - Recent
            score += 0.8
        elif age_hours <= 72:  # 72 hours - Still relevant for ETH
            score += 0.3
        
        # 4. Momentum Analysis (ETH-specific thresholds)
        momentum_score = 0
        if change_5m > 8:  # 8%+ in 5 minutes (conservative for ETH)
            momentum_score += 1.5
        elif change_5m > 3:  # 3%+ in 5 minutes
            momentum_score += 1
        
        if change_1h > 20:  # 20%+ in 1 hour
            momentum_score += 1.5
        elif change_1h > 8:  # 8%+ in 1 hour
            momentum_score += 1
        
        if change_6h > 40:  # 40%+ in 6 hours
            momentum_score += 1
        elif change_6h > 15:  # 15%+ in 6 hours
            momentum_score += 0.5
        
        score += min(momentum_score, 2)
        
        # 5. Volume Analysis (ETH-specific)
        if volume_24h > 0 and liquidity_usd > 0:
            vol_liq_ratio = volume_24h / liquidity_usd
            if vol_liq_ratio > 1.5:  # High activity for ETH
                score += 1.5
            elif vol_liq_ratio > 0.8:  # Good activity
                score += 1
            elif vol_liq_ratio > 0.3:  # Decent activity
                score += 0.5
        
        # 6. Volume Acceleration
        if volume_6h > 0 and volume_24h > 0:
            vol_acceleration = (volume_6h * 4) / volume_24h
            if vol_acceleration > 1.8:  # Accelerating
                score += 1
            elif vol_acceleration > 1.2:  # Growing
                score += 0.5
        
        # 7. ETH-specific: Higher volume threshold bonus
        if volume_24h > 100000:  # $100K+ daily volume is significant for ETH
            score += 0.5
        elif volume_24h > 500000:  # $500K+ is very strong
            score += 1
        
        # 8. Transaction activity (if available)
        txns = token_data.get('txns', {})
        if isinstance(txns, dict):
            h1_data = txns.get('h1', {})
            h1_buys = h1_data.get('buys', 0) or 0
            h1_sells = h1_data.get('sells', 0) or 0
            
            # Lower transaction thresholds for ETH due to gas costs
            if h1_buys > 50:  # 50+ buys in 1h is good for ETH
                score += 1
            elif h1_buys > 20:  # 20+ buys is decent
                score += 0.5
            
            # Buy pressure
            if h1_buys > 0 and h1_sells > 0:
                buy_ratio = h1_buys / (h1_buys + h1_sells)
                if buy_ratio > 0.65:  # Strong buy pressure
                    score += 0.8
                elif buy_ratio > 0.55:  # Good buy pressure
                    score += 0.4
        
        # Cap at 5
        score = min(5, score)
        
    except Exception as e:
        print(f"[eth_enhanced_runner_score] Error: {e}")
        score = 0
    
    return round(score, 1)