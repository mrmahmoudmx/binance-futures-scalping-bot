import time
from typing import Dict, Optional, List
import numpy as np
import pandas as pd
import ta
from datetime import datetime
from .binance_api import BinanceWrapper
from .risk_management import RiskManager
from .logger import bot_logger

class ScalpingBot:
    def __init__(self, config_path: str = 'bot/config.yaml'):
        """Initialize the scalping trading bot"""
        self.binance = BinanceWrapper(config_path)
        self.risk_manager = RiskManager(config_path)
        
        # Trading state
        self.in_position = False
        self.position_side = None
        self.entry_price = None
        self.position_size = None
        self.stop_loss = None
        self.take_profit = None
        self.highest_price = None
        self.lowest_price = None

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators for trading decisions"""
        # RSI
        df['rsi'] = ta.momentum.RSIIndicator(
            df['close'], 
            window=14
        ).rsi()
        
        # MACD
        macd = ta.trend.MACD(
            df['close'],
            window_fast=12,
            window_slow=26,
            window_sign=9
        )
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        
        # EMAs
        df['ema_short'] = ta.trend.EMAIndicator(
            df['close'], 
            window=9
        ).ema_indicator()
        df['ema_long'] = ta.trend.EMAIndicator(
            df['close'], 
            window=21
        ).ema_indicator()
        
        # Bollinger Bands
        bollinger = ta.volatility.BollingerBands(
            df['close'],
            window=20,
            window_dev=2
        )
        df['bb_upper'] = bollinger.bollinger_hband()
        df['bb_lower'] = bollinger.bollinger_lband()
        df['bb_middle'] = bollinger.bollinger_mavg()
        
        # Volume indicators
        df['volume_ema'] = ta.trend.EMAIndicator(
            df['volume'],
            window=20
        ).ema_indicator()
        
        return df

    def get_trading_signals(self, df: pd.DataFrame) -> tuple[bool, bool]:
        """
        Analyze indicators and return trading signals
        Returns: (buy_signal, sell_signal)
        """
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Initialize signals
        buy_signal = False
        sell_signal = False
        
        # Volume confirmation
        volume_active = current['volume'] > current['volume_ema'] * 1.5
        
        # Trend confirmation
        uptrend = current['ema_short'] > current['ema_long']
        downtrend = current['ema_short'] < current['ema_long']
        
        # RSI conditions
        rsi_oversold = current['rsi'] < 30
        rsi_overbought = current['rsi'] > 70
        
        # MACD crossover
        macd_cross_up = (prev['macd'] < prev['macd_signal']) and (current['macd'] > current['macd_signal'])
        macd_cross_down = (prev['macd'] > prev['macd_signal']) and (current['macd'] < current['macd_signal'])
        
        # Bollinger Band conditions
        bb_squeeze = (current['bb_upper'] - current['bb_lower']) < (prev['bb_upper'] - prev['bb_lower'])
        price_near_lower = current['close'] <= current['bb_lower'] * 1.001
        price_near_upper = current['close'] >= current['bb_upper'] * 0.999
        
        # Generate buy signal
        if (not self.in_position and
            uptrend and
            rsi_oversold and
            macd_cross_up and
            price_near_lower and
            volume_active):
            buy_signal = True
            
        # Generate sell signal
        elif (not self.in_position and
              downtrend and
              rsi_overbought and
              macd_cross_down and
              price_near_upper and
              volume_active):
            sell_signal = True
            
        return buy_signal, sell_signal

    def execute_trade(self, side: str, current_price: float):
        """Execute a trade based on the signal"""
        try:
            # Get account balance
            balance = float(self.binance.get_account_balance()['balance'])
            
            # Calculate position size
            position_size = self.risk_manager.calculate_position_size(
                balance=balance,
                current_price=current_price
            )
            
            # Place the order
            order = self.binance.place_order(
                side=side,
                quantity=position_size,
                order_type='MARKET'
            )
            
            # Update position tracking
            self.in_position = True
            self.position_side = side
            self.position_size = position_size
            self.entry_price = float(order['avgPrice'])
            
            # Set stop loss and take profit
            self.stop_loss = self.risk_manager.calculate_stop_loss(
                self.entry_price,
                side
            )
            self.take_profit = self.risk_manager.calculate_take_profit(
                self.entry_price,
                side
            )
            
            # Initialize price tracking for trailing stop
            if side == 'BUY':
                self.highest_price = self.entry_price
                self.lowest_price = None
            else:
                self.highest_price = None
                self.lowest_price = self.entry_price
            
            bot_logger.trade(
                f"Opened {side} position: Size={position_size}, "
                f"Entry={self.entry_price}, SL={self.stop_loss}, TP={self.take_profit}"
            )
            
        except Exception as e:
            bot_logger.error(f"Error executing trade: {str(e)}", exc_info=True)
            self.reset_position()

    def manage_position(self, current_price: float):
        """Manage open position - check stop loss, take profit, and trailing stop"""
        if not self.in_position:
            return
            
        # Update highest/lowest prices for trailing stop
        if self.position_side == 'BUY':
            self.highest_price = max(self.highest_price, current_price)
        else:
            self.lowest_price = min(self.lowest_price, current_price)
            
        # Check trailing stop
        trailing_stop = self.risk_manager.calculate_trailing_stop(
            current_price=current_price,
            entry_price=self.entry_price,
            side=self.position_side,
            highest_price=self.highest_price,
            lowest_price=self.lowest_price
        )
        
        if trailing_stop:
            self.stop_loss = trailing_stop
            
        # Check if stop loss or take profit hit
        if self.position_side == 'BUY':
            if current_price <= self.stop_loss:
                self.close_position('Stop loss hit')
            elif current_price >= self.take_profit:
                self.close_position('Take profit hit')
        else:
            if current_price >= self.stop_loss:
                self.close_position('Stop loss hit')
            elif current_price <= self.take_profit:
                self.close_position('Take profit hit')

    def close_position(self, reason: str):
        """Close the current position"""
        try:
            close_side = 'SELL' if self.position_side == 'BUY' else 'BUY'
            
            # Place closing order
            order = self.binance.place_order(
                side=close_side,
                quantity=self.position_size,
                order_type='MARKET',
                reduce_only=True
            )
            
            # Calculate PnL
            exit_price = float(order['avgPrice'])
            pnl = (exit_price - self.entry_price) * self.position_size
            if self.position_side == 'SELL':
                pnl = -pnl
                
            # Update risk manager
            self.risk_manager.update_trade_result(pnl)
            
            bot_logger.trade(
                f"Closed position: Reason={reason}, Entry={self.entry_price}, "
                f"Exit={exit_price}, PnL={pnl:.2f} USDT"
            )
            
        except Exception as e:
            bot_logger.error(f"Error closing position: {str(e)}", exc_info=True)
        finally:
            self.reset_position()

    def reset_position(self):
        """Reset position tracking variables"""
        self.in_position = False
        self.position_side = None
        self.entry_price = None
        self.position_size = None
        self.stop_loss = None
        self.take_profit = None
        self.highest_price = None
        self.lowest_price = None

    def run(self):
        """Main bot loop"""
        bot_logger.info("Starting scalping bot...")
        
        while True:
            try:
                # Get latest market data
                klines = self.binance.get_market_data(interval='1m', limit=100)
                
                # Convert to DataFrame
                df = pd.DataFrame(klines)
                df['close'] = pd.to_numeric(df['close'])
                df['high'] = pd.to_numeric(df['high'])
                df['low'] = pd.to_numeric(df['low'])
                df['volume'] = pd.to_numeric(df['volume'])
                
                # Calculate indicators
                df = self.calculate_indicators(df)
                
                current_price = float(df.iloc[-1]['close'])
                
                # Manage open position if exists
                if self.in_position:
                    self.manage_position(current_price)
                else:
                    # Check for new trade signals
                    buy_signal, sell_signal = self.get_trading_signals(df)
                    
                    # Get 24h volume
                    volume_24h = df['volume'].sum() * current_price
                    
                    if buy_signal or sell_signal:
                        # Check risk parameters
                        balance = float(self.binance.get_account_balance()['balance'])
                        can_trade, reason = self.risk_manager.can_open_position(
                            current_price=current_price,
                            balance=balance,
                            volume_24h=volume_24h
                        )
                        
                        if can_trade:
                            if buy_signal:
                                self.execute_trade('BUY', current_price)
                            elif sell_signal:
                                self.execute_trade('SELL', current_price)
                        else:
                            bot_logger.info(f"Trade signal ignored: {reason}")
                
                # Sleep until next candle
                time.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                bot_logger.error(f"Error in main loop: {str(e)}", exc_info=True)
                time.sleep(5)  # Wait before retrying

if __name__ == "__main__":
    bot = ScalpingBot()
    bot.run()
