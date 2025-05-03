# Binance Futures Scalping Bot

A high-frequency scalping bot for Binance Futures with 120x leverage, implementing advanced risk management and technical analysis strategies.

⚠️ **WARNING: HIGH RISK** ⚠️
- This bot uses 120x leverage which is EXTREMELY risky
- Potential for rapid and significant losses
- Use at your own risk
- Paper trade first and thoroughly test before using real funds

## Features

- High-frequency scalping on 1-minute timeframes
- Advanced technical analysis using multiple indicators:
  - RSI (Relative Strength Index)
  - MACD (Moving Average Convergence Divergence)
  - EMA (Exponential Moving Average)
  - Bollinger Bands
  - Volume analysis
- Robust risk management:
  - Dynamic position sizing
  - Trailing stop-loss
  - Daily loss limits
  - Maximum trade limits
  - Liquidation risk protection
- Real-time logging and monitoring
- Configurable trading parameters
- Cross-margin with 120x leverage

## Requirements

- Python 3.8+
- Binance Futures account
- API key with Futures trading permissions

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd binance-futures-bot
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Create a .env file in the project root:
```bash
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
```

## Configuration

Edit `bot/config.yaml` to customize the bot's behavior:

```yaml
binance:
  testnet: true  # Set to false for live trading
  futures: true
  margin_type: "CROSS"
  leverage: 120

trading:
  symbol: "BTCUSDT"
  timeframe: "1m"
  trade_amount: 0.001
  profit_target_pct: 0.15
  stop_loss_pct: 0.08
  trailing_stop: true

risk_management:
  max_daily_trades: 50
  max_daily_loss_pct: 2.0
  max_position_risk_pct: 1.0
```

## Usage

1. Start with paper trading (testnet):
```bash
python -m bot.main
```

2. Monitor the logs in the `logs` directory

3. For live trading:
- Set `testnet: false` in config.yaml
- Double-check all risk parameters
- Ensure you understand the risks
- Start with a small amount

## Risk Management

The bot implements several risk management features:

1. Position Sizing
   - Dynamic calculation based on account balance
   - Maximum position size limits
   - Risk-adjusted based on volatility

2. Stop Loss
   - Initial stop loss
   - Trailing stop activation
   - Liquidation price protection

3. Daily Limits
   - Maximum number of trades per day
   - Maximum daily loss limit
   - Volume requirements

## Strategy Logic

The bot uses a combination of technical indicators for entry and exit signals:

### Entry Conditions
- Volume confirmation (1.5x above average)
- Trend confirmation using EMA cross
- RSI oversold/overbought signals
- MACD crossovers
- Bollinger Band squeezes

### Exit Conditions
- Take profit target reached
- Stop loss hit
- Trailing stop activated
- Technical indicator reversal

## Monitoring

The bot provides detailed logging:
- Trade entries and exits
- PnL tracking
- Error notifications
- Risk limit warnings

Logs are stored in the `logs` directory with daily rotation.

## Safety Features

1. Graceful shutdown handling
2. Error recovery mechanisms
3. API error handling
4. Rate limit management
5. Connection loss recovery

## Disclaimer

This bot is for educational purposes only. Cryptocurrency futures trading with high leverage is extremely risky and may not be suitable for everyone. You can lose a substantial amount of money in a very short period. DO NOT TRADE WITH MONEY YOU CANNOT AFFORD TO LOSE.

## License

MIT License - See LICENSE file for details
