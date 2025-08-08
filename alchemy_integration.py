"""
Alchemy API Integration for Enhanced Ethereum Data
Provides faster, more reliable Ethereum token data with additional metrics
"""

import requests
import os
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class AlchemyClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ALCHEMY_API_KEY")
        self.base_url = f"https://eth-mainnet.g.alchemy.com/v2/{self.api_key}"
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'AlphaSniper/1.0'
        })
    
    def get_token_metadata(self, token_address: str) -> Optional[Dict]:
        """Get ERC-20 token metadata from Alchemy"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "alchemy_getTokenMetadata",
                "params": [token_address]
            }
            
            response = self.session.post(self.base_url, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'result' in data and data['result']:
                    return data['result']
            
        except Exception as e:
            print(f"[alchemy] Error getting token metadata for {token_address}: {e}")
        
        return None
    
    def get_token_balances(self, token_address: str, page_key: str = None) -> Optional[Dict]:
        """Get token holder balances using Alchemy"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "alchemy_getTokenBalances",
                "params": [
                    "latest",
                    {
                        "contractAddresses": [token_address]
                    }
                ]
            }
            
            if page_key:
                payload["params"][1]["pageKey"] = page_key
            
            response = self.session.post(self.base_url, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'result' in data:
                    return data['result']
            
        except Exception as e:
            print(f"[alchemy] Error getting token balances for {token_address}: {e}")
        
        return None
    
    def get_transaction_receipts(self, token_address: str, from_block: str = "latest") -> Optional[List]:
        """Get recent transactions for the token"""
        try:
            # Get logs for Transfer events
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_getLogs",
                "params": [{
                    "fromBlock": hex(int(from_block, 16) - 1000) if from_block != "latest" else "0x" + hex(int(time.time()) - 3600)[2:],
                    "toBlock": "latest",
                    "address": token_address,
                    "topics": ["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"]  # Transfer event
                }]
            }
            
            response = self.session.post(self.base_url, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'result' in data:
                    return data['result']
            
        except Exception as e:
            print(f"[alchemy] Error getting transactions for {token_address}: {e}")
        
        return None
    
    def enhanced_token_analysis(self, token_address: str) -> Dict:
        """Get enhanced token analysis combining multiple Alchemy endpoints"""
        result = {
            'token_address': token_address,
            'metadata': None,
            'total_supply': 0,
            'decimals': 18,
            'holder_count': 0,
            'transaction_count': 0,
            'verified': False,
            'activity_score': 0.0,
            'risk_flags': []
        }
        
        # Get basic metadata
        metadata = self.get_token_metadata(token_address)
        if metadata:
            result['metadata'] = metadata
            result['name'] = metadata.get('name', 'Unknown')
            result['symbol'] = metadata.get('symbol', 'UNK')
            result['decimals'] = metadata.get('decimals', 18)
            result['total_supply'] = int(metadata.get('totalSupply', '0'), 16) if metadata.get('totalSupply') else 0
            
            # Basic verification check
            result['verified'] = len(result['name']) > 0 and len(result['symbol']) > 0
        
        # Get transaction activity
        transactions = self.get_transaction_receipts(token_address)
        if transactions:
            result['transaction_count'] = len(transactions)
            result['activity_score'] = min(len(transactions) / 100.0, 5.0)  # Scale 0-5
            
            # Risk analysis based on transaction patterns
            if len(transactions) < 10:
                result['risk_flags'].append('LOW_ACTIVITY')
            if result['total_supply'] == 0:
                result['risk_flags'].append('ZERO_SUPPLY')
        
        return result

# Global Alchemy client
alchemy_client = AlchemyClient()

def get_enhanced_ethereum_data(token_address: str) -> Dict:
    """Get enhanced Ethereum token data using Alchemy API"""
    if not alchemy_client.api_key:
        print("[alchemy] No API key configured, using fallback data")
        return {}
    
    return alchemy_client.enhanced_token_analysis(token_address)

def is_alchemy_available() -> bool:
    """Check if Alchemy API is available and configured"""
    return alchemy_client.api_key is not None