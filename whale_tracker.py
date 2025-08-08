"""
Whale Tracking System for Multi-Chain Alerts
Monitors large wallet movements on Solana and Ethereum
"""

import json
import os
from typing import Set, Dict, List
from datetime import datetime

# File paths for whale addresses
WHALES_ETH_FILE = "whales_eth.json"
WHALES_SOL_FILE = "whales_sol.json"

class WhaleTracker:
    def __init__(self):
        self.eth_whales = self._load_addresses(WHALES_ETH_FILE)
        self.sol_whales = self._load_addresses(WHALES_SOL_FILE)
    
    def _load_addresses(self, filename: str) -> Set[str]:
        """Load whale addresses from JSON file"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    return set(json.load(f))
            return set()
        except Exception as e:
            print(f"[whale_tracker] Error loading {filename}: {e}")
            return set()
    
    def _save_addresses(self, addresses: Set[str], filename: str):
        """Save whale addresses to JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump(list(addresses), f)
        except Exception as e:
            print(f"[whale_tracker] Error saving {filename}: {e}")
    
    def add_eth_whale(self, address: str) -> bool:
        """Add Ethereum whale address to tracking"""
        address = address.lower().strip()
        if address not in self.eth_whales:
            self.eth_whales.add(address)
            self._save_addresses(self.eth_whales, WHALES_ETH_FILE)
            return True
        return False
    
    def add_sol_whale(self, address: str) -> bool:
        """Add Solana whale address to tracking"""
        address = address.strip()
        if address not in self.sol_whales:
            self.sol_whales.add(address)
            self._save_addresses(self.sol_whales, WHALES_SOL_FILE)
            return True
        return False
    
    def remove_eth_whale(self, address: str) -> bool:
        """Remove Ethereum whale address from tracking"""
        address = address.lower().strip()
        if address in self.eth_whales:
            self.eth_whales.remove(address)
            self._save_addresses(self.eth_whales, WHALES_ETH_FILE)
            return True
        return False
    
    def remove_sol_whale(self, address: str) -> bool:
        """Remove Solana whale address from tracking"""
        address = address.strip()
        if address in self.sol_whales:
            self.sol_whales.remove(address)
            self._save_addresses(self.sol_whales, WHALES_SOL_FILE)
            return True
        return False
    
    def is_eth_whale(self, address: str) -> bool:
        """Check if address is tracked Ethereum whale"""
        return address.lower().strip() in self.eth_whales
    
    def is_sol_whale(self, address: str) -> bool:
        """Check if address is tracked Solana whale"""
        return address.strip() in self.sol_whales
    
    def get_eth_whales(self) -> List[str]:
        """Get list of tracked Ethereum whale addresses"""
        return list(self.eth_whales)
    
    def get_sol_whales(self) -> List[str]:
        """Get list of tracked Solana whale addresses"""
        return list(self.sol_whales)
    
    def format_whale_alert(self, chain: str, direction: str, address: str, 
                          asset: str, amount: str, tx_hash: str = None) -> str:
        """Format whale movement alert message"""
        chain_emoji = "⛽" if chain.lower() == "ethereum" else "☀️"
        direction_emoji = "🟢" if direction == "BUY" else "🔴"
        
        explorer_link = ""
        if tx_hash:
            if chain.lower() == "ethereum":
                explorer_link = f"\n🔗 [View on Etherscan](https://etherscan.io/tx/{tx_hash})"
            elif chain.lower() == "solana":
                explorer_link = f"\n🔗 [View on Solscan](https://solscan.io/tx/{tx_hash})"
        
        return (
            f"🐋 **{chain_emoji} {chain.upper()} WHALE {direction}** {direction_emoji}\n\n"
            f"**Address:** `{address[:8]}...{address[-6:]}`\n"
            f"**Asset:** {asset}\n"
            f"**Amount:** {amount}\n"
            f"**Time:** {datetime.now().strftime('%H:%M:%S UTC')}"
            f"{explorer_link}"
        )

# Global whale tracker instance
whale_tracker = WhaleTracker()

def add_whale_address(chain: str, address: str) -> bool:
    """Add whale address for tracking"""
    if chain.lower() == "ethereum":
        return whale_tracker.add_eth_whale(address)
    elif chain.lower() == "solana":
        return whale_tracker.add_sol_whale(address)
    return False

def remove_whale_address(chain: str, address: str) -> bool:
    """Remove whale address from tracking"""
    if chain.lower() == "ethereum":
        return whale_tracker.remove_eth_whale(address)
    elif chain.lower() == "solana":
        return whale_tracker.remove_sol_whale(address)
    return False

def is_tracked_whale(chain: str, address: str) -> bool:
    """Check if address is a tracked whale"""
    if chain.lower() == "ethereum":
        return whale_tracker.is_eth_whale(address)
    elif chain.lower() == "solana":
        return whale_tracker.is_sol_whale(address)
    return False