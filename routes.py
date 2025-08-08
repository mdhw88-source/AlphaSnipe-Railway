import asyncio
import logging
from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, flash, jsonify
from app import app, db
from models import Alert, BotConfig, ActivityLog, BotStatus
from discord_bot import send_alert, get_bot_instance

@app.route('/')
def dashboard():
    """Main dashboard view"""
    # Get bot status
    bot_status = BotStatus.query.first()
    
    # Get recent alerts
    recent_alerts = Alert.query.order_by(Alert.created_at.desc()).limit(5).all()
    
    # Get activity logs
    recent_logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(10).all()
    
    # Statistics
    total_alerts = Alert.query.count()
    sent_alerts = Alert.query.filter_by(status='sent').count()
    failed_alerts = Alert.query.filter_by(status='failed').count()
    pending_alerts = Alert.query.filter_by(status='pending').count()
    
    stats = {
        'total_alerts': total_alerts,
        'sent_alerts': sent_alerts,
        'failed_alerts': failed_alerts,
        'pending_alerts': pending_alerts
    }
    
    return render_template('dashboard.html', 
                         bot_status=bot_status,
                         recent_alerts=recent_alerts,
                         recent_logs=recent_logs,
                         stats=stats)

@app.route('/alerts')
def alerts():
    """View all alerts"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    
    query = Alert.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    alerts = query.order_by(Alert.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('alerts.html', alerts=alerts, status_filter=status_filter)

@app.route('/alerts/new', methods=['GET', 'POST'])
def new_alert():
    """Create a new alert"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        message = request.form.get('message', '').strip()
        symbol = request.form.get('symbol', '').strip()
        price = request.form.get('price', '').strip()
        channel_id = request.form.get('channel_id', '').strip()
        send_immediately = request.form.get('send_immediately') == 'on'
        
        # Validation
        if not title or not message or not channel_id:
            flash('Title, message, and channel ID are required.', 'error')
            return render_template('alerts.html')
        
        try:
            # Create alert
            alert = Alert(
                title=title,
                message=message,
                symbol=symbol if symbol else None,
                price=float(price) if price else None,
                channel_id=channel_id,
                status='pending'
            )
            
            db.session.add(alert)
            db.session.commit()
            
            # Send immediately if requested
            if send_immediately:
                return redirect(url_for('send_alert_route', alert_id=alert.id))
            
            flash('Alert created successfully!', 'success')
            return redirect(url_for('alerts'))
            
        except ValueError:
            flash('Invalid price format.', 'error')
        except Exception as e:
            flash(f'Error creating alert: {str(e)}', 'error')
            logging.error(f"Error creating alert: {e}")
    
    return redirect(url_for('alerts'))

@app.route('/alerts/<int:alert_id>/send')
def send_alert_route(alert_id):
    """Send a specific alert"""
    alert = Alert.query.get_or_404(alert_id)
    
    if alert.status == 'sent':
        flash('Alert has already been sent.', 'warning')
        return redirect(url_for('alerts'))
    
    bot = get_bot_instance()
    if not bot or not bot.is_ready():
        flash('Discord bot is not ready. Please try again later.', 'error')
        return redirect(url_for('alerts'))
    
    try:
        # Schedule the alert to be sent
        asyncio.create_task(send_alert(alert_id))
        flash('Alert is being sent...', 'info')
    except Exception as e:
        flash(f'Error sending alert: {str(e)}', 'error')
        logging.error(f"Error sending alert {alert_id}: {e}")
    
    return redirect(url_for('alerts'))

@app.route('/alerts/<int:alert_id>/delete', methods=['POST'])
def delete_alert(alert_id):
    """Delete an alert"""
    alert = Alert.query.get_or_404(alert_id)
    
    try:
        db.session.delete(alert)
        db.session.commit()
        flash('Alert deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting alert: {str(e)}', 'error')
        logging.error(f"Error deleting alert {alert_id}: {e}")
    
    return redirect(url_for('alerts'))

@app.route('/config')
def config():
    """Bot configuration management"""
    configs = BotConfig.query.all()
    return render_template('config.html', configs=configs)

@app.route('/config/update', methods=['POST'])
def update_config():
    """Update bot configuration"""
    try:
        for key, value in request.form.items():
            if key.startswith('config_'):
                config_key = key.replace('config_', '')
                config = BotConfig.query.filter_by(key=config_key).first()
                
                if config:
                    config.value = value
                    config.updated_at = datetime.utcnow()
                else:
                    config = BotConfig(
                        key=config_key,
                        value=value,
                        updated_at=datetime.utcnow()
                    )
                    db.session.add(config)
        
        db.session.commit()
        flash('Configuration updated successfully!', 'success')
        
    except Exception as e:
        flash(f'Error updating configuration: {str(e)}', 'error')
        logging.error(f"Error updating config: {e}")
    
    return redirect(url_for('config'))

@app.route('/logs')
def logs():
    """View activity logs"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    
    query = ActivityLog.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    logs = query.order_by(ActivityLog.timestamp.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    
    return render_template('logs.html', logs=logs, status_filter=status_filter)

@app.route('/api/status')
def api_status():
    """API endpoint for bot status"""
    bot_status = BotStatus.query.first()
    bot = get_bot_instance()
    
    status_data = {
        'is_online': False,
        'guild_count': 0,
        'latency': 0,
        'uptime': None
    }
    
    if bot_status:
        status_data.update({
            'is_online': bot_status.is_online and bot is not None and bot.is_ready(),
            'guild_count': bot_status.guild_count,
            'latency': round(bot_status.latency, 2) if bot_status.latency else 0,
            'uptime': str(datetime.utcnow() - bot_status.uptime_start) if bot_status.uptime_start else None
        })
    
    return jsonify(status_data)

@app.route('/api/alerts/pending')
def api_pending_alerts():
    """API endpoint for pending alerts count"""
    pending_count = Alert.query.filter_by(status='pending').count()
    return jsonify({'pending_alerts': pending_count})
