import time
from typing import Dict, Optional, List
import yaml
from binance.client import Client
from binance.exceptions import BinanceAPIException
from binance.enums import *
import os
from decimal import Decimal
from .logger import bot_logger

class BinanceWrapper:
    def __init__(self, config_path: str = 'bot/config.yaml'):
        """Initialize Binance API wrapper with configuration"""
        self.config = self._load_config(config_path)
        self.client = self._initialize_client()
        self.symbol = self.config['trading']['symbol']
        self._setup_leverage_and_margin()
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            bot_logger.critical(f"Failed to load config: {str(e)}", exc_info=True)
            raise

    def _initialize_client(self) -> Client:
        """Initialize Binance client with API credentials"""
        try:
            api_key = os.getenv('BINANCE_API_KEY') or self.config['binance']['api_key']
            api_secret = os.getenv('BINANCE_API_SECRET') or self.config['binance']['api_secret']
            testnet = self.config['binance'].get('testnet', True)
            
            client = Client(api_key, api_secret, testnet=testnet)
            bot_logger.info("Binance client initialized successfully")
            return client
        except Exception as e:
            bot_logger.critical(f"Failed to initialize Binance client: {str(e)}", exc_info=True)
            raise

    def _setup_leverage_and_margin(self):
        """Set up leverage and margin type for futures trading"""
        try:
            # Set margin type to CROSSED
            self.client.futures_change_margin_type(
                symbol=self.symbol,
                marginType='CROSSED'
            )
            bot_logger.info(f"Margin type set to CROSSED for {self.symbol}")

            # Set leverage
            leverage = self.config['binance']['leverage']
            self.client.futures_change_leverage(
                symbol=self.symbol,
                leverage=leverage
            )
            bot_logger.info(f"Leverage set to {leverage}x for {self.symbol}")
        except BinanceAPIException as e:
            if e.code == -4046:  # Already set
                bot_logger.info("Leverage and margin type already set correctly")
            else:
                bot_logger.error(f"Error setting leverage/margin: {str(e)}", exc_info=True)
                raise

    def get_symbol_info(self) -> Dict:
        """Get detailed information about the trading symbol"""
        try:
            exchange_info = self.client.futures_exchange_info()
            symbol_info = next(
                (item for item in exchange_info['symbols'] if item['symbol'] == self.symbol),
                None
            )
            if not symbol_info:
                raise ValueError(f"Symbol {self.symbol} not found in futures exchange")
            return symbol_info
        except Exception as e:
            bot_logger.error(f"Error getting symbol info: {str(e)}", exc_info=True)
            raise

    def get_market_data(self, interval: str = '1m', limit: int = 100) -> List[Dict]:
        """Get historical kline/candlestick data"""
        try:
            klines = self.client.futures_klines(
                symbol=self.symbol,
                interval=interval,
                limit=limit
            )
            return [
                {
                    'timestamp': k[0],
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5]),
                    'close_time': k[6],
                    'quote_volume': float(k[7]),
                    'trades': int(k[8])
                }
                for k in klines
            ]
        except Exception as e:
            bot_logger.error(f"Error fetching market data: {str(e)}", exc_info=True)
            raise

    def place_order(
        self,
        side: str,
        quantity: float,
        order_type: str = ORDER_TYPE_MARKET,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        reduce_only: bool = False
    ) -> Dict:
        """Place an order on Binance Futures"""
        try:
            params = {
                'symbol': self.symbol,
                'side': side,
                'type': order_type,
                'quantity': self._format_quantity(quantity)
            }

            if price:
                params['price'] = self._format_price(price)
            if stop_price:
                params['stopPrice'] = self._format_price(stop_price)
            if reduce_only:
                params['reduceOnly'] = 'true'

            order = self.client.futures_create_order(**params)
            bot_logger.trade(
                f"Order placed - Side: {side}, Type: {order_type}, "
                f"Quantity: {quantity}, Price: {price}, Stop: {stop_price}"
            )
            return order
        except Exception as e:
            bot_logger.error(f"Error placing order: {str(e)}", exc_info=True)
            raise

    def get_position(self) -> Dict:
        """Get current position information"""
        try:
            positions = self.client.futures_position_information(symbol=self.symbol)
            position = positions[0] if positions else None
            if position:
                bot_logger.position(
                    f"Current position - Amount: {position['positionAmt']}, "
                    f"Entry Price: {position['entryPrice']}, "
                    f"Unrealized PNL: {position['unRealizedProfit']}"
                )
            return position
        except Exception as e:
            bot_logger.error(f"Error getting position info: {str(e)}", exc_info=True)
            raise

    def get_account_balance(self) -> Dict:
        """Get account balance information"""
        try:
            account = self.client.futures_account_balance()
            usdt_balance = next(
                (item for item in account if item['asset'] == 'USDT'),
                None
            )
            if usdt_balance:
                bot_logger.balance(f"Account balance: {usdt_balance['balance']} USDT")
            return usdt_balance
        except Exception as e:
            bot_logger.error(f"Error getting account balance: {str(e)}", exc_info=True)
            raise

    def cancel_all_orders(self):
        """Cancel all open orders for the symbol"""
        try:
            result = self.client.futures_cancel_all_open_orders(symbol=self.symbol)
            bot_logger.info(f"Cancelled all orders for {self.symbol}")
            return result
        except Exception as e:
            bot_logger.error(f"Error cancelling orders: {str(e)}", exc_info=True)
            raise

    def _format_quantity(self, quantity: float) -> str:
        """Format quantity according to symbol's quantity precision"""
        symbol_info = self.get_symbol_info()
        precision = next(
            filter(lambda x: x['filterType'] == 'LOT_SIZE', symbol_info['filters'])
        )['stepSize']
        decimal_places = str(precision)[::-1].find('.')
        return f"{quantity:.{decimal_places}f}"

    def _format_price(self, price: float) -> str:
        """Format price according to symbol's price precision"""
        symbol_info = self.get_symbol_info()
        precision = next(
            filter(lambda x: x['filterType'] == 'PRICE_FILTER', symbol_info['filters'])
        )['tickSize']
        decimal_places = str(precision)[::-1].find('.')
        return f"{price:.{decimal_places}f}"

if __name__ == "__main__":
    # Example usage
    wrapper = BinanceWrapper()
    print(wrapper.get_market_data(limit=5))
