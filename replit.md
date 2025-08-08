# Overview

Alpha Sniper Bot is a cryptocurrency alert system that combines a Discord bot with a Flask web dashboard. The application automatically scans multiple data sources for fresh cryptocurrency opportunities and sends real-time alerts to Discord channels. It features comprehensive duplicate prevention, rate limiting, and a web interface for monitoring bot status and activity logs.

## Recent Changes (August 2025)
- ✅ **Fresh Token Detection System**: Implemented multi-source scanner using CoinGecko, Birdeye, and Solscan APIs for truly fresh opportunities
- ✅ **Smart Duplicate Prevention**: Added token tracking system that prevents spam while allowing fresh alerts every hour
- ✅ **Rate Limiting**: Fixed rapid-fire duplicate alerts issue with proper cooldown mechanisms
- ✅ **Enhanced Filtering**: Optimized for small-cap tokens under $1.5M market cap with proper age and liquidity filters
- ✅ **Production Ready**: Bot successfully delivering unique crypto alerts every 20 seconds to Discord webhook

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Web Application Framework
The application uses Flask as the primary web framework with SQLAlchemy for database operations. The architecture employs a traditional MVC pattern with separate modules for models, routes, and templates. Flask-SQLAlchemy provides the ORM layer with a declarative base model for database operations.

## Database Design
The system uses SQLite as the default database with support for PostgreSQL through environment configuration. The database schema includes four main entities:
- **Alert**: Stores cryptocurrency alerts with status tracking
- **BotConfig**: Manages bot configuration settings as key-value pairs
- **ActivityLog**: Records system events and bot activities
- **BotStatus**: Tracks real-time bot connection status and metrics

## Discord Bot Integration
The Discord bot runs as a separate thread alongside the Flask application using the discord.py library. The bot handles real-time messaging while sharing the same database context as the web application. This dual-threaded approach allows simultaneous web dashboard access and Discord bot operations.

## Frontend Architecture
The frontend uses Bootstrap 5 with a dark theme optimized for cryptocurrency applications. The template system includes:
- Base template with navigation and shared components
- Dashboard with real-time status monitoring and charts
- Alert management interface with filtering and pagination
- Configuration management for bot settings
- Activity logging with status-based filtering

The interface incorporates Feather icons and Chart.js for data visualization, with custom CSS providing crypto-themed styling and animations.

## Data Flow Architecture
Alerts flow from web creation through database storage to Discord delivery. The system tracks alert lifecycle states (pending, sent, failed) and logs all activities for monitoring. The bot status updates in real-time through database heartbeat mechanisms.

# External Dependencies

## Core Framework Dependencies
- **Flask**: Web application framework with SQLAlchemy integration
- **discord.py**: Discord bot library for message handling and guild management
- **SQLAlchemy**: Database ORM with support for SQLite and PostgreSQL

## Frontend Libraries
- **Bootstrap 5**: UI framework with dark theme support
- **Feather Icons**: Icon library for consistent interface elements
- **Chart.js**: JavaScript charting library for dashboard analytics

## Infrastructure Requirements
- **Discord Bot Token**: Required for bot authentication and Discord API access
- **Database**: SQLite default with PostgreSQL support via DATABASE_URL environment variable
- **Session Management**: Configurable session secret for Flask security

## Optional Integrations
The system is designed to accommodate cryptocurrency price APIs and webhook integrations for automated alert triggers, though these are not currently implemented in the core architecture.