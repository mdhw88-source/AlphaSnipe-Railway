"""
Paper Trading System for Alpha Sniper Bot
Tracks positions, P/L, and trading performance on runner alerts
"""

import time
import json
import requests
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import os

@dataclass
class Position:
    token_address: str
    token_symbol: str
    chain: str
    entry_price: float
    size_usd: float
    entry_time: datetime
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    pnl_usd: Optional[float] = None
    pnl_percent: Optional[float] = None
    status: str = "OPEN"  # OPEN, CLOSED

class PaperTradingEngine:
    def __init__(self, storage_file="paper_trades.json"):
        self.storage_file = storage_file
        self.positions: Dict[str, Position] = {}
        self.closed_positions: List[Position] = []
        self.load_positions()
    
    def load_positions(self):
        """Load positions from storage file"""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    
                # Load open positions
                for pos_data in data.get('open_positions', []):
                    pos_data['entry_time'] = datetime.fromisoformat(pos_data['entry_time'])
                    if pos_data.get('exit_time'):
                        pos_data['exit_time'] = datetime.fromisoformat(pos_data['exit_time'])
                    position = Position(**pos_data)
                    self.positions[position.token_address] = position
                
                # Load closed positions
                for pos_data in data.get('closed_positions', []):
                    pos_data['entry_time'] = datetime.fromisoformat(pos_data['entry_time'])
                    if pos_data.get('exit_time'):
                        pos_data['exit_time'] = datetime.fromisoformat(pos_data['exit_time'])
                    position = Position(**pos_data)
                    self.closed_positions.append(position)
                    
            except Exception as e:
                print(f"[paper_trading] Error loading positions: {e}")
    
    def save_positions(self):
        """Save positions to storage file"""
        try:
            data = {
                'open_positions': [],
                'closed_positions': []
            }
            
            # Save open positions
            for position in self.positions.values():
                pos_dict = asdict(position)
                pos_dict['entry_time'] = position.entry_time.isoformat()
                if position.exit_time:
                    pos_dict['exit_time'] = position.exit_time.isoformat()
                data['open_positions'].append(pos_dict)
            
            # Save closed positions
            for position in self.closed_positions:
                pos_dict = asdict(position)
                pos_dict['entry_time'] = position.entry_time.isoformat()
                if position.exit_time:
                    pos_dict['exit_time'] = position.exit_time.isoformat()
                data['closed_positions'].append(pos_dict)
            
            with open(self.storage_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"[paper_trading] Error saving positions: {e}")
    
    def get_current_price(self, token_address: str, chain: str) -> Optional[float]:
        """Get current token price from DexScreener"""
        try:
            if chain.lower() == "solana":
                url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            else:  # ethereum
                url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                pairs = data.get('pairs', [])
                if pairs:
                    # Get the pair with highest liquidity
                    best_pair = max(pairs, key=lambda x: float(x.get('liquidity', {}).get('usd', 0) or 0))
                    price = float(best_pair.get('priceUsd', 0))
                    return price if price > 0 else None
            
        except Exception as e:
            print(f"[paper_trading] Error getting price for {token_address}: {e}")
        
        return None
    
    def enter_position(self, token_address: str, token_symbol: str, chain: str, size_usd: float) -> dict:
        """Enter a new position"""
        # Check if position already exists
        if token_address in self.positions:
            return {
                "success": False,
                "message": f"Position already exists for {token_symbol}"
            }
        
        # Get current price
        current_price = self.get_current_price(token_address, chain)
        if not current_price:
            return {
                "success": False,
                "message": f"Could not get current price for {token_symbol}"
            }
        
        # Create position
        position = Position(
            token_address=token_address,
            token_symbol=token_symbol,
            chain=chain,
            entry_price=current_price,
            size_usd=size_usd,
            entry_time=datetime.now()
        )
        
        self.positions[token_address] = position
        self.save_positions()
        
        return {
            "success": True,
            "message": f"Entered {token_symbol} position: ${size_usd:.2f} at ${current_price:.8f}",
            "position": position
        }
    
    def exit_position(self, token_identifier: str) -> dict:
        """Exit a position by token address or symbol"""
        # Find position by address or symbol
        position = None
        token_key = None
        
        for key, pos in self.positions.items():
            if key == token_identifier or pos.token_symbol.lower() == token_identifier.lower():
                position = pos
                token_key = key
                break
        
        if not position:
            return {
                "success": False,
                "message": f"No open position found for {token_identifier}"
            }
        
        # Get current price
        current_price = self.get_current_price(position.token_address, position.chain)
        if not current_price:
            return {
                "success": False,
                "message": f"Could not get current price for {position.token_symbol}"
            }
        
        # Calculate P/L
        pnl_percent = ((current_price - position.entry_price) / position.entry_price) * 100
        pnl_usd = (pnl_percent / 100) * position.size_usd
        
        # Update position
        position.exit_price = current_price
        position.exit_time = datetime.now()
        position.pnl_usd = pnl_usd
        position.pnl_percent = pnl_percent
        position.status = "CLOSED"
        
        # Move to closed positions
        self.closed_positions.append(position)
        if token_key is not None:
            del self.positions[token_key]
        self.save_positions()
        
        return {
            "success": True,
            "message": f"Exited {position.token_symbol}: {pnl_percent:+.2f}% (${pnl_usd:+.2f})",
            "position": position
        }
    
    def get_pnl_summary(self) -> dict:
        """Get P/L summary for all positions"""
        # Calculate open P/L
        open_pnl = 0
        open_positions_data = []
        
        for position in self.positions.values():
            current_price = self.get_current_price(position.token_address, position.chain)
            if current_price:
                pnl_percent = ((current_price - position.entry_price) / position.entry_price) * 100
                pnl_usd = (pnl_percent / 100) * position.size_usd
                open_pnl += pnl_usd
                
                open_positions_data.append({
                    "symbol": position.token_symbol,
                    "chain": position.chain,
                    "entry_price": position.entry_price,
                    "current_price": current_price,
                    "size_usd": position.size_usd,
                    "pnl_percent": pnl_percent,
                    "pnl_usd": pnl_usd,
                    "duration": str(datetime.now() - position.entry_time).split('.')[0]
                })
        
        # Calculate closed P/L
        closed_pnl = sum(pos.pnl_usd for pos in self.closed_positions if pos.pnl_usd)
        
        # Calculate stats
        total_trades = len(self.closed_positions)
        winning_trades = len([pos for pos in self.closed_positions if pos.pnl_usd and pos.pnl_usd > 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        return {
            "open_pnl": open_pnl,
            "closed_pnl": closed_pnl,
            "total_pnl": open_pnl + closed_pnl,
            "open_positions": len(self.positions),
            "closed_positions": total_trades,
            "win_rate": win_rate,
            "open_positions_data": open_positions_data,
            "recent_closed": self.closed_positions[-5:] if self.closed_positions else []
        }

# Global paper trading engine
paper_engine = PaperTradingEngine()

def handle_trading_command(message_content: str) -> str:
    """Handle trading commands from Discord"""
    content = message_content.strip()
    
    try:
        if content.startswith('!enter'):
            # !enter <token> <size_usd>
            parts = content.split()
            if len(parts) < 3:
                return "Usage: !enter <token_address_or_symbol> <size_usd>"
            
            token = parts[1]
            try:
                size_usd = float(parts[2])
            except ValueError:
                return "Invalid size amount"
            
            # Try to determine if it's an address or symbol
            # For now, assume it's a symbol and we need to look it up
            # This would need integration with the scanner to get current tokens
            return f"Paper trading entry command received for {token} with ${size_usd}"
        
        elif content.startswith('!exit'):
            # !exit <token>
            parts = content.split()
            if len(parts) < 2:
                return "Usage: !exit <token_address_or_symbol>"
            
            token = parts[1]
            result = paper_engine.exit_position(token)
            return result["message"]
        
        elif content.startswith('!pnl'):
            # !pnl - show summary
            summary = paper_engine.get_pnl_summary()
            
            response = f"📊 **Paper Trading Summary**\n\n"
            response += f"💰 **P/L Overview**\n"
            response += f"• Open P/L: ${summary['open_pnl']:+.2f}\n"
            response += f"• Closed P/L: ${summary['closed_pnl']:+.2f}\n"
            response += f"• **Total P/L: ${summary['total_pnl']:+.2f}**\n\n"
            
            response += f"📈 **Stats**\n"
            response += f"• Open Positions: {summary['open_positions']}\n"
            response += f"• Closed Trades: {summary['closed_positions']}\n"
            response += f"• Win Rate: {summary['win_rate']:.1f}%\n\n"
            
            if summary['open_positions_data']:
                response += f"🔓 **Open Positions**\n"
                for pos in summary['open_positions_data']:
                    response += f"• {pos['symbol']} ({pos['chain']}): {pos['pnl_percent']:+.2f}% (${pos['pnl_usd']:+.2f})\n"
                response += "\n"
            
            if summary['recent_closed']:
                response += f"📝 **Recent Closed Trades**\n"
                for pos in summary['recent_closed']:
                    response += f"• {pos.token_symbol}: {pos.pnl_percent:+.2f}% (${pos.pnl_usd:+.2f})\n"
            
            return response
        
        else:
            return "Unknown command. Use: !enter <token> <size>, !exit <token>, or !pnl"
            
    except Exception as e:
        print(f"[paper_trading] Command error: {e}")
        return f"Error processing command: {str(e)}"

def get_quick_enter_message(token_symbol: str, token_address: str, chain: str) -> str:
    """Generate quick enter message for runner alerts"""
    return f"\n\n💡 **Paper Trade**: `!enter {token_address} 1000` (${1000:.0f} position)"