# Agent and Tool Improvements

## Summary of Improvements Made

### 1. ✅ Retry Handler Utility (`utils/retry_handler.py`)
**Status: Implemented**

- **RetryHandler**: Exponential backoff retry logic for async and sync functions
- **RateLimiter**: Token bucket algorithm for rate limiting API calls
- **CircuitBreaker**: Circuit breaker pattern for failing services
- Features:
  - Configurable max retries, backoff factor, initial delay
  - Timeout support
  - Exception-specific retry logic
  - Async and sync function support

### 2. ✅ Improved WebSearchTool
**Status: Implemented**

- Added retry logic with exponential backoff (3 retries by default)
- Added timeout handling (30s default)
- Input validation (query validation, num_results clamping)
- Better error messages
- Non-blocking execution using asyncio executor

### 3. 🔄 Recommended Additional Improvements

#### A. Logging Standardization
**Priority: High | Effort: Medium**

**Current State:**
- Mix of `print()` statements and no logging
- Inconsistent log levels
- No structured logging

**Improvements:**
```python
# utils/logger.py
import logging
import sys

def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger
```

**Action Items:**
- Replace all `print()` with proper logging
- Use structured logging with context (user_id, query_id, etc.)
- Add log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

#### B. Input Validation & Sanitization
**Priority: High | Effort: Low**

**Current State:**
- Limited input validation in tools
- No sanitization of user inputs

**Improvements:**
```python
# utils/validators.py
class InputValidator:
    @staticmethod
    def validate_query(query: str, max_length: int = 1000) -> str:
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        if len(query) > max_length:
            raise ValueError(f"Query exceeds maximum length of {max_length}")
        return query.strip()
    
    @staticmethod
    def validate_isin(isin: str) -> str:
        # ISIN format: 2 letters + 9 alphanumeric + 1 check digit
        if not re.match(r'^[A-Z]{2}[A-Z0-9]{9}\d$', isin):
            raise ValueError(f"Invalid ISIN format: {isin}")
        return isin.upper()
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        # Remove potentially harmful characters
        return text.replace('\x00', '').strip()
```

**Action Items:**
- Add validation to all tool inputs
- Sanitize user queries before processing
- Validate ISINs, company names, etc.

#### C. Rate Limiting for External APIs
**Priority: Medium | Effort: Low**

**Current State:**
- No rate limiting for SerpAPI, Groq, etc.
- Risk of hitting API rate limits

**Improvements:**
- Use `RateLimiter` from `retry_handler.py`
- Configure per-API rate limits:
  - SerpAPI: 100 requests/hour (free tier)
  - Groq: Check API limits
  - OpenAI: Already handled by SDK

**Implementation:**
```python
# In tools_manager.py
from utils.retry_handler import RateLimiter

class WebSearchTool:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('SERPAPI_KEY')
        self.rate_limiter = RateLimiter(max_calls=100, time_window=3600)  # 100/hour
    
    async def search(self, query: str, num_results: int = 10) -> ToolResult:
        await self.rate_limiter.wait_if_needed()
        # ... rest of search logic
```

#### D. Better Error Handling in Agents
**Priority: High | Effort: Medium**

**Current State:**
- Some agents catch all exceptions generically
- Error messages not always user-friendly
- No error recovery strategies

**Improvements:**
```python
# agents/base_agent.py (new base class)
class BaseAgent:
    def handle_error(self, error: Exception, context: Dict[str, Any]) -> str:
        """Convert technical errors to user-friendly messages"""
        if isinstance(error, TimeoutError):
            return "The request took too long. Please try again."
        elif isinstance(error, ValueError):
            return f"Invalid input: {str(error)}"
        elif isinstance(error, ConnectionError):
            return "Unable to connect to the service. Please check your internet connection."
        else:
            logger.error(f"Unexpected error: {error}", extra=context)
            return "An unexpected error occurred. Please try again later."
```

**Action Items:**
- Create base agent class with common error handling
- Add error recovery strategies (fallback data sources, cached responses)
- Improve error messages for users

#### E. Connection Pooling & Resource Management
**Priority: Medium | Effort: Medium**

**Current State:**
- No connection pooling for HTTP clients
- Resources not always properly cleaned up

**Improvements:**
```python
# utils/http_client.py
import aiohttp

class HTTPClientPool:
    _instance = None
    _session: Optional[aiohttp.ClientSession] = None
    
    @classmethod
    async def get_session(cls) -> aiohttp.ClientSession:
        if cls._session is None or cls._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            connector = aiohttp.TCPConnector(limit=100, limit_per_host=10)
            cls._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector
            )
        return cls._session
    
    @classmethod
    async def close(cls):
        if cls._session and not cls._session.closed:
            await cls._session.close()
```

**Action Items:**
- Implement connection pooling for aiohttp
- Add proper cleanup in orchestrator shutdown
- Use context managers for resource management

#### F. Caching Improvements
**Priority: Medium | Effort: Low**

**Current State:**
- Some tools have caching, but inconsistent
- No cache invalidation strategy
- No cache size limits

**Improvements:**
- Use consistent caching library (e.g., `cachetools`)
- Add TTL (time-to-live) for cached data
- Implement cache size limits (LRU eviction)
- Add cache invalidation on data updates

#### G. Type Hints & Documentation
**Priority: Low | Effort: Low**

**Current State:**
- Some missing type hints
- Inconsistent docstring formats

**Improvements:**
- Add type hints to all public methods
- Use consistent docstring format (Google style)
- Add type checking with mypy

#### H. Testing Improvements
**Priority: Medium | Effort: Medium**

**Current State:**
- Some tests exist but coverage could be better
- No integration tests for retry logic

**Improvements:**
- Add unit tests for retry handler
- Add integration tests for tools with retries
- Mock external APIs in tests
- Test error scenarios

## Implementation Priority

1. **High Priority (Do First):**
   - ✅ Retry handler utility
   - ✅ WebSearchTool improvements
   - Logging standardization
   - Input validation
   - Better error handling in agents

2. **Medium Priority (Do Next):**
   - Rate limiting
   - Connection pooling
   - Caching improvements
   - Testing improvements

3. **Low Priority (Nice to Have):**
   - Type hints & documentation
   - Additional monitoring/metrics

## Usage Examples

### Using Retry Handler
```python
from utils.retry_handler import RetryHandler

retry_handler = RetryHandler()

@retry_handler.with_retry(
    max_retries=3,
    backoff_factor=2.0,
    timeout=30.0,
    exceptions=(TimeoutError, ConnectionError)
)
async def my_api_call():
    # Your API call here
    pass
```

### Using Rate Limiter
```python
from utils.retry_handler import RateLimiter

rate_limiter = RateLimiter(max_calls=100, time_window=3600)

async def make_api_call():
    await rate_limiter.wait_if_needed()
    # Make your API call
    pass
```

### Using Circuit Breaker
```python
from utils.retry_handler import CircuitBreaker

circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60.0
)

async def call_external_service():
    return await circuit_breaker.call(my_api_function, arg1, arg2)
```

