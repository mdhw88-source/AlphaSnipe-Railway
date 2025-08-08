# ethereum_scanner.py
import requests
import time
import json

def get_ethereum_runner_candidates(limit=20):
    """
    Get fresh Ethereum tokens with runner potential from multiple sources
    """
    candidates = []
    
    # Source 1: Uniswap V3 pairs from DexScreener
    uniswap_tokens = get_uniswap_tokens(limit//2)
    candidates.extend(uniswap_tokens)
    
    # Source 2: General Ethereum search
    eth_tokens = get_ethereum_dex_tokens(limit//2)
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
    Calculate runner potential score (0-5) for Ethereum tokens
    Ethereum has different characteristics than Solana due to gas costs
    """
    score = 0
    
    try:
        # Get token metrics
        fdv = float(token_data.get('fdv', 0) or token_data.get('marketCap', 0))
        liquidity_usd = float(token_data.get('liquidity', {}).get('usd', 0))
        age_min = token_data.get('age_minutes', 0)
        volume_24h = float(token_data.get('volume', {}).get('h24', 0))
        
        # Market cap scoring (adjusted for ETH)
        if 50000 <= fdv <= 2000000:  # $50K-$2M sweet spot for ETH runners
            score += 2
        elif 2000000 < fdv <= 5000000:  # $2M-$5M still good
            score += 1
        elif fdv < 50000:  # Too small, might be rugged
            score += 0
        
        # Liquidity scoring (higher requirements for ETH)
        if liquidity_usd >= 20000:  # $20K+ liquidity is strong for ETH
            score += 2
        elif liquidity_usd >= 10000:  # $10K+ is decent
            score += 1
        
        # Age scoring (ETH tokens tend to have longer lifecycles)
        if age_min <= 180:  # 3 hours - very fresh
            score += 1
        elif age_min <= 1440:  # 24 hours - still fresh
            score += 0.5
        
        # Volume/Liquidity ratio (activity indicator)
        if liquidity_usd > 0:
            vol_liq_ratio = volume_24h / liquidity_usd
            if vol_liq_ratio > 0.5:  # High activity
                score += 1
        
        # Cap at 5
        score = min(5, score)
        
    except Exception as e:
        print(f"[eth_runner_score] Error calculating score: {e}")
        score = 0
    
    return int(score)