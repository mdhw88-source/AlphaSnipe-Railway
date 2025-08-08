from datetime import datetime
from app import db

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    symbol = db.Column(db.String(20), nullable=True)
    price = db.Column(db.Float, nullable=True)
    channel_id = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, sent, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.Text, nullable=True)

class BotConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False)  # success, error, info
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class BotStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    is_online = db.Column(db.Boolean, default=False)
    last_heartbeat = db.Column(db.DateTime, nullable=True)
    guild_count = db.Column(db.Integer, default=0)
    latency = db.Column(db.Float, nullable=True)
    uptime_start = db.Column(db.DateTime, nullable=True)
