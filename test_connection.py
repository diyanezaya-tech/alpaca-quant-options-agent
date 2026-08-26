import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

load_dotenv()

client = TradingClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    paper=True,
)

account = client.get_account()
print("Account ID:", account.id)
print("Status:", account.status)
print("Cash:", account.cash)
print("Portfolio value:", account.portfolio_value)
print("Buying power:", account.buying_power)
print("Options trading level:", getattr(account, "options_trading_level", "N/A"))
print("Options approved:", getattr(account, "options_approved_level", "N/A"))