"""
State validation and access helpers for GraphState
Reduces repetitive .get() calls and adds validation
"""

from typing import Dict, Any, Optional, TypeVar, Type

T = TypeVar("T")


class StateHelper:
    """Helper class for safe state access and validation"""

    @staticmethod
    def get(
        state: Dict[str, Any],
        key: str,
        default: Any = None,
        required: bool = False,
        expected_type: Optional[Type[T]] = None,
    ) -> Any:
        """
        Safely get a value from state with optional validation

        Args:
            state: GraphState dictionary
            key: Key to retrieve
            default: Default value if key not found
            required: If True, raise ValueError if key is missing
            expected_type: Expected type for validation

        Returns:
            Value from state or default

        Raises:
            ValueError: If required key is missing or type mismatch
        """
        value = state.get(key, default)

        if required and value is None and default is None:
            raise ValueError(f"Required state key '{key}' is missing")

        if expected_type and value is not None and not isinstance(value, expected_type):
            raise TypeError(
                f"State key '{key}' has type {type(value).__name__}, "
                f"expected {expected_type.__name__}"
            )

        return value

    @staticmethod
    def get_list(
        state: Dict[str, Any],
        key: str,
        default: Optional[list] = None,
        min_length: Optional[int] = None,
    ) -> list:
        """
        Get a list from state with validation

        Args:
            state: GraphState dictionary
            key: Key to retrieve
            default: Default value (empty list if None)
            min_length: Minimum required length

        Returns:
            List from state

        Raises:
            ValueError: If value is not a list or too short
        """
        if default is None:
            default = []

        value = state.get(key, default)

        if not isinstance(value, list):
            raise TypeError(
                f"State key '{key}' is not a list, got {type(value).__name__}"
            )

        if min_length is not None and len(value) < min_length:
            raise ValueError(
                f"State key '{key}' has length {len(value)}, "
                f"minimum required: {min_length}"
            )

        return value

    @staticmethod
    def get_dict(
        state: Dict[str, Any],
        key: str,
        default: Optional[dict] = None,
        required_keys: Optional[list] = None,
    ) -> dict:
        """
        Get a dictionary from state with validation

        Args:
            state: GraphState dictionary
            key: Key to retrieve
            default: Default value (empty dict if None)
            required_keys: List of required keys in the dict

        Returns:
            Dictionary from state

        Raises:
            ValueError: If value is not a dict or missing required keys
        """
        if default is None:
            default = {}

        value = state.get(key, default)

        if not isinstance(value, dict):
            raise TypeError(
                f"State key '{key}' is not a dict, got {type(value).__name__}"
            )

        if required_keys:
            missing = [k for k in required_keys if k not in value]
            if missing:
                raise ValueError(f"State key '{key}' missing required keys: {missing}")

        return value

    @staticmethod
    def ensure_list(state: Dict[str, Any], key: str) -> list:
        """Ensure a key exists as a list, creating it if missing"""
        if key not in state or state[key] is None:
            state[key] = []
        elif not isinstance(state[key], list):
            state[key] = [state[key]]
        return state[key]

    @staticmethod
    def ensure_dict(state: Dict[str, Any], key: str) -> dict:
        """Ensure a key exists as a dict, creating it if missing"""
        if key not in state or state[key] is None:
            state[key] = {}
        elif not isinstance(state[key], dict):
            state[key] = {}
        return state[key]

    @staticmethod
    def has_data(state: Dict[str, Any], key: str) -> bool:
        """Check if a key exists and has non-empty data"""
        value = state.get(key)
        if value is None:
            return False
        if isinstance(value, (list, dict, str)):
            return len(value) > 0
        return True
