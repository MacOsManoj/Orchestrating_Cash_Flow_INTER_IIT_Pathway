"""
Dynamic Model Selector
Selects appropriate LLM models for each agent based on query complexity
Uses GPT-5 series models with smart routing
"""

from typing import Dict, Optional, Tuple
from enum import Enum
import re


class ModelTier(str, Enum):
    """Model tiers for different complexity levels"""

    NANO = "gpt-5-nano"  # Fastest, simplest tasks
    MINI = "gpt-5-mini"  # Fast, well-defined tasks
    STANDARD = "gpt-5"  # Standard intelligent reasoning
    PRO = "gpt-5-pro"  # Smarter, more precise
    ADVANCED = "gpt-5.1"  # Most advanced for complex tasks
    LEGACY = "gpt-4.1"  # Fallback for non-reasoning needs


class AgentType(str, Enum):
    """Agent types for model selection"""

    QUERY_CLASSIFIER = "query_classifier"
    PLANNER = "planner"
    ADVISORY = "advisory"
    RESPONSE = "response"
    EXPLAINABILITY = "explainability"
    GENERAL = "general"


class ModelSelector:
    """
    Selects appropriate models for each agent based on query complexity
    """

    # Default model mapping for each agent type
    DEFAULT_MODELS = {
        AgentType.QUERY_CLASSIFIER: ModelTier.MINI,  # Fast classification
        AgentType.PLANNER: ModelTier.STANDARD,  # Needs reasoning for planning
        AgentType.ADVISORY: ModelTier.PRO,  # Complex recommendations
        AgentType.RESPONSE: ModelTier.STANDARD,  # Standard responses
        AgentType.EXPLAINABILITY: ModelTier.PRO,  # Complex explanations
        AgentType.GENERAL: ModelTier.MINI,  # General queries
    }

    # Complexity indicators
    SIMPLE_INDICATORS = [
        "what is",
        "what are",
        "show me",
        "list",
        "tell me about",
        "simple",
        "basic",
        "quick",
        "just",
        "only",
    ]

    COMPLEX_INDICATORS = [
        "analyze",
        "compare",
        "strategy",
        "optimize",
        "recommend",
        "explain why",
        "how does",
        "complex",
        "detailed",
        "comprehensive",
        "multiple",
        "portfolio",
        "rebalance",
        "barbell",
        "hedge",
    ]

    VERY_COMPLEX_INDICATORS = [
        "multi-step",
        "sophisticated",
        "advanced",
        "deep analysis",
        "comprehensive strategy",
        "optimize portfolio",
        "risk analysis",
    ]

    def __init__(self, base_model: str = "gpt-5"):
        """
        Initialize model selector

        Args:
            base_model: Base model to use (will be adjusted per agent)
        """
        self.base_model = base_model
        self.complexity_cache: Dict[str, str] = {}  # Cache complexity assessments

    def assess_complexity(self, query: str, agent_type: AgentType) -> str:
        """
        Assess query complexity and return appropriate model tier

        Args:
            query: User query
            agent_type: Type of agent that will process this

        Returns:
            Model tier string
        """
        # Check cache first
        cache_key = f"{agent_type.value}:{query[:50]}"
        if cache_key in self.complexity_cache:
            return self.complexity_cache[cache_key]

        query_lower = query.lower()

        # Count complexity indicators
        simple_count = sum(
            1 for indicator in self.SIMPLE_INDICATORS if indicator in query_lower
        )
        complex_count = sum(
            1 for indicator in self.COMPLEX_INDICATORS if indicator in query_lower
        )
        very_complex_count = sum(
            1 for indicator in self.VERY_COMPLEX_INDICATORS if indicator in query_lower
        )

        # Query length as complexity indicator
        word_count = len(query.split())
        is_long_query = word_count > 20

        # Determine complexity level
        if very_complex_count > 0 or (complex_count >= 2 and is_long_query):
            complexity = "very_complex"
        elif complex_count > 0 or is_long_query:
            complexity = "complex"
        elif simple_count > 0 and word_count < 10:
            complexity = "simple"
        else:
            complexity = "medium"

        # Select model based on agent type and complexity
        model = self._select_model(agent_type, complexity)

        # Cache result
        self.complexity_cache[cache_key] = model

        return model

    def _select_model(self, agent_type: AgentType, complexity: str) -> str:
        """
        Select model for agent type and complexity

        Args:
            agent_type: Type of agent
            complexity: Complexity level (simple, medium, complex, very_complex)

        Returns:
            Model name string
        """
        # Agent-specific model selection logic
        if agent_type == AgentType.QUERY_CLASSIFIER:
            # Classification is usually fast - use mini/nano
            if complexity == "simple":
                return ModelTier.NANO.value
            elif complexity == "medium":
                return ModelTier.MINI.value
            else:
                return (
                    ModelTier.MINI.value
                )  # Even complex queries, classification is quick

        elif agent_type == AgentType.PLANNER:
            # Planning needs reasoning
            if complexity == "simple":
                return ModelTier.MINI.value
            elif complexity == "medium":
                return ModelTier.STANDARD.value
            elif complexity == "complex":
                return ModelTier.STANDARD.value
            else:
                return ModelTier.PRO.value

        elif agent_type == AgentType.ADVISORY:
            # Recommendations need smart reasoning
            if complexity == "simple":
                return ModelTier.STANDARD.value
            elif complexity == "medium":
                return ModelTier.PRO.value
            elif complexity == "complex":
                return ModelTier.PRO.value
            else:
                return ModelTier.ADVANCED.value

        elif agent_type == AgentType.RESPONSE:
            # Response generation
            if complexity == "simple":
                return ModelTier.MINI.value
            elif complexity == "medium":
                return ModelTier.STANDARD.value
            elif complexity == "complex":
                return ModelTier.STANDARD.value
            else:
                return ModelTier.PRO.value

        elif agent_type == AgentType.EXPLAINABILITY:
            # Explanations need precision
            if complexity == "simple":
                return ModelTier.STANDARD.value
            elif complexity == "medium":
                return ModelTier.PRO.value
            else:
                return ModelTier.PRO.value

        elif agent_type == AgentType.GENERAL:
            # General queries
            if complexity == "simple":
                return ModelTier.NANO.value
            elif complexity == "medium":
                return ModelTier.MINI.value
            else:
                return ModelTier.STANDARD.value

        # Default fallback
        return self.DEFAULT_MODELS[agent_type].value

    def get_model_for_agent(
        self,
        agent_type: AgentType,
        query: Optional[str] = None,
        force_model: Optional[str] = None,
    ) -> str:
        """
        Get model for specific agent

        Args:
            agent_type: Type of agent
            query: Optional query for complexity assessment
            force_model: Optional model to force (overrides selection)

        Returns:
            Model name string
        """
        if force_model:
            return force_model

        if query:
            return self.assess_complexity(query, agent_type)

        # Return default for agent type
        return self.DEFAULT_MODELS[agent_type].value

    def clear_cache(self):
        """Clear complexity cache"""
        self.complexity_cache.clear()


def create_model_selector(base_model: str = "gpt-5") -> ModelSelector:
    """Factory function"""
    return ModelSelector(base_model)
