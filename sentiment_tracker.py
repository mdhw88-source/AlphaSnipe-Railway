"""
Emoji-based Trade Sentiment Tracker for Alpha Sniper Bot
Tracks Discord reactions on runner alerts and correlates with trading performance
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict

@dataclass
class AlertSentiment:
    message_id: str
    token_address: str
    token_symbol: str
    chain: str
    runner_score: float
    timestamp: datetime
    reactions: Dict[str, int] = None  # emoji -> count
    sentiment_score: float = 0.0
    total_reactions: int = 0
    bullish_reactions: int = 0
    bearish_reactions: int = 0
    neutral_reactions: int = 0
    
    def __post_init__(self):
        if self.reactions is None:
            self.reactions = {}

class SentimentTracker:
    def __init__(self, storage_file="sentiment_data.json"):
        self.storage_file = storage_file
        self.alert_sentiments: Dict[str, AlertSentiment] = {}
        
        # Emoji sentiment mapping
        self.emoji_sentiment = {
            # Bullish indicators
            "🚀": 3.0, "🔥": 2.5, "💎": 2.5, "🌕": 2.0, "💰": 2.0,
            "📈": 2.0, "⬆️": 1.5, "✅": 1.5, "🎯": 1.5, "💪": 1.5,
            "👀": 1.0, "🤑": 2.0, "💸": 1.5, "🏆": 2.0, "⚡": 1.5,
            
            # Bearish indicators  
            "📉": -2.0, "⬇️": -1.5, "❌": -1.5, "💸": -1.0, "😬": -1.0,
            "🤡": -2.5, "💀": -2.0, "👎": -1.5, "🗑️": -2.0, "🔻": -1.5,
            
            # Neutral/uncertain
            "🤔": 0.0, "👍": 0.5, "🔍": 0.0, "❓": 0.0, "⚖️": 0.0,
            "🤷": 0.0, "😐": 0.0, "💭": 0.0, "🎰": 0.0
        }
        
        self.load_data()
    
    def load_data(self):
        """Load sentiment data from storage"""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    
                for alert_id, alert_data in data.get('alert_sentiments', {}).items():
                    alert_data['timestamp'] = datetime.fromisoformat(alert_data['timestamp'])
                    alert = AlertSentiment(**alert_data)
                    self.alert_sentiments[alert_id] = alert
                    
            except Exception as e:
                print(f"[sentiment_tracker] Error loading data: {e}")
    
    def save_data(self):
        """Save sentiment data to storage"""
        try:
            data = {
                'alert_sentiments': {},
                'last_updated': datetime.now().isoformat()
            }
            
            for alert_id, alert in self.alert_sentiments.items():
                alert_dict = asdict(alert)
                alert_dict['timestamp'] = alert.timestamp.isoformat()
                data['alert_sentiments'][alert_id] = alert_dict
            
            with open(self.storage_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"[sentiment_tracker] Error saving data: {e}")
    
    def register_alert(self, message_id: str, token_address: str, token_symbol: str, 
                      chain: str, runner_score: float) -> bool:
        """Register a new runner alert for sentiment tracking"""
        try:
            alert = AlertSentiment(
                message_id=message_id,
                token_address=token_address,
                token_symbol=token_symbol,
                chain=chain,
                runner_score=runner_score,
                timestamp=datetime.now()
            )
            
            self.alert_sentiments[message_id] = alert
            self.save_data()
            print(f"[sentiment_tracker] Registered alert for {token_symbol} ({message_id})")
            return True
            
        except Exception as e:
            print(f"[sentiment_tracker] Error registering alert: {e}")
            return False
    
    def update_reaction(self, message_id: str, emoji: str, count: int) -> bool:
        """Update reaction count for a message"""
        if message_id not in self.alert_sentiments:
            return False
        
        try:
            alert = self.alert_sentiments[message_id]
            alert.reactions[emoji] = count
            
            # Recalculate sentiment metrics
            self._calculate_sentiment(alert)
            self.save_data()
            return True
            
        except Exception as e:
            print(f"[sentiment_tracker] Error updating reaction: {e}")
            return False
    
    def _calculate_sentiment(self, alert: AlertSentiment):
        """Calculate sentiment metrics for an alert"""
        total_score = 0.0
        total_reactions = 0
        bullish_reactions = 0
        bearish_reactions = 0
        neutral_reactions = 0
        
        for emoji, count in alert.reactions.items():
            sentiment_value = self.emoji_sentiment.get(emoji, 0.0)
            total_score += sentiment_value * count
            total_reactions += count
            
            if sentiment_value > 0.5:
                bullish_reactions += count
            elif sentiment_value < -0.5:
                bearish_reactions += count
            else:
                neutral_reactions += count
        
        alert.sentiment_score = total_score / total_reactions if total_reactions > 0 else 0.0
        alert.total_reactions = total_reactions
        alert.bullish_reactions = bullish_reactions
        alert.bearish_reactions = bearish_reactions
        alert.neutral_reactions = neutral_reactions
    
    def get_token_sentiment(self, token_identifier: str) -> Optional[Dict]:
        """Get sentiment data for a specific token"""
        # Find by token address or symbol
        matching_alerts = []
        for alert in self.alert_sentiments.values():
            if (alert.token_address.lower() == token_identifier.lower() or 
                alert.token_symbol.lower() == token_identifier.lower()):
                matching_alerts.append(alert)
        
        if not matching_alerts:
            return None
        
        # Get the most recent alert for this token
        latest_alert = max(matching_alerts, key=lambda x: x.timestamp)
        
        return {
            'token_symbol': latest_alert.token_symbol,
            'token_address': latest_alert.token_address,
            'chain': latest_alert.chain,
            'runner_score': latest_alert.runner_score,
            'sentiment_score': latest_alert.sentiment_score,
            'total_reactions': latest_alert.total_reactions,
            'bullish_reactions': latest_alert.bullish_reactions,
            'bearish_reactions': latest_alert.bearish_reactions,
            'neutral_reactions': latest_alert.neutral_reactions,
            'reactions': latest_alert.reactions,
            'timestamp': latest_alert.timestamp,
            'age_minutes': (datetime.now() - latest_alert.timestamp).total_seconds() / 60
        }
    
    def get_sentiment_summary(self) -> Dict:
        """Get overall sentiment analysis summary"""
        if not self.alert_sentiments:
            return {
                'total_tracked_alerts': 0,
                'average_sentiment': 0.0,
                'most_bullish': None,
                'most_bearish': None,
                'recent_alerts': []
            }
        
        # Calculate overall metrics
        total_sentiment = sum(alert.sentiment_score for alert in self.alert_sentiments.values() 
                             if alert.total_reactions > 0)
        active_alerts = [alert for alert in self.alert_sentiments.values() if alert.total_reactions > 0]
        avg_sentiment = total_sentiment / len(active_alerts) if active_alerts else 0.0
        
        # Find most bullish/bearish
        most_bullish = max(active_alerts, key=lambda x: x.sentiment_score) if active_alerts else None
        most_bearish = min(active_alerts, key=lambda x: x.sentiment_score) if active_alerts else None
        
        # Recent alerts (last 24 hours)
        recent_cutoff = datetime.now() - timedelta(hours=24)
        recent_alerts = [
            alert for alert in self.alert_sentiments.values()
            if alert.timestamp > recent_cutoff
        ]
        recent_alerts.sort(key=lambda x: x.timestamp, reverse=True)
        
        return {
            'total_tracked_alerts': len(self.alert_sentiments),
            'active_alerts': len(active_alerts),
            'average_sentiment': avg_sentiment,
            'most_bullish': {
                'token': most_bullish.token_symbol,
                'score': most_bullish.sentiment_score,
                'reactions': most_bullish.total_reactions
            } if most_bullish else None,
            'most_bearish': {
                'token': most_bearish.token_symbol,
                'score': most_bearish.sentiment_score,
                'reactions': most_bearish.total_reactions
            } if most_bearish else None,
            'recent_alerts': recent_alerts[:5]
        }
    
    def get_sentiment_vs_performance(self) -> Dict:
        """Analyze correlation between sentiment and trading performance"""
        # This would integrate with paper trading data
        try:
            from paper_trading import paper_engine
            correlations = []
            paper_positions = paper_engine.closed_positions + list(paper_engine.positions.values())
        except ImportError:
            return {'correlation_data': [], 'insights': 'Paper trading module not available'}
        
        for position in paper_positions:
            sentiment_data = self.get_token_sentiment(position.token_address)
            if sentiment_data and hasattr(position, 'pnl_percent'):
                correlations.append({
                    'token': position.token_symbol,
                    'sentiment_score': sentiment_data['sentiment_score'],
                    'total_reactions': sentiment_data['total_reactions'],
                    'pnl_percent': position.pnl_percent or 0,
                    'successful': (position.pnl_percent or 0) > 0
                })
        
        if not correlations:
            return {'correlation_data': [], 'insights': 'No trading data available for correlation analysis'}
        
        # Calculate insights
        high_sentiment_wins = len([c for c in correlations if c['sentiment_score'] > 1.0 and c['successful']])
        high_sentiment_total = len([c for c in correlations if c['sentiment_score'] > 1.0])
        low_sentiment_wins = len([c for c in correlations if c['sentiment_score'] < 0 and c['successful']])
        low_sentiment_total = len([c for c in correlations if c['sentiment_score'] < 0])
        
        high_sentiment_winrate = (high_sentiment_wins / high_sentiment_total * 100) if high_sentiment_total > 0 else 0
        low_sentiment_winrate = (low_sentiment_wins / low_sentiment_total * 100) if low_sentiment_total > 0 else 0
        
        return {
            'correlation_data': correlations,
            'high_sentiment_winrate': high_sentiment_winrate,
            'low_sentiment_winrate': low_sentiment_winrate,
            'total_analyzed': len(correlations),
            'insights': f"High sentiment tokens: {high_sentiment_winrate:.1f}% win rate ({high_sentiment_wins}/{high_sentiment_total})\n"
                       f"Low sentiment tokens: {low_sentiment_winrate:.1f}% win rate ({low_sentiment_wins}/{low_sentiment_total})"
        }

# Global sentiment tracker
sentiment_tracker = SentimentTracker()

def handle_reaction_update(message_id: str, emoji: str, count: int) -> bool:
    """Handle reaction updates from Discord"""
    return sentiment_tracker.update_reaction(message_id, emoji, count)

def register_runner_alert(message_id: str, token_address: str, token_symbol: str, 
                         chain: str, runner_score: float) -> bool:
    """Register a new runner alert for sentiment tracking"""
    return sentiment_tracker.register_alert(message_id, token_address, token_symbol, chain, runner_score)

def get_sentiment_command_response(command: str) -> str:
    """Generate response for sentiment commands"""
    try:
        parts = command.strip().split()
        
        if len(parts) == 1:  # !sentiment
            summary = sentiment_tracker.get_sentiment_summary()
            
            response = f"📊 **Sentiment Analysis Summary**\n\n"
            response += f"📈 **Overview**\n"
            response += f"• Tracked Alerts: {summary['total_tracked_alerts']}\n"
            response += f"• Active (with reactions): {summary['active_alerts']}\n"
            response += f"• Average Sentiment: {summary['average_sentiment']:+.2f}\n\n"
            
            if summary['most_bullish']:
                response += f"🚀 **Most Bullish**: {summary['most_bullish']['token']} "
                response += f"({summary['most_bullish']['score']:+.2f} score, {summary['most_bullish']['reactions']} reactions)\n"
            
            if summary['most_bearish']:
                response += f"📉 **Most Bearish**: {summary['most_bearish']['token']} "
                response += f"({summary['most_bearish']['score']:+.2f} score, {summary['most_bearish']['reactions']} reactions)\n"
            
            if summary['recent_alerts']:
                response += f"\n🕐 **Recent Alerts (last 24h)**\n"
                for alert in summary['recent_alerts'][:3]:
                    age_mins = (datetime.now() - alert.timestamp).total_seconds() / 60
                    response += f"• {alert.token_symbol}: {alert.sentiment_score:+.2f} ({alert.total_reactions} reactions, {int(age_mins)}m ago)\n"
            
            # Add performance correlation
            perf_data = sentiment_tracker.get_sentiment_vs_performance()
            if perf_data['correlation_data']:
                response += f"\n💡 **Performance Insights**\n{perf_data['insights']}"
            
            return response
            
        elif len(parts) == 2:  # !sentiment <token>
            token = parts[1]
            sentiment_data = sentiment_tracker.get_token_sentiment(token)
            
            if not sentiment_data:
                return f"No sentiment data found for {token}"
            
            response = f"📊 **Sentiment for {sentiment_data['token_symbol']}**\n\n"
            response += f"🎯 **Token Info**\n"
            response += f"• Chain: {sentiment_data['chain'].upper()}\n"
            response += f"• Runner Score: {sentiment_data['runner_score']}/5\n"
            response += f"• Alert Age: {int(sentiment_data['age_minutes'])}m ago\n\n"
            
            response += f"😄 **Sentiment Analysis**\n"
            response += f"• Overall Score: {sentiment_data['sentiment_score']:+.2f}\n"
            response += f"• Total Reactions: {sentiment_data['total_reactions']}\n"
            response += f"• Bullish: {sentiment_data['bullish_reactions']} 🚀\n"
            response += f"• Bearish: {sentiment_data['bearish_reactions']} 📉\n"
            response += f"• Neutral: {sentiment_data['neutral_reactions']} 🤔\n\n"
            
            if sentiment_data['reactions']:
                response += f"🔥 **Top Reactions**\n"
                sorted_reactions = sorted(sentiment_data['reactions'].items(), 
                                        key=lambda x: x[1], reverse=True)
                for emoji, count in sorted_reactions[:5]:
                    response += f"• {emoji}: {count}\n"
            
            return response
        
        else:
            return "Usage: `!sentiment` or `!sentiment <token_address_or_symbol>`"
            
    except Exception as e:
        print(f"[sentiment_tracker] Error in command response: {e}")
        return f"Error processing sentiment command: {str(e)}"