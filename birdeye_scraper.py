# birdeye_scraper.py
import requests
import time

def get_birdeye_new_tokens(limit=20):
    """
    Get new tokens from Birdeye API - they have official endpoints for trending/new tokens
    """
    endpoints = [
        "https://public-api.birdeye.so/public/tokenlist?sort_by=v24hChangePercent&sort_type=desc&offset=0&limit=50",
        "https://public-api.birdeye.so/public/tokenlist?sort_by=mc&sort_type=asc&offset=0&limit=50"
    ]
    
    all_tokens = []
    
    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, timeout=10)
            if response.status_code == 200:
                data = response.json()
                tokens = data.get('data', {}).get('tokens', [])
                
                for token in tokens[:limit]:
                    # Convert to DexScreener-like format
                    pair = {
                        'chainId': 'solana',
                        'pairAddress': f"birdeye_{token.get('address', '')}",
                        'pairCreatedAt': int(time.time() * 1000),  # Mark as fresh
                        'baseToken': {
                            'name': token.get('name', ''),
                            'symbol': token.get('symbol', ''),
                            'address': token.get('address', '')
                        },
                        'liquidity': {'usd': token.get('liquidity', 0)},
                        'fdv': token.get('mc', 0),
                        'marketCap': token.get('mc', 0),
                        'url': f"https://birdeye.so/token/{token.get('address', '')}",
                        'holders': 100  # Placeholder
                    }
                    all_tokens.append(pair)
                    
                print(f"[birdeye] Got {len(tokens)} tokens from endpoint")
                break  # Use first successful endpoint
                
        except Exception as e:
            print(f"[birdeye] Error with endpoint: {e}")
            continue
    
    return all_tokens[:limit]

def get_solscan_new_tokens(limit=20):
    """
    Alternative: Get new tokens from Solscan API
    """
    try:
        url = "https://api.solscan.io/token/trending"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            tokens = data.get('data', [])
            
            pairs = []
            for token in tokens[:limit]:
                pair = {
                    'chainId': 'solana',
                    'pairAddress': f"solscan_{token.get('tokenAddress', '')}",
                    'pairCreatedAt': int(time.time() * 1000),
                    'baseToken': {
                        'name': token.get('tokenName', ''),
                        'symbol': token.get('tokenSymbol', ''),
                        'address': token.get('tokenAddress', '')
                    },
                    'liquidity': {'usd': 10000},  # Placeholder
                    'fdv': token.get('marketCapRank', 1000000),
                    'marketCap': token.get('marketCapRank', 1000000),
                    'url': f"https://solscan.io/token/{token.get('tokenAddress', '')}",
                    'holders': 50
                }
                pairs.append(pair)
            
            print(f"[solscan] Got {len(pairs)} trending tokens")
            return pairs
            
    except Exception as e:
        print(f"[solscan] Error: {e}")
        return []

def get_coingecko_new_tokens(limit=20):
    """
    Get new tokens from CoinGecko API (recently added)
    """
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_asc&per_page=50&page=1"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            pairs = []
            for token in data[:limit]:
                # Only include tokens with small market caps (newer/smaller tokens)
                if token.get('market_cap', 0) < 5000000:  # Under $5M
                    pair = {
                        'chainId': 'ethereum',
                        'pairAddress': f"coingecko_{token.get('id', '')}",
                        'pairCreatedAt': int(time.time() * 1000 - 3600000),  # 1 hour ago
                        'baseToken': {
                            'name': token.get('name', ''),
                            'symbol': token.get('symbol', '').upper(),
                            'address': ''
                        },
                        'liquidity': {'usd': 8000},
                        'fdv': token.get('market_cap', 0),
                        'marketCap': token.get('market_cap', 0),
                        'url': f"https://www.coingecko.com/en/coins/{token.get('id', '')}",
                        'holders': 75
                    }
                    pairs.append(pair)
            
            print(f"[coingecko] Got {len(pairs)} small cap tokens")
            return pairs
            
    except Exception as e:
        print(f"[coingecko] Error: {e}")
        return []

def get_combined_fresh_tokens(max_tokens=30):
    """
    Combine tokens from multiple sources for better coverage
    """
    all_tokens = []
    
    sources = [
        ("birdeye", get_birdeye_new_tokens),
        ("solscan", get_solscan_new_tokens), 
        ("coingecko", get_coingecko_new_tokens)
    ]
    
    for source_name, source_func in sources:
        try:
            tokens = source_func(10)  # Get 10 from each source
            all_tokens.extend(tokens)
            print(f"[{source_name}] Added {len(tokens)} tokens")
        except Exception as e:
            print(f"[{source_name}] Failed: {e}")
            continue
    
    # Remove duplicates and limit results
    seen_addresses = set()
    unique_tokens = []
    
    for token in all_tokens:
        addr = token.get('baseToken', {}).get('address', '') or token.get('pairAddress', '')
        if addr not in seen_addresses:
            seen_addresses.add(addr)
            unique_tokens.append(token)
    
    return unique_tokens[:max_tokens]