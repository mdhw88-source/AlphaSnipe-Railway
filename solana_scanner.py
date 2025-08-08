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
    Calculate runner score for DexScreener pairs
    """
    score = 0
    
    # Price change
    price_change = pair.get('priceChange', {})
    change_1h = price_change.get('h1', 0) or 0
    change_24h = price_change.get('h24', 0) or 0
    
    if change_1h > 50:
        score += 3
    elif change_1h > 20:
        score += 2
    elif change_1h > 10:
        score += 1
    
    # Liquidity growth indicates interest
    liquidity = pair.get('liquidity', {}).get('usd', 0)
    if 50000 < liquidity < 200000:  # Sweet spot
        score += 2
    elif liquidity > 20000:
        score += 1
    
    # Transaction activity
    txns = pair.get('txns', {})
    if isinstance(txns, dict):
        h1_buys = txns.get('h1', {}).get('buys', 0) or 0
        if h1_buys > 100:
            score += 2
        elif h1_buys > 50:
            score += 1
    
    return score

def get_runner_candidates(max_tokens=20):
    """
    Get the best runner candidates from all Solana sources
    """
    all_tokens = []
    
    sources = [
        ("pump.fun", get_pump_fun_tokens, 10),
        ("birdeye", get_birdeye_trending_solana, 8),
        ("dexscreener", get_dexscreener_new_solana_pairs, 7)
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