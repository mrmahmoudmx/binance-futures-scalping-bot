"""
Binance Futures Scalping Bot
---------------------------
A high-frequency scalping bot for Binance Futures with 120x leverage,
implementing advanced risk management and technical analysis strategies.
"""

from .trading_bot import ScalpingBot
from .binance_api import BinanceWrapper
from .risk_management import RiskManager
from .logger import bot_logger

__version__ = '1.0.0'
__author__ = 'BLACKBOXAI'

# Export main classes for easy imports
__all__ = ['ScalpingBot', 'BinanceWrapper', 'RiskManager', 'bot_logger']
