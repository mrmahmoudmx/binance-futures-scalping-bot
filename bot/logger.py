import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

class BotLogger:
    def __init__(self):
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.makedirs('logs')

        # Set up logging format
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        formatter = logging.Formatter(log_format)

        # Set up file handler with rotation
        log_file = f'logs/trading_bot_{datetime.now().strftime("%Y%m%d")}.log'
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)

        # Set up console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        # Set up logger
        self.logger = logging.getLogger('TradingBot')
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def info(self, message):
        """Log info level message"""
        self.logger.info(message)

    def warning(self, message):
        """Log warning level message"""
        self.logger.warning(message)

    def error(self, message, exc_info=None):
        """Log error level message with optional exception info"""
        self.logger.error(message, exc_info=exc_info)

    def trade(self, message):
        """Log trade-specific information"""
        self.logger.info(f"TRADE: {message}")

    def position(self, message):
        """Log position-specific information"""
        self.logger.info(f"POSITION: {message}")

    def balance(self, message):
        """Log balance-specific information"""
        self.logger.info(f"BALANCE: {message}")

    def signal(self, message):
        """Log trading signal information"""
        self.logger.info(f"SIGNAL: {message}")

    def critical(self, message, exc_info=None):
        """Log critical errors that require immediate attention"""
        self.logger.critical(message, exc_info=exc_info)

# Global logger instance
bot_logger = BotLogger()

# Example usage:
if __name__ == "__main__":
    bot_logger.info("Trading bot started")
    bot_logger.trade("Opening long position BTCUSDT")
    try:
        raise Exception("Test error")
    except Exception as e:
        bot_logger.error("An error occurred", exc_info=True)
