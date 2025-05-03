from typing import Dict, Optional
from datetime import datetime, timedelta
import yaml
from .logger import bot_logger

class RiskManager:
    def __init__(self, config_path: str = 'bot/config.yaml'):
        """Initialize Risk Manager with configuration"""
        self.config = self._load_config(config_path)
        self.daily_trades = []
        self.daily_pnl = 0.0
        self.initial_balance = None
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            bot_logger.error(f"Failed to load config: {str(e)}", exc_info=True)
            raise

    def can_open_position(self, 
                         current_price: float,
                         balance: float,
                         volume_24h: float) -> tuple[bool, str]:
        """
        Check if a new position can be opened based on risk parameters
        Returns: (bool, str) - (can_trade, reason)
        """
        if not self.initial_balance:
            self.initial_balance = balance

        # Check daily loss limit
        daily_loss_limit = self.initial_balance * (self.config['risk_management']['max_daily_loss_pct'] / 100)
        if self.daily_pnl <= -daily_loss_limit:
            return False, "Daily loss limit reached"

        # Check maximum number of daily trades
        self._update_daily_trades()
        if len(self.daily_trades) >= self.config['risk_management']['max_daily_trades']:
            return False, "Maximum daily trades reached"

        # Check minimum 24h volume
        if volume_24h < self.config['risk_management']['min_volume_24h']:
            return False, f"24h volume ({volume_24h}) below minimum threshold"

        # All checks passed
        return True, "Risk checks passed"

    def calculate_position_size(self, 
                              balance: float,
                              current_price: float,
                              stop_loss_pct: Optional[float] = None) -> float:
        """Calculate safe position size based on risk parameters"""
        if stop_loss_pct is None:
            stop_loss_pct = self.config['trading']['stop_loss_pct']

        # Calculate maximum position size based on risk per trade
        max_risk_amount = balance * (self.config['risk_management']['max_position_risk_pct'] / 100)
        
        # Calculate position size based on stop loss
        position_size = max_risk_amount / (current_price * (stop_loss_pct / 100))
        
        # Ensure position size doesn't exceed maximum allowed
        max_position_size = self.config['trading']['max_position_size']
        position_size = min(position_size, max_position_size)
        
        return position_size

    def calculate_stop_loss(self, 
                           entry_price: float,
                           side: str,
                           custom_stop_pct: Optional[float] = None) -> float:
        """Calculate stop loss price based on configuration"""
        stop_pct = custom_stop_pct or self.config['trading']['stop_loss_pct']
        
        if side.upper() == 'BUY':
            return entry_price * (1 - stop_pct / 100)
        else:
            return entry_price * (1 + stop_pct / 100)

    def calculate_take_profit(self, 
                            entry_price: float,
                            side: str,
                            custom_profit_pct: Optional[float] = None) -> float:
        """Calculate take profit price based on configuration"""
        profit_pct = custom_profit_pct or self.config['trading']['profit_target_pct']
        
        if side.upper() == 'BUY':
            return entry_price * (1 + profit_pct / 100)
        else:
            return entry_price * (1 - profit_pct / 100)

    def update_trade_result(self, pnl: float):
        """Update daily PnL and trade history"""
        self.daily_pnl += pnl
        self.daily_trades.append({
            'timestamp': datetime.now(),
            'pnl': pnl
        })
        
        bot_logger.info(f"Trade PnL: {pnl:.2f} USDT, Daily PnL: {self.daily_pnl:.2f} USDT")

    def _update_daily_trades(self):
        """Remove trades older than 24 hours"""
        cutoff_time = datetime.now() - timedelta(days=1)
        self.daily_trades = [
            trade for trade in self.daily_trades 
            if trade['timestamp'] > cutoff_time
        ]
        
        # Recalculate daily PnL
        self.daily_pnl = sum(trade['pnl'] for trade in self.daily_trades)

    def check_liquidation_risk(self, 
                             position_size: float,
                             entry_price: float,
                             leverage: int,
                             margin_balance: float) -> tuple[bool, float]:
        """
        Check if position has sufficient distance to liquidation
        Returns: (is_safe, distance_to_liquidation_percent)
        """
        position_value = position_size * entry_price
        required_margin = position_value / leverage
        maintenance_margin_rate = 0.004  # 0.4% for most pairs
        
        # Calculate liquidation price (simplified)
        liquidation_margin = required_margin * maintenance_margin_rate
        max_loss = margin_balance - liquidation_margin
        max_price_move = (max_loss * leverage) / position_value
        
        distance_to_liquidation = max_price_move * 100  # Convert to percentage
        
        is_safe = distance_to_liquidation >= self.config['risk_management']['min_distance_to_liquidation']
        
        if not is_safe:
            bot_logger.warning(
                f"Liquidation risk warning: {distance_to_liquidation:.2f}% "
                f"to liquidation (minimum: {self.config['risk_management']['min_distance_to_liquidation']}%)"
            )
        
        return is_safe, distance_to_liquidation

    def calculate_trailing_stop(self,
                              current_price: float,
                              entry_price: float,
                              side: str,
                              highest_price: float = None,
                              lowest_price: float = None) -> Optional[float]:
        """
        Calculate trailing stop price if conditions are met
        Returns: New stop price or None if trailing stop shouldn't be activated
        """
        if not self.config['trading']['trailing_stop']:
            return None
            
        activation_threshold = self.config['trading']['trailing_stop_activation'] / 100
        trail_distance = self.config['trading']['trailing_stop_distance'] / 100
        
        if side.upper() == 'BUY':
            # For long positions
            if highest_price is None:
                highest_price = current_price
                
            profit_pct = (highest_price - entry_price) / entry_price
            if profit_pct >= activation_threshold:
                return highest_price * (1 - trail_distance)
        else:
            # For short positions
            if lowest_price is None:
                lowest_price = current_price
                
            profit_pct = (entry_price - lowest_price) / entry_price
            if profit_pct >= activation_threshold:
                return lowest_price * (1 + trail_distance)
                
        return None

if __name__ == "__main__":
    # Example usage
    risk_manager = RiskManager()
    can_trade, reason = risk_manager.can_open_position(
        current_price=50000,
        balance=10000,
        volume_24h=1000000000
    )
    print(f"Can trade: {can_trade}, Reason: {reason}")
