import pathway as pw


class ForexOHLCVSchema(pw.Schema):
    """Input schema for raw OHLCV data"""

    ts_ms: int  # Timestamp in milliseconds
    open: float
    high: float
    low: float
    close: float
    volume: float
    pair: str


class ForexOHLCVWithTimestampSchema(pw.Schema):
    """Schema with parsed timestamp"""

    timestamp: pw.DateTimeUtc
    open: float
    high: float
    low: float
    close: float
    volume: float
    pair: str


class RawForexSchema(pw.Schema):
    """Schema for reading raw CSV"""

    ts_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float
