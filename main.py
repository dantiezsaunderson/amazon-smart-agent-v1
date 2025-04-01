#!/usr/bin/env python3
"""
Amazon Smart Agent - Automated Arbitrage Bot
Main application entry point
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.getenv('LOG_FILE', 'logs/arbitrage_bot.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the application"""
    logger.info("Starting Amazon Smart Agent - Arbitrage Bot")
    
    # Import modules here to avoid circular imports
    from src.cli import cli_app
    from src.telegram_bot import bot_app
    from src.web_dashboard import dashboard_app
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Amazon Smart Agent - Arbitrage Bot')
    parser.add_argument('--cli', action='store_true', help='Run CLI tool')
    parser.add_argument('--telegram', action='store_true', help='Run Telegram bot')
    parser.add_argument('--dashboard', action='store_true', help='Run web dashboard')
    parser.add_argument('--all', action='store_true', help='Run all components')
    args = parser.parse_args()
    
    # Run components based on arguments
    if args.cli or args.all:
        logger.info("Starting CLI tool")
        cli_app.run()
    
    if args.telegram or args.all:
        logger.info("Starting Telegram bot")
        bot_app.run()
    
    if args.dashboard or args.all:
        logger.info("Starting web dashboard")
        dashboard_app.run()
    
    # If no arguments provided, show help
    if not (args.cli or args.telegram or args.dashboard or args.all):
        parser.print_help()

if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(os.getenv('LOG_FILE', 'logs/arbitrage_bot.log')), exist_ok=True)
    
    try:
        main()
    except Exception as e:
        logger.exception(f"Unhandled exception: {e}")
        sys.exit(1)
