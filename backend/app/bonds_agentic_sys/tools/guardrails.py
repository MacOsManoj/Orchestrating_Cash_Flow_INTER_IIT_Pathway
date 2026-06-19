"""
Guardrails Module using Llama Guard 4-12B
Provides input and output safety checks using Groq's Llama Guard model
"""

from typing import Optional, Dict, Any, Tuple
from enum import Enum
import os
from dotenv import load_dotenv

load_dotenv()

try:
    from groq import Groq

    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    Groq = None


class SafetyLevel(str, Enum):
    """Safety check result levels"""

    SAFE = "safe"
    UNSAFE = "unsafe"
    UNCERTAIN = "uncertain"


class GuardrailsResult:
    """Result from guardrails check"""

    def __init__(
        self,
        is_safe: bool,
        safety_level: SafetyLevel,
        reason: Optional[str] = None,
        categories: Optional[list] = None,
    ):
        self.is_safe = is_safe
        self.safety_level = safety_level
        self.reason = reason or ""
        self.categories = categories or []


class GuardrailsChecker:
    """
    Guardrails checker using Llama Guard 4-12B via Groq
    """

    def __init__(self, api_key: Optional[str] = None, enabled: bool = True):
        """
        Initialize guardrails checker

        Args:
            api_key: Groq API key (defaults to GROQ_API_KEY env var)
            enabled: Whether guardrails are enabled
        """
        self.enabled = enabled
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = "meta-llama/llama-guard-4-12b"

        if not enabled:
            self.client = None
            return

        if not GROQ_AVAILABLE:
            print("Warning: Groq library not available. Install with: pip install groq")
            self.client = None
            self.enabled = False
            return

        if not self.api_key:
            print("Warning: GROQ_API_KEY not set. Guardrails disabled.")
            self.client = None
            self.enabled = False
            return

        try:
            self.client = Groq(api_key=self.api_key)
        except Exception as e:
            print(f"Warning: Failed to initialize Groq client: {e}")
            self.client = None
            self.enabled = False

    def check_input(self, user_query: str) -> GuardrailsResult:
        """
        Check if user input is safe

        Args:
            user_query: User's query text

        Returns:
            GuardrailsResult indicating if input is safe
        """
        if not self.enabled or not self.client:
            return GuardrailsResult(
                is_safe=True,
                safety_level=SafetyLevel.SAFE,
                reason="Guardrails disabled",
            )

        try:
            # Use Llama Guard to check input
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": user_query}],
                temperature=0.0,
                max_tokens=100,
            )

            response = completion.choices[0].message.content.strip().upper()

            # Parse Llama Guard response
            # Typically returns "SAFE" or "UNSAFE" with categories
            is_safe = "UNSAFE" not in response and "SAFE" in response

            if is_safe:
                return GuardrailsResult(
                    is_safe=True,
                    safety_level=SafetyLevel.SAFE,
                    reason="Input passed safety check",
                )
            else:
                # Extract categories if present
                categories = []
                if "CATEGORY" in response or "VIOLENCE" in response:
                    categories.append("violence")
                if "HATE" in response or "DISCRIMINATION" in response:
                    categories.append("hate_speech")
                if "SEXUAL" in response:
                    categories.append("sexual_content")
                if "HARASSMENT" in response:
                    categories.append("harassment")
                if "SELF_HARM" in response or "SUICIDE" in response:
                    categories.append("self_harm")
                if "ILLEGAL" in response or "CRIMINAL" in response:
                    categories.append("illegal_activity")

                return GuardrailsResult(
                    is_safe=False,
                    safety_level=SafetyLevel.UNSAFE,
                    reason=response,
                    categories=categories,
                )

        except Exception as e:
            print(f"Guardrails check error: {e}")
            # On error, allow through but log warning
            return GuardrailsResult(
                is_safe=True,
                safety_level=SafetyLevel.UNCERTAIN,
                reason=f"Guardrails check failed: {str(e)}",
            )

    def check_output(self, output_text: str) -> GuardrailsResult:
        """
        Check if AI output is safe

        Args:
            output_text: AI-generated output text

        Returns:
            GuardrailsResult indicating if output is safe
        """
        if not self.enabled or not self.client:
            return GuardrailsResult(
                is_safe=True,
                safety_level=SafetyLevel.SAFE,
                reason="Guardrails disabled",
            )

        try:
            # Use Llama Guard to check output
            # Format as a conversation to check both user and assistant messages
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a safety checker. Evaluate if the following assistant response is safe and appropriate.",
                    },
                    {"role": "user", "content": output_text},
                ],
                temperature=0.0,
                max_tokens=100,
            )

            response = completion.choices[0].message.content.strip().upper()

            # Parse Llama Guard response
            is_safe = "UNSAFE" not in response and "SAFE" in response

            if is_safe:
                return GuardrailsResult(
                    is_safe=True,
                    safety_level=SafetyLevel.SAFE,
                    reason="Output passed safety check",
                )
            else:
                categories = []
                if "VIOLENCE" in response:
                    categories.append("violence")
                if "HATE" in response:
                    categories.append("hate_speech")
                if "SEXUAL" in response:
                    categories.append("sexual_content")
                if "HARASSMENT" in response:
                    categories.append("harassment")
                if "SELF_HARM" in response:
                    categories.append("self_harm")
                if "ILLEGAL" in response:
                    categories.append("illegal_activity")
                if "FINANCIAL_ADVICE" in response or "INVESTMENT_ADVICE" in response:
                    # For bond trading, we might want to flag unauthorized financial advice
                    categories.append("unauthorized_advice")

                return GuardrailsResult(
                    is_safe=False,
                    safety_level=SafetyLevel.UNSAFE,
                    reason=response,
                    categories=categories,
                )

        except Exception as e:
            print(f"Guardrails output check error: {e}")
            # On error, allow through but log warning
            return GuardrailsResult(
                is_safe=True,
                safety_level=SafetyLevel.UNCERTAIN,
                reason=f"Guardrails check failed: {str(e)}",
            )

    def check_both(
        self, user_query: str, output_text: str
    ) -> Tuple[GuardrailsResult, GuardrailsResult]:
        """
        Check both input and output

        Args:
            user_query: User's query
            output_text: AI output

        Returns:
            Tuple of (input_result, output_result)
        """
        input_result = self.check_input(user_query)
        output_result = self.check_output(output_text)
        return input_result, output_result


def create_guardrails_checker(
    api_key: Optional[str] = None, enabled: bool = True
) -> GuardrailsChecker:
    """Factory function"""
    return GuardrailsChecker(api_key=api_key, enabled=enabled)
