# Overview

Alpha Sniper Bot is a multi-chain cryptocurrency alert system that combines a Discord bot with a Flask web dashboard. The application automatically scans Solana and Ethereum data sources for fresh runner opportunities and sends enhanced real-time alerts to Discord channels. It features comprehensive duplicate prevention, chain-specific filtering, and a web interface for monitoring bot status and activity logs.

## Recent Changes (August 2025)
- ✅ **Enhanced Multi-Chain Runner Detection**: Sophisticated momentum, volume, and timing analysis across Solana and Ethereum
- ✅ **Ultra-Fresh Discovery**: 15-minute to 1-hour optimal entry windows with age-based scoring bonuses
- ✅ **Advanced Scoring Algorithms**: Momentum analysis, buy pressure scoring, volume acceleration detection
- ✅ **Chain-Specific Optimization**: Solana ($5K-$300K caps) vs Ethereum ($25K-$1M caps) with gas-cost considerations
- ✅ **Increased Coverage**: Expanded to 50+ candidates per scan (37 Solana + 27 Ethereum sources)
- ✅ **Professional Discord Alerts**: Chain-specific formatting with ☀️ Solana and ⛽ Ethereum indicators
- ✅ **Perfect Score Detection**: Successfully identifying 5/5 runners like "Murad 💹🧲", "Ibiza Final Boss Wife", "ChillBoss"
- ✅ **Smart Duplicate Prevention**: Hourly cooldown system preventing spam while allowing fresh high-quality alerts
- ✅ **Paper Trading Integration**: Full position tracking with Discord commands (!enter, !exit, !pnl)
- ✅ **Emoji-Based Sentiment Tracker**: Real-time reaction monitoring with performance correlation analysis

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