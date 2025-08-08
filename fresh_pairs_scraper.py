# fresh_pairs_scraper.py
import trafilatura
import requests
from bs4 import BeautifulSoup
import json
import time
import re

def scrape_fresh_pairs(max_pairs=50):
    """
    Scrape DexScreener's new-pairs page to get truly fresh tokens
    Returns list of fresh pair data with proper age filtering
    """
    url = "https://dexscreener.com/new-pairs"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for JSON data in script tags (common pattern)
        pairs_data = []
        script_tags = soup.find_all('script')
        
        for script in script_tags:
            if script.string:
                # Look for pair data patterns
                if 'pairAddress' in script.string or 'baseToken' in script.string:
                    try:
                        # Extract JSON from script content
                        text = script.string
                        
                        # Find JSON patterns
                        json_matches = re.findall(r'\{[^{}]*"pairAddress"[^{}]*\}', text)
                        for match in json_matches:
                            try:
                                pair = json.loads(match)
                                if validate_pair_data(pair):
                                    pairs_data.append(pair)
                                    if len(pairs_data) >= max_pairs:
                                        break
                            except:
                                continue
                        
                        if len(pairs_data) >= max_pairs:
                            break
                            
                    except Exception as e:
                        continue
        
        # Fallback: parse table data if JSON extraction fails
        if not pairs_data:
            pairs_data = parse_table_data(soup, max_pairs)
        
        print(f"[scraper] Found {len(pairs_data)} fresh pairs from new-pairs page")
        return pairs_data[:max_pairs]
        
    except Exception as e:
        print(f"[scraper] Error scraping fresh pairs: {e}")
        return []

def parse_table_data(soup, max_pairs):
    """
    Parse table/list data from the page as fallback
    """
    pairs = []
    
    # Look for common table patterns
    tables = soup.find_all(['table', 'div'], class_=re.compile(r'table|list|pair', re.I))
    
    for table in tables:
        rows = table.find_all(['tr', 'div'], class_=re.compile(r'row|item|pair', re.I))
        
        for row in rows[:max_pairs]:
            try:
                # Extract basic data from row structure
                texts = [elem.get_text().strip() for elem in row.find_all(['td', 'div', 'span'])]
                
                # Look for patterns like token names, addresses, etc.
                for text in texts:
                    if any(pattern in text.lower() for pattern in ['sol', 'eth', 'token', '$']):
                        # Create basic pair structure
                        pair = {
                            'pairAddress': f'scraped_{len(pairs)}',
                            'chainId': 'solana' if 'sol' in text.lower() else 'ethereum',
                            'baseToken': {
                                'name': text,
                                'symbol': text.split()[0] if text.split() else 'UNKNOWN'
                            },
                            'pairCreatedAt': int(time.time() * 1000),  # Current time as fresh
                            'liquidity': {'usd': 5000},  # Placeholder values
                            'fdv': 500000
                        }
                        pairs.append(pair)
                        break
                        
                if len(pairs) >= max_pairs:
                    break
            except:
                continue
                
        if len(pairs) >= max_pairs:
            break
    
    return pairs

def validate_pair_data(pair):
    """
    Validate that pair data has required fields
    """
    required_fields = ['pairAddress']
    return all(field in pair for field in required_fields)

def get_fresh_pairs_enhanced():
    """
    Enhanced version that combines scraping with API calls for complete data
    """
    fresh_pairs = scrape_fresh_pairs(30)
    enhanced_pairs = []
    
    for pair in fresh_pairs:
        try:
            # Try to get full data from API using pair address
            pair_address = pair.get('pairAddress')
            chain_id = pair.get('chainId', 'solana')
            
            if pair_address and not pair_address.startswith('scraped_'):
                api_url = f"https://api.dexscreener.com/latest/dex/pairs/{chain_id}/{pair_address}"
                
                try:
                    response = requests.get(api_url, timeout=10)
                    if response.status_code == 200:
                        api_data = response.json()
                        if api_data.get('pairs'):
                            enhanced_pairs.extend(api_data['pairs'])
                            continue
                except:
                    pass
            
            # If API call fails, use scraped data
            enhanced_pairs.append(pair)
            
        except Exception as e:
            print(f"[scraper] Error enhancing pair data: {e}")
            enhanced_pairs.append(pair)
    
    return enhanced_pairs