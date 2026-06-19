"""
Portfolio Update Parser Agent
Parses natural language queries to extract portfolio update commands
"""

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any, Optional, List
import json
import re
from dotenv import load_dotenv

load_dotenv()


class PortfolioUpdateCommand:
    """Structured portfolio update command"""

    def __init__(self, **kwargs):
        self.action = kwargs.get("action", "")  # 'add', 'update', 'remove'
        self.isin = kwargs.get("isin", "")
        self.bond_name = kwargs.get("bond_name", "")
        self.quantity = kwargs.get("quantity", None)
        self.current_price = kwargs.get("current_price", None)
        self.avg_cost = kwargs.get("avg_cost", None)
        self.updates = kwargs.get("updates", {})  # For update action
        self.confidence = kwargs.get("confidence", 0.8)
        self.reasoning = kwargs.get("reasoning", "")


class PortfolioUpdateParserAgent:
    """
    Parses natural language queries to extract portfolio update commands
    """

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

        self.parser_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are an expert at parsing portfolio update COMMANDS from natural language queries.

**CRITICAL: Distinguish between QUESTIONS and COMMANDS**

**QUESTIONS (NOT portfolio update commands):**
- "What are the best bonds for my portfolio?" → NOT a command, return action: null
- "Which bonds should I buy?" → NOT a command, return action: null
- "Recommend bonds for my portfolio" → NOT a command, return action: null
- "What bonds can I buy?" → NOT a command, return action: null
- Any query starting with "what", "which", "how", "should", "can", "recommend", "suggest" → NOT a command

**COMMANDS (portfolio update commands):**
- "Add 1000 units of HDFC bond to my portfolio" → IS a command
- "Update quantity of INE001A01036 to 1500000" → IS a command
- "Remove SBI bond from my portfolio" → IS a command

Your task is to extract structured information about portfolio updates from user queries ONLY if they are commands.

Actions you can detect:
1. ADD: User wants to add a new bond to their portfolio
   - Keywords: "add", "buy", "purchase", "include", "new position"
   - Required: isin (or bond_name), quantity, current_price (or avg_cost)
   - Must be a COMMAND, not a question
   
2. UPDATE: User wants to update an existing bond's information
   - Keywords: "update", "change", "modify", "set", "adjust"
   - Required: isin (or bond_name), and at least one field to update (quantity, current_price, avg_cost)
   - Must be a COMMAND, not a question
   
3. REMOVE: User wants to remove a bond from their portfolio
   - Keywords: "remove", "delete", "sell all", "exit", "drop"
   - Required: isin (or bond_name)
   - Must be a COMMAND, not a question

Extract information:
- ISIN: Look for ISIN codes (e.g., "INE001A01036", "IN0020230010")
- Bond name: Company/bond names (e.g., "HDFC Bank 7.50% 2025", "SBI bond", "Government bond")
- Quantity: Numbers with units like "1000", "1.5M", "1500000", "1 lakh"
- Price: Numbers with currency or price context (e.g., "₹101.5", "98.5", "at 100")
- Average cost: Similar to price, but look for "cost", "purchase price", "bought at"

Handle variations:
- "1 lakh" = 100,000
- "1 crore" = 10,000,000
- "1M" or "1 million" = 1,000,000
- "1K" or "1 thousand" = 1,000
- Prices can be in rupees (₹) or without currency symbol

Output JSON format:
{{
    "action": "add" | "update" | "remove",
    "isin": "INE001A01036" or "",
    "bond_name": "HDFC Bank 7.50% 2025" or "",
    "quantity": 1000.0 or null,
    "current_price": 101.5 or null,
    "avg_cost": 100.0 or null,
    "updates": {{
        "quantity": 1000.0,
        "current_price": 101.5,
        "avg_cost": 100.0,
        "name": "Updated Bond Name"
    }},
    "confidence": 0.9,
    "reasoning": "User wants to add HDFC Bank bond with 1000 units at price 101.5"
}}

**If the query is a QUESTION (not a command), return:**
{{
    "action": null,
    "isin": "",
    "bond_name": "",
    "quantity": null,
    "current_price": null,
    "avg_cost": null,
    "updates": {{}},
    "confidence": 0.0,
    "reasoning": "Query is a question/recommendation request, not a portfolio update command"
}}

**Examples of queries that should return action: null:**
- "What are the best PSU bonds for my portfolio?" → action: null (question)
- "Which bonds should I buy?" → action: null (question)
- "Recommend bonds for my portfolio" → action: null (recommendation request)
- "What other bonds can I buy?" → action: null (question)

**Examples of queries that should return an action:**
- "Add 1000 units of HDFC bond at price 101.5" → action: "add"
- "Update quantity of INE001A01036 to 1500000" → action: "update"
- "Remove SBI bond from portfolio" → action: "remove" """,
                ),
                (
                    "user",
                    """Query: {query}

Current Portfolio Holdings (if available):
{portfolio_info}

**IMPORTANT:** First determine if this is a COMMAND (action to perform) or a QUESTION (asking for recommendations/information). 
- If it's a QUESTION (starts with "what", "which", "how", "should", "can", "recommend", "suggest"), return action: null
- If it's a COMMAND (direct instruction to add/update/remove), extract the action and required fields.""",
                ),
            ]
        )

    def parse(
        self, query: str, portfolio_info: Optional[str] = None
    ) -> PortfolioUpdateCommand:
        """
        Parse a natural language query to extract portfolio update command

        Args:
            query: User's natural language query
            portfolio_info: Optional string describing current portfolio holdings

        Returns:
            PortfolioUpdateCommand object with extracted information
        """
        try:
            # First try LLM-based parsing
            response = self.llm.invoke(
                self.parser_prompt.format_messages(
                    query=query,
                    portfolio_info=portfolio_info
                    or "No portfolio information available",
                )
            )

            content = response.content.strip()

            # Try to extract JSON from response
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
            else:
                # Fallback to keyword-based parsing
                data = self._keyword_parse(query)

            return PortfolioUpdateCommand(**data)

        except Exception as e:
            print(f"Error parsing portfolio update command: {e}")
            # Fallback to keyword-based parsing
            return PortfolioUpdateCommand(**self._keyword_parse(query))

    def _keyword_parse(self, query: str) -> Dict[str, Any]:
        """Fallback keyword-based parsing"""
        query_lower = query.lower()

        # Detect action
        action = None
        if any(
            kw in query_lower
            for kw in ["add", "buy", "purchase", "include", "new position"]
        ):
            action = "add"
        elif any(
            kw in query_lower for kw in ["update", "change", "modify", "set", "adjust"]
        ):
            action = "update"
        elif any(
            kw in query_lower for kw in ["remove", "delete", "sell all", "exit", "drop"]
        ):
            action = "remove"

        if not action:
            return {
                "action": None,
                "isin": "",
                "bond_name": "",
                "quantity": None,
                "current_price": None,
                "avg_cost": None,
                "updates": {},
                "confidence": 0.0,
                "reasoning": "Query is not a portfolio update command",
            }

        # Extract ISIN
        isin_pattern = r"IN[E0-9]{10,12}"
        isin_match = re.search(isin_pattern, query, re.IGNORECASE)
        isin = isin_match.group(0) if isin_match else ""

        # Extract bond name (look for company names or bond descriptions)
        bond_name = ""
        common_companies = [
            "hdfc",
            "sbi",
            "axis",
            "icici",
            "pnb",
            "bob",
            "canara",
            "union",
            "indian bank",
        ]
        for company in common_companies:
            if company in query_lower:
                # Try to extract full bond name
                pattern = rf"{company}[^.]*?(?:\d+\.\d+%)?[^.]*?(?:\d{{4}})?"
                match = re.search(pattern, query, re.IGNORECASE)
                if match:
                    bond_name = match.group(0).strip()
                    break

        # Extract quantity
        quantity = None
        quantity_patterns = [
            r"(\d+(?:\.\d+)?)\s*(?:lakh|crore|million|M|K|thousand)",
            r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:units|shares|bonds)?",
            r"(\d+(?:\.\d+)?)\s*(?:units|shares|bonds)",
            r"quantity[:\s]+(\d+(?:,\d{3})*(?:\.\d+)?)",
        ]
        for pattern in quantity_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                qty_str = match.group(1).replace(",", "")
                quantity = float(qty_str)
                # Handle lakh, crore, etc.
                if "lakh" in match.group(0).lower():
                    quantity *= 100000
                elif "crore" in match.group(0).lower():
                    quantity *= 10000000
                elif "million" in match.group(0).lower() or "M" in match.group(0):
                    quantity *= 1000000
                elif "K" in match.group(0) or "thousand" in match.group(0).lower():
                    quantity *= 1000
                break

        # Extract price
        current_price = None
        price_patterns = [
            r"(?:price|at|₹|Rs\.?)\s*(\d+(?:\.\d+)?)",
            r"(\d+(?:\.\d+)?)\s*(?:rupees?|₹|Rs\.?)",
        ]
        for pattern in price_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                current_price = float(match.group(1))
                break

        # Extract average cost
        avg_cost = None
        cost_patterns = [
            r"(?:cost|purchase|bought|avg)\s*(?:price|at|₹|Rs\.?)?\s*(\d+(?:\.\d+)?)",
            r"(\d+(?:\.\d+)?)\s*(?:cost|purchase price)",
        ]
        for pattern in cost_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                avg_cost = float(match.group(1))
                break

        # Build updates dict for update action
        updates = {}
        if action == "update":
            if quantity is not None:
                updates["quantity"] = quantity
            if current_price is not None:
                updates["current_price"] = current_price
            if avg_cost is not None:
                updates["avg_cost"] = avg_cost
            if bond_name:
                updates["name"] = bond_name

        return {
            "action": action,
            "isin": isin,
            "bond_name": bond_name,
            "quantity": quantity,
            "current_price": current_price,
            "avg_cost": avg_cost,
            "updates": updates,
            "confidence": 0.7,  # Lower confidence for keyword parsing
            "reasoning": f"Parsed {action} action from query",
        }


def create_portfolio_update_parser(
    llm: Optional[ChatOpenAI] = None,
) -> PortfolioUpdateParserAgent:
    """Factory function to create PortfolioUpdateParserAgent"""
    if llm is None:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
    return PortfolioUpdateParserAgent(llm)
