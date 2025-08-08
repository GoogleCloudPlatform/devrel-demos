import yfinance as yf

def get_stock_price(ticker: str) -> dict:
    """
    Gets the most recent stock price for a given ticker symbol.

    Args:
        ticker (str): The stock ticker symbol to look up (e.g., 'GOOGL', 'AAPL').

    Returns:
        A dictionary containing the status and the price, or an error message.
    """
    try:
        stock = yf.Ticker(ticker)
        # Fetching the last 2 days to ensure we get the most recent closing price
        todays_data = stock.history(period='2d')
        if todays_data.empty:
            return {"status": "error", "message": f"Could not find ticker symbol: {ticker}"}
        
        last_price = todays_data['Close'].iloc[-1]
        return {"status": "success", "ticker": ticker, "price": last_price}
    except Exception as e:
        return {"status": "error", "message": f"An error occurred while fetching the price for {ticker}: {str(e)}"}
