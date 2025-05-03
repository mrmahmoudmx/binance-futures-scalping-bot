import os
import sys
import signal
from dotenv import load_dotenv
from .trading_bot import ScalpingBot
from .logger import bot_logger

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    bot_logger.info("Received shutdown signal. Cleaning up...")
    sys.exit(0)

def main():
    """Main entry point for the trading bot"""
    try:
        # Load environment variables from .env file if it exists
        load_dotenv()
        
        # Verify required environment variables
        required_env_vars = ['BINANCE_API_KEY', 'BINANCE_API_SECRET']
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            bot_logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            bot_logger.error("Please set them in your environment or .env file")
            sys.exit(1)
            
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Print startup banner
        print("""
╔════════════════════════════════════════════╗
║         Binance Futures Scalping Bot       ║
║            High-Frequency Trading          ║
║                                           ║
║    !!! USE AT YOUR OWN RISK !!!           ║
║    High leverage can lead to large losses  ║
╚════════════════════════════════════════════╝
        """)
        
        # Display warning for high leverage
        bot_logger.warning(
            "ATTENTION: This bot uses 120x leverage. "
            "This is EXTREMELY risky and can lead to rapid losses. "
            "Make sure you understand the risks before proceeding."
        )
        
        # Initialize and start the bot
        bot = ScalpingBot()
        bot.run()
        
    except KeyboardInterrupt:
        bot_logger.info("Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        bot_logger.critical(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
