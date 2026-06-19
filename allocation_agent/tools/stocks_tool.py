import random
from ..schema import MarketSentiment, Volatility

def get_market_status():
    """
    Mock tool to get Stock Market status.
    Returns a dict with 'sentiment' and 'volatility'.
    """
    # Randomly select for simulation
    sentiment = random.choice(list(MarketSentiment))
    volatility = random.choice(list(Volatility))
    
    return {
        "sentiment": sentiment,
        "volatility": volatility
    }
