"""
Helius API Integration for Enhanced Solana Data
Provides faster, more reliable Solana token data with additional metrics
"""

import requests
import os
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class HeliusClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("HELIUS_API_KEY")
        self.base_url = f"https://mainnet.helius-rpc.com/?api-key={self.api_key}"
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'AlphaSniper/1.0'
        })
    
    def get_token_metadata(self, token_address: str) -> Optional[Dict]:
        """Get comprehensive token metadata from Helius"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": "helius-test",
                "method": "getAsset",
                "params": {
                    "id": token_address,
                    "displayOptions": {
                        "showUnverifiedCollections": True,
                        "showCollectionMetadata": True,
                        "showFungibleTokens": True
                    }
                }
            }
            
            response = self.session.post(self.base_url, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'result' in data and data['result']:
                    return data['result']
            
        except Exception as e:
            print(f"[helius] Error getting token metadata for {token_address}: {e}")
        
        return None
    
    def get_token_holders(self, token_address: str, limit: int = 1000) -> Optional[Dict]:
        """Get token holder information"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": "helius-holders",
                "method": "getTokenAccounts",
                "params": {
                    "mint": token_address,
                    "limit": limit,
                    "cursor": None
                }
            }
            
            response = self.session.post(self.base_url, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'result' in data:
                    return data['result']
            
        except Exception as e:
            print(f"[helius] Error getting holders for {token_address}: {e}")
        
        return None
    
    def get_token_transactions(self, token_address: str, limit: int = 100) -> Optional[List]:
        """Get recent token transactions for volume/activity analysis"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": "helius-txns",
                "method": "searchAssets",
                "params": {
                    "nativeAddress": token_address,
                    "tokenType": "fungible",
                    "limit": limit
                }
            }
            
            response = self.session.post(self.base_url, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'result' in data:
                    return data['result']
            
        except Exception as e:
            print(f"[helius] Error getting transactions for {token_address}: {e}")
        
        return None
    
    def enhanced_token_analysis(self, token_address: str) -> Dict:
        """Get enhanced token analysis combining multiple Helius endpoints"""
        result = {
            'token_address': token_address,
            'metadata': None,
            'holder_count': 0,
            'holder_distribution': {},
            'whale_concentration': 0.0,
            'creation_time': None,
            'verified': False,
            'liquidity_score': 0.0,
            'activity_score': 0.0,
            'risk_flags': []
        }
        
        # Get basic metadata
        metadata = self.get_token_metadata(token_address)
        if metadata:
            result['metadata'] = metadata
            result['verified'] = metadata.get('burnt', False) == False
            
            # Extract creation info if available
            if 'content' in metadata:
                content = metadata['content']
                result['name'] = content.get('metadata', {}).get('name', 'Unknown')
                result['symbol'] = content.get('metadata', {}).get('symbol', 'UNK')
        
        # Get holder analysis
        holders_data = self.get_token_holders(token_address)
        if holders_data and 'token_accounts' in holders_data:
            accounts = holders_data['token_accounts']
            result['holder_count'] = len(accounts)
            
            # Calculate holder distribution
            if accounts:
                balances = [float(acc.get('amount', 0)) for acc in accounts if acc.get('amount')]
                if balances:
                    total_supply = sum(balances)
                    balances.sort(reverse=True)
                    
                    # Top holder concentration
                    top_10_supply = sum(balances[:10]) if len(balances) >= 10 else sum(balances)
                    result['whale_concentration'] = (top_10_supply / total_supply * 100) if total_supply > 0 else 0
                    
                    # Risk flags
                    if result['whale_concentration'] > 80:
                        result['risk_flags'].append('HIGH_WHALE_CONCENTRATION')
                    if result['holder_count'] < 10:
                        result['risk_flags'].append('LOW_HOLDER_COUNT')
        
        return result

# Global Helius client
helius_client = HeliusClient()

def get_enhanced_solana_data(token_address: str) -> Dict:
    """Get enhanced Solana token data using Helius API"""
    if not helius_client.api_key:
        print("[helius] No API key configured, using fallback data")
        return {}
    
    return helius_client.enhanced_token_analysis(token_address)

def is_helius_available() -> bool:
    """Check if Helius API is available and configured"""
    return helius_client.api_key is not None