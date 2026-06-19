"""
Agent Logger - Pretty formatted output for agent messages
Provides colored, structured terminal output for agent activities
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import json


class Colors:
    """ANSI color codes for terminal output"""

    # Agent colors
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"

    # Styles
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    DIM = "\033[2m"

    # Reset
    END = "\033[0m"

    # Agent-specific colors
    AGENT_COLORS = {
        "query_classifier": CYAN,
        "realtime_info": MAGENTA,
        "planner": BLUE,
        "ml_model": YELLOW,
        "analyst": GREEN,
        "scoring": CYAN,
        "advisory": GREEN,
        "response": BLUE,
        "explainability": YELLOW,
    }


class AgentLogger:
    """Formatted logger for agent outputs"""

    @staticmethod
    def _get_agent_color(agent_name: str) -> str:
        """Get color for agent"""
        agent_lower = agent_name.lower().replace(" ", "_")
        for key, color in Colors.AGENT_COLORS.items():
            if key in agent_lower:
                return color
        return Colors.CYAN

    @staticmethod
    def print_agent_header(agent_name: str, action: str = "RUNNING"):
        """Print agent header"""
        color = AgentLogger._get_agent_color(agent_name)
        print(f"\n{Colors.BOLD}{color}{'=' * 80}{Colors.END}")
        print(f"{Colors.BOLD}{color}{agent_name.upper()}: {action}{Colors.END}")
        print(f"{Colors.BOLD}{color}{'=' * 80}{Colors.END}\n")

    @staticmethod
    def print_agent_output(agent_name: str, output: Any, title: str = "Output"):
        """Print agent output in formatted box"""
        color = AgentLogger._get_agent_color(agent_name)

        # Convert output to string if needed
        if isinstance(output, dict):
            output_str = json.dumps(output, indent=2, default=str)
        elif hasattr(output, "__dict__"):
            output_str = json.dumps(output.__dict__, indent=2, default=str)
        else:
            output_str = str(output)

        # Truncate if too long
        if len(output_str) > 500:
            output_str = output_str[:500] + "\n... (truncated)"

        print(
            f"{color}┌─ {title} ─────────────────────────────────────────────────────────────{Colors.END}"
        )
        for line in output_str.split("\n"):
            print(f"{color}│ {Colors.END}{line}")
        print(
            f"{color}└───────────────────────────────────────────────────────────────────────{Colors.END}\n"
        )

    @staticmethod
    def print_agent_result(agent_name: str, result: Any, summary: Optional[str] = None):
        """Print agent result with summary"""
        color = AgentLogger._get_agent_color(agent_name)

        if summary:
            print(f"{color} {summary}{Colors.END}")

        if result:
            if isinstance(result, dict):
                # Print key metrics
                for key, value in list(result.items())[:5]:  # Top 5 items
                    if isinstance(value, (int, float)):
                        print(f"  {Colors.DIM}• {key}:{Colors.END} {value}")
                    elif isinstance(value, str) and len(value) < 100:
                        print(f"  {Colors.DIM}• {key}:{Colors.END} {value}")
            elif hasattr(result, "__dict__"):
                # Print object attributes
                attrs = {
                    k: v for k, v in result.__dict__.items() if not k.startswith("_")
                }
                for key, value in list(attrs.items())[:5]:
                    if isinstance(value, (int, float)):
                        print(f"  {Colors.DIM}• {key}:{Colors.END} {value}")
                    elif isinstance(value, str) and len(value) < 100:
                        print(f"  {Colors.DIM}• {key}:{Colors.END} {value}")

        print()  # Empty line

    @staticmethod
    def print_recommendations(recommendations: List[Any], agent_name: str = "Advisory"):
        """Print recommendations in formatted table"""
        if not recommendations:
            print(f"{Colors.YELLOW}Info: No recommendations generated{Colors.END}\n")
            return

        color = AgentLogger._get_agent_color(agent_name)
        print(
            f"{color}┌─ RECOMMENDATIONS ────────────────────────────────────────────────────{Colors.END}"
        )

        for idx, rec in enumerate(recommendations[:10], 1):  # Top 10
            action = getattr(rec, "action", "N/A")
            name = getattr(rec, "name", "N/A")
            isin = getattr(rec, "isin", "N/A")
            confidence = getattr(rec, "confidence", 0)
            expected_return = getattr(rec, "expected_return", 0)

            # Color code action
            action_color = (
                Colors.GREEN
                if action == "BUY"
                else Colors.RED
                if action == "SELL"
                else Colors.YELLOW
            )

            print(
                f"{color}│ {Colors.END}{idx}. {action_color}{action}{Colors.END}: {name}"
            )
            print(f"{color}│ {Colors.END}   ISIN: {isin}")
            print(
                f"{color}│ {Colors.END}   Confidence: {confidence:.1%} | Expected Return: {expected_return:.1%}"
            )
            if hasattr(rec, "rationale") and rec.rationale:
                rationale = (
                    rec.rationale[:80] + "..."
                    if len(rec.rationale) > 80
                    else rec.rationale
                )
                print(f"{color}│ {Colors.END}   Rationale: {rationale}")
            print(f"{color}│{Colors.END}")

        if len(recommendations) > 10:
            print(f"{color}│ {Colors.END}... and {len(recommendations) - 10} more")

        print(
            f"{color}└───────────────────────────────────────────────────────────────────────{Colors.END}\n"
        )

    @staticmethod
    def print_summary(summary: str, agent_name: str = "Advisory"):
        """Print summary in formatted box"""
        if not summary:
            return

        color = AgentLogger._get_agent_color(agent_name)

        # Truncate if too long
        summary_lines = summary.split("\n")
        if len(summary_lines) > 10:
            summary_lines = summary_lines[:10] + ["... (truncated)"]

        print(
            f"{color}┌─ SUMMARY ─────────────────────────────────────────────────────────────{Colors.END}"
        )
        for line in summary_lines:
            # Wrap long lines
            if len(line) > 75:
                words = line.split(" ")
                current_line = ""
                for word in words:
                    if len(current_line + word) > 75:
                        print(f"{color}│ {Colors.END}{current_line}")
                        current_line = word + " "
                    else:
                        current_line += word + " "
                if current_line:
                    print(f"{color}│ {Colors.END}{current_line}")
            else:
                print(f"{color}│ {Colors.END}{line}")
        print(
            f"{color}└───────────────────────────────────────────────────────────────────────{Colors.END}\n"
        )

    @staticmethod
    def print_info(message: str, agent_name: Optional[str] = None):
        """Print info message"""
        if agent_name:
            color = AgentLogger._get_agent_color(agent_name)
            print(f"{color}Info: {message}{Colors.END}")
        else:
            print(f"{Colors.CYAN}Info: {message}{Colors.END}")

    @staticmethod
    def print_success(message: str, agent_name: Optional[str] = None):
        """Print success message"""
        if agent_name:
            color = AgentLogger._get_agent_color(agent_name)
            print(f"{color}Success: {message}{Colors.END}")
        else:
            print(f"{Colors.GREEN}Success: {message}{Colors.END}")

    @staticmethod
    def print_warning(message: str, agent_name: Optional[str] = None):
        """Print warning message"""
        print(f"{Colors.YELLOW}Warning: {message}{Colors.END}")

    @staticmethod
    def print_error(message: str, agent_name: Optional[str] = None):
        """Print error message"""
        print(f"{Colors.RED}Error: {message}{Colors.END}")

    @staticmethod
    def print_metrics(metrics: Dict[str, Any], agent_name: str):
        """Print metrics in formatted table"""
        color = AgentLogger._get_agent_color(agent_name)
        print(
            f"{color}┌─ METRICS ─────────────────────────────────────────────────────────────{Colors.END}"
        )
        for key, value in metrics.items():
            if isinstance(value, float):
                print(f"{color}│ {Colors.END}{key}: {value:.2f}")
            elif isinstance(value, int):
                print(f"{color}│ {Colors.END}{key}: {value}")
            else:
                print(f"{color}│ {Colors.END}{key}: {value}")
        print(
            f"{color}└───────────────────────────────────────────────────────────────────────{Colors.END}\n"
        )

    @staticmethod
    def print_step(step: str, status: str = "running"):
        """Print execution step"""
        if status == "running":
            print(f"{Colors.DIM}→ {step}...{Colors.END}")
        elif status == "done":
            print(f"{Colors.GREEN}Success: {step}{Colors.END}")
        elif status == "error":
            print(f"{Colors.RED}Error: {step}{Colors.END}")
