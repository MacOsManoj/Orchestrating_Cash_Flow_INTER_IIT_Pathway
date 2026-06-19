"""
Context Manager for Smart Context Sharing
Intelligently formats and shares conversation context with different agents
"""

from typing import List, Dict, Optional, Any
from datetime import datetime


class ContextManager:
    """
    Manages conversation context and formats it appropriately for different agents
    """

    @staticmethod
    def format_context_for_classifier(
        conversation_history: List[Dict[str, str]], max_messages: int = 5
    ) -> str:
        """
        Format context for query classifier
        Focuses on recent queries and intents
        """
        if not conversation_history:
            return ""

        recent = conversation_history[-max_messages:]
        context_parts = []

        for msg in recent:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                context_parts.append(f"Previous user query: {content}")
            elif role == "assistant":
                # Extract key info from assistant responses
                if "recommend" in content.lower() or "buy" in content.lower():
                    context_parts.append(f"Previous recommendation was made")

        return "\n".join(context_parts) if context_parts else ""

    @staticmethod
    def format_context_for_planner(
        conversation_history: List[Dict[str, str]], max_messages: int = 3
    ) -> str:
        """
        Format context for planner
        Focuses on what tools/agents were used previously
        """
        if not conversation_history:
            return ""

        recent = conversation_history[-max_messages:]
        context_parts = ["Previous conversation context:"]

        for msg in recent:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                context_parts.append(f"User asked: {content[:100]}...")

        return "\n".join(context_parts)

    @staticmethod
    def format_context_for_advisory(
        conversation_history: List[Dict[str, str]], max_messages: int = 5
    ) -> str:
        """
        Format context for advisory agent
        Focuses on previous recommendations and user preferences
        """
        if not conversation_history:
            return ""

        recent = conversation_history[-max_messages:]
        context_parts = []

        for msg in recent:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "user":
                # Extract user preferences and constraints
                if any(
                    kw in content.lower() for kw in ["prefer", "like", "want", "need"]
                ):
                    context_parts.append(f"User preference: {content[:150]}")
            elif role == "assistant":
                # Extract previous recommendations
                if (
                    "recommend" in content.lower()
                    or "buy" in content.lower()
                    or "sell" in content.lower()
                ):
                    # Extract bond names/ISINs mentioned
                    context_parts.append(
                        f"Previous recommendation context: {content[:200]}..."
                    )

        return "\n".join(context_parts) if context_parts else ""

    @staticmethod
    def format_context_for_response(
        conversation_history: List[Dict[str, str]], max_messages: int = 10
    ) -> str:
        """
        Format full context for response agent
        Includes full conversation for follow-up questions
        """
        if not conversation_history:
            return "No previous conversation."

        recent = conversation_history[-max_messages:]
        context_parts = []

        for msg in recent:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            role_label = "User" if role == "user" else "Assistant"
            context_parts.append(f"{role_label}: {content}")

        return "\n".join(context_parts)

    @staticmethod
    def extract_relevant_context(
        conversation_history: List[Dict[str, str]],
        current_query: str,
        agent_type: str = "general",
    ) -> str:
        """
        Intelligently extract relevant context based on current query
        """
        if not conversation_history:
            return ""

        query_lower = current_query.lower()

        # Check if this is a follow-up question
        follow_up_keywords = [
            "this",
            "that",
            "these",
            "those",
            "it",
            "they",
            "them",
            "how",
            "why",
            "explain",
            "what about",
            "tell me more",
            "previous",
            "earlier",
            "before",
            "last time",
            "next",
            "best",
            "another",
            "second",
            "third",
            "other",
            "also",
            "more",
            "give me",
            "show me",
            "what else",
            "above",
            "mentioned",
        ]

        is_follow_up = any(kw in query_lower for kw in follow_up_keywords)

        if not is_follow_up:
            # Not a follow-up, return minimal context
            return ContextManager.format_context_for_classifier(
                conversation_history, max_messages=2
            )

        # It's a follow-up, return more context
        if agent_type == "classifier":
            return ContextManager.format_context_for_classifier(
                conversation_history, max_messages=5
            )
        elif agent_type == "planner":
            return ContextManager.format_context_for_planner(
                conversation_history, max_messages=3
            )
        elif agent_type == "advisory":
            return ContextManager.format_context_for_advisory(
                conversation_history, max_messages=5
            )
        elif agent_type == "response":
            return ContextManager.format_context_for_response(
                conversation_history, max_messages=10
            )
        else:
            return ContextManager.format_context_for_response(
                conversation_history, max_messages=5
            )

    @staticmethod
    def get_summary_context(
        conversation_history: List[Dict[str, str]], max_messages: int = 10
    ) -> Dict[str, Any]:
        """
        Get a summary of conversation context for quick reference
        Returns structured summary
        """
        if not conversation_history:
            return {
                "has_history": False,
                "total_messages": 0,
                "recent_topics": [],
                "previous_recommendations": [],
            }

        recent = conversation_history[-max_messages:]

        topics = []
        recommendations = []

        for msg in recent:
            content = msg.get("content", "").lower()
            if msg.get("role") == "user":
                # Extract topics
                if "bond" in content:
                    topics.append("bonds")
                if "portfolio" in content:
                    topics.append("portfolio")
                if "yield" in content or "return" in content:
                    topics.append("yield")
            elif msg.get("role") == "assistant":
                if "recommend" in content or "buy" in content:
                    recommendations.append(content[:100])

        return {
            "has_history": True,
            "total_messages": len(conversation_history),
            "recent_topics": list(set(topics)),
            "previous_recommendations": recommendations[:3],  # Last 3 recommendations
        }

    @staticmethod
    def extract_user_context(
        conversation_history: List[Dict[str, str]], max_messages: int = 20
    ) -> Dict[str, Any]:
        """
        Extract user information from conversation history
        Returns user profile with name, budget, preferences, etc.
        """
        user_context = {
            "name": None,
            "budget": None,
            "investment_goals": [],
            "previous_queries": [],
            "recommendations_received": [],
        }

        if not conversation_history:
            return user_context

        recent = conversation_history[-max_messages:]

        for msg in recent:
            content = msg.get("content", "")
            role = msg.get("role", "")

            if role == "user":
                content_lower = content.lower()

                # Extract name (patterns like "my name is X", "I'm X", "call me X")
                if not user_context["name"]:
                    import re

                    name_patterns = [
                        r"my name is ([A-Z][a-z]+)",
                        r"i'?m ([A-Z][a-z]+)",
                        r"call me ([A-Z][a-z]+)",
                        r"name is ([A-Z][a-z]+)",
                        r"i am ([A-Z][a-z]+)",
                    ]
                    for pattern in name_patterns:
                        match = re.search(pattern, content, re.IGNORECASE)
                        if match:
                            user_context["name"] = match.group(1)
                            break

                # Extract budget (patterns like "Rs. X", "₹X", "X rupees", "budget of X")
                if not user_context["budget"]:
                    budget_patterns = [
                        r"rs\.?\s*([\d,]+)",
                        r"₹\s*([\d,]+)",
                        r"([\d,]+)\s*rupees?",
                        r"budget\s+of\s+rs\.?\s*([\d,]+)",
                        r"i\s+have\s+rs\.?\s*([\d,]+)",
                    ]
                    for pattern in budget_patterns:
                        match = re.search(pattern, content, re.IGNORECASE)
                        if match:
                            budget_str = match.group(1).replace(",", "")
                            try:
                                user_context["budget"] = float(budget_str)
                            except ValueError:
                                pass
                            break

                # Extract investment goals
                if any(
                    word in content_lower
                    for word in ["maximum returns", "max returns", "highest return"]
                ):
                    user_context["investment_goals"].append("maximize_returns")
                if any(
                    word in content_lower for word in ["safe", "low risk", "secure"]
                ):
                    user_context["investment_goals"].append("safety")
                if any(
                    word in content_lower for word in ["diversify", "diversification"]
                ):
                    user_context["investment_goals"].append("diversification")

                # Store previous queries
                user_context["previous_queries"].append(content[:200])

            elif role == "assistant":
                # Extract recommendations from assistant responses
                if "recommend" in content.lower() or "buy" in content.lower():
                    user_context["recommendations_received"].append(content[:300])

        # Keep only recent items
        user_context["previous_queries"] = user_context["previous_queries"][-5:]
        user_context["recommendations_received"] = user_context[
            "recommendations_received"
        ][-3:]

        return user_context


def create_context_manager() -> ContextManager:
    """Factory function"""
    return ContextManager()
