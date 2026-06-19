"""
MCP Client for Forex Tools
==========================

This module provides a synchronous wrapper for calling tools from the
Pathway MCP server. It uses fastmcp.Client to communicate with the server.

Usage:
    from mcp_client import call_tool_sync

    # Call a tool
    result = call_tool_sync("get_trades_summary", {"pairs": ["EURUSD", "GBPUSD"]})
    print(result)

Environment Variables:
    PATHWAY_MCP_URL: URL of the MCP server (default: http://localhost:8123/mcp/)
"""

import os
import json
import asyncio
import threading
from typing import Optional, Any, Dict, Coroutine


def _run_coro_sync(coro: Coroutine) -> Any:
    """
    Run a coroutine in a synchronous context.

    If there is an active event loop (e.g., inside an async framework),
    starts a new thread with its own loop. Otherwise, uses asyncio.run.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Already in an async context - use a separate thread
        result_container = {}
        exc_container = {}

        def _runner():
            new_loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(new_loop)
                res = new_loop.run_until_complete(coro)
                result_container["res"] = res
            except Exception as e:
                exc_container["e"] = e
            finally:
                new_loop.close()

        thread = threading.Thread(target=_runner)
        thread.start()
        thread.join()

        if "e" in exc_container:
            raise exc_container["e"]
        return result_container.get("res")
    else:
        return asyncio.run(coro)


def _parse_mcp_result(result: Any) -> str:
    """
    Extract a human-readable string from MCP client call result.

    The fastmcp Client returns various formats depending on the server response.
    This function normalizes them to a string.
    """
    try:
        # Handle CallToolResult object with content attribute
        if hasattr(result, "content") and result.content:
            content = result.content
            if isinstance(content, (list, tuple)) and len(content) > 0:
                first = content[0]
                # TextContent has a 'text' attribute
                if hasattr(first, "text"):
                    return first.text
                # Dict format
                if isinstance(first, dict):
                    return first.get("text", json.dumps(first))
            return str(content)

        # fastmcp Client typically returns lists of TextContent-like objects
        if isinstance(result, (list, tuple)) and len(result) > 0:
            first = result[0]

            # Dict-like result
            if isinstance(first, dict):
                text = first.get("text") or first.get("result") or json.dumps(first)
                return text if isinstance(text, str) else json.dumps(text)

            # Object with attributes (TextContent)
            text = getattr(first, "text", None) or getattr(first, "result", None)
            if text is not None:
                return text if isinstance(text, str) else json.dumps(text)

            # Try to convert to string
            return str(first)

        # Direct string response
        if isinstance(result, str):
            return result

        # Dict response
        if isinstance(result, dict):
            return result.get("text") or result.get("result") or json.dumps(result)

        # Unknown type - stringify
        return str(result)
    except Exception:
        try:
            return json.dumps(result)
        except Exception:
            return str(result)


async def _call_tool_async(name: str, arguments: Dict, url: str) -> str:
    """Async implementation of tool call."""
    from fastmcp import Client

    client = Client(url)
    async with client:
        result = await client.call_tool(name=name, arguments=arguments)
        return _parse_mcp_result(result)


def call_tool_sync(
    name: str, arguments: Optional[Dict] = None, url: Optional[str] = None
) -> str:
    """
    Call an MCP tool synchronously and return result as text.

    This is the main function to use for calling forex tools from the MCP server.

    Parameters:
        name: Tool name (e.g., "get_trades_summary", "get_currency_regime")
        arguments: Dict of arguments to pass to the tool (e.g., {"pairs": ["EURUSD"]})
        url: Optional MCP server URL (defaults to env PATHWAY_MCP_URL or http://localhost:8123/mcp/)

    Returns:
        String result from the tool (typically Markdown-formatted)

    Example:
        >>> result = call_tool_sync("get_trades_summary", {"pairs": ["EURUSD", "GBPUSD"]})
        >>> print(result)
        ## EURUSD Trading Summary
        - **Total Trades**: 47 (28 wins, 19 losses)
        ...
    """
    if arguments is None:
        arguments = {}

    # Get MCP server URL from environment or use default
    url = (
        url
        or os.environ.get("PATHWAY_MCP_URL")
        or os.environ.get("MCP_URL")
        or "http://localhost:8123/mcp/"
    )

    try:
        from fastmcp import Client
    except ImportError as e:
        raise RuntimeError(
            "fastmcp package not installed. Install it with: pip install fastmcp"
        ) from e

    try:
        coro = _call_tool_async(name, arguments, url)
        return _run_coro_sync(coro)
    except Exception as e:
        return f"Error calling MCP tool '{name}': {str(e)}"


async def call_tool_async(
    name: str, arguments: Optional[Dict] = None, url: Optional[str] = None
) -> str:
    """
    Call an MCP tool asynchronously.
    """
    if arguments is None:
        arguments = {}

    url = (
        url
        or os.environ.get("PATHWAY_MCP_URL")
        or os.environ.get("MCP_URL")
        or "http://localhost:8123/mcp/"
    )
    return await _call_tool_async(name, arguments, url)


def list_tools_sync(url: Optional[str] = None) -> list:
    """
    List all available tools from the MCP server.

    Returns:
        List of tool information dicts
    """
    url = (
        url
        or os.environ.get("PATHWAY_MCP_URL")
        or os.environ.get("MCP_URL")
        or "http://localhost:8123/mcp/"
    )

    async def _list():
        from fastmcp import Client

        client = Client(url)
        async with client:
            return await client.list_tools()

    try:
        return _run_coro_sync(_list())
    except Exception as e:
        return [{"error": str(e)}]


async def list_tools_async(url: Optional[str] = None) -> list:
    """
    List all available tools from the MCP server asynchronously.
    """
    url = (
        url
        or os.environ.get("PATHWAY_MCP_URL")
        or os.environ.get("MCP_URL")
        or "http://localhost:8123/mcp/"
    )

    try:
        from fastmcp import Client

        client = Client(url)
        async with client:
            return await client.list_tools()
    except Exception as e:
        return [{"error": str(e)}]


# ============================================================================
# CLI Interface for testing
# ============================================================================

if __name__ == "__main__":
    import sys

    print("MCP Client - Forex Tools")
    print("=" * 50)

    # Default URL
    url = os.environ.get("PATHWAY_MCP_URL", "http://localhost:8123/mcp/")
    print(f"Server URL: {url}\n")

    # List available tools
    print("Available tools:")
    tools = list_tools_sync(url)
    for tool in tools:
        if isinstance(tool, dict) and "error" in tool:
            print(f"  Error: {tool['error']}")
        else:
            name = getattr(tool, "name", None) or tool.get("name", "unknown")
            desc = getattr(tool, "description", None) or tool.get("description", "")
            print(f"  - {name}: {desc[:60]}...")

    print("\n" + "=" * 50)

    # Test each tool
    test_pairs = ["EURUSD", "GBPUSD"]

    print(f"\nTesting tools with pairs: {test_pairs}\n")

    tools_to_test = [
        ("get_trades_summary", {"pairs": test_pairs}),
        ("get_position_details", {"pairs": test_pairs}),
        ("get_currency_regime", {"pairs": test_pairs}),
        ("get_currency_correlation", {"pairs": test_pairs}),
        ("get_news_sentiment", {"pairs": ["EURUSD"]}),  # Test with single pair
    ]

    for tool_name, args in tools_to_test:
        print(f"\n{'=' * 50}")
        print(f"Tool: {tool_name}")
        print(f"Args: {args}")
        print("-" * 50)

        result = call_tool_sync(tool_name, args, url)

        # Print first 500 chars to avoid flooding terminal
        if len(result) > 500:
            print(result[:500] + "\n... [truncated]")
        else:
            print(result)
