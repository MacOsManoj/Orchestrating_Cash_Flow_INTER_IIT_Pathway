"""
Planner Agent - Intelligently decides execution strategy
Refactored to use JSON configuration for tools and agents
"""

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any, Optional, List
import json
import os
from pydantic import SecretStr

from schemas_v2 import ExecutionPlan, ToolType, AgentType, DataSource, ToolCall
from dotenv import load_dotenv

load_dotenv()


class PlannerAgent:
    """
    High-level planner that creates an adaptive execution strategy based on dynamic configuration.
    """

    def __init__(self, llm: ChatOpenAI, config_path: str):
        self.llm = llm
        self.config = self._load_config(config_path)
        self.planning_prompt = self._create_planning_prompt()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Loads the planner configuration from a JSON file."""
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading planner config: {e}")
            # Fallback to an empty config
            return {"tools": [], "agents": [], "planning_rules": []}

    def _format_tools_description(self) -> str:
        """Formats tools from config into a comprehensive description."""
        tools = self.config.get("tools", [])

        # Group tools by category
        categories = {}
        for tool in tools:
            category = tool.get("category", "other")
            if category not in categories:
                categories[category] = []
            categories[category].append(tool)

        # Build formatted description
        description_parts = []

        category_titles = {
            "yield_analytics": "YIELD ANALYTICS (MCP Server - Real-Time Data)",
            "bond_discovery": "BOND DISCOVERY (MCP Server - Real-Time Data)",
            "bond_valuation": "BOND VALUATION (MCP Server - Real-Time Data)",
            "bond_analysis": "BOND ANALYSIS (MCP Server - Real-Time Data)",
            "external_data": "EXTERNAL DATA SOURCES",
            "portfolio": "PORTFOLIO MANAGEMENT",
            "knowledge": "KNOWLEDGE BASE",
        }

        for category, tools_list in sorted(categories.items()):
            title = category_titles.get(category, category.upper())
            description_parts.append(f"\n=== {title} ===\n")

            for idx, tool in enumerate(tools_list, 1):
                # Tool name and aliases
                tool_names = [tool["name"]]
                if "aliases" in tool:
                    tool_names.extend(tool["aliases"])
                tool_header = f"{idx}. {' or '.join(tool_names)}"

                # Add parameters if any
                if tool.get("parameters"):
                    params = ", ".join([p["name"] for p in tool["parameters"]])
                    tool_header += f"({params})"

                description_parts.append(tool_header)

                # Add key information
                desc_lines = [f"   • {tool['description']}"]

                # Add special notes
                if tool.get("notes"):
                    desc_lines.append(f"   •  {tool['notes']}")

                if not tool.get("requires_agents", False):
                    desc_lines.append(
                        "   •  INFORMATION ONLY - NO agents needed for this tool"
                    )
                elif tool.get("required_agents"):
                    agents = ", ".join(tool["required_agents"])
                    desc_lines.append(f"   • Requires agents: [{agents}]")

                # Add conditional agent logic
                if tool.get("conditional_agents"):
                    desc_lines.append(f"   • {tool['conditional_agents']}")

                # Add parameters details
                if tool.get("parameters"):
                    desc_lines.append("   • Parameters:")
                    for param in tool["parameters"]:
                        param_desc = f"     - {param['name']}: {param.get('description', 'No description')}"
                        if not param.get("required", False):
                            default = param.get("default", "None")
                            param_desc += f" (optional, default: {default})"
                        desc_lines.append(param_desc)

                # Add trigger phrases
                if tool.get("trigger_phrases"):
                    phrases = tool["trigger_phrases"][:5]  # Limit to 5 for brevity
                    desc_lines.append(
                        f"   • Trigger phrases: {', '.join([f'"{p}"' for p in phrases])}"
                    )

                # Add examples
                if tool.get("examples"):
                    desc_lines.append("   • Examples:")
                    for example in tool["examples"][:3]:  # Limit to 3
                        desc_lines.append(f'      "{example}" → Use THIS tool')

                description_parts.append("\n".join(desc_lines))
                description_parts.append("")  # Empty line between tools

        return "\n".join(description_parts)

    def _format_agents_description(self) -> str:
        """Formats agents from config into a description."""
        agents = self.config.get("agents", [])

        description_parts = []
        for idx, agent in enumerate(agents, 1):
            agent_desc = f"{idx}. **{agent['name']}** ({agent['type']})"
            description_parts.append(agent_desc)
            description_parts.append(f"   • {agent['description']}")

            if agent.get("capabilities"):
                caps = ", ".join(agent["capabilities"][:4])  # Limit capabilities
                description_parts.append(f"   • Capabilities: {caps}")

            if agent.get("required_for"):
                required = ", ".join(agent["required_for"])
                description_parts.append(f"   • Required for: {required}")

            if agent.get("trigger_phrases"):
                phrases = ", ".join([f'"{p}"' for p in agent["trigger_phrases"][:3]])
                description_parts.append(f"   • Trigger phrases: {phrases}")

            description_parts.append("")  # Empty line

        return "\n".join(description_parts)

    def _format_planning_rules(self) -> str:
        """Formats planning rules from config."""
        rules = self.config.get("planning_rules", [])

        rules_parts = []
        for idx, rule in enumerate(rules, 1):
            rules_parts.append(
                f"{idx}. **{rule['rule'].upper()}**: {rule['description']}"
            )

            if rule.get("examples"):
                rules_parts.append("   Examples:")
                for example in rule["examples"][:3]:  # Limit examples
                    query = example["query"]
                    tools = ", ".join(example["tools"])
                    agents = (
                        ", ".join(example["agents"]) if example["agents"] else "NONE"
                    )
                    rules_parts.append(
                        f'   • "{query}" → tools: [{tools}], agents: [{agents}]'
                    )

            rules_parts.append("")

        return "\n".join(rules_parts)

    def _create_planning_prompt(self) -> ChatPromptTemplate:
        """Creates the planning prompt using configuration."""

        tools_description = self._format_tools_description()
        agents_description = self._format_agents_description()
        planning_rules = self._format_planning_rules()

        system_prompt = (
            """You are an expert system planner for a bond trading AI system. Your job is to analyze a user query and create an execution plan by selecting from the available tools and agents.

**Available Tools:**
"""
            + tools_description
            + """

**Available Agents:**
"""
            + agents_description
            + """

**Key Planning Rules:**
"""
            + planning_rules
            + """

**Additional Key Rules for Planning:**
1.  **Be Efficient:** Only select the components absolutely necessary to answer the user's query. Do not add extra tools or agents.
2.  **Explainability is Rare:** The 'explainability' agent is expensive and slow. Only use it if the user explicitly asks for a reason, using words like "why", "explain", "rationale", or "reasoning".
3.  **Check Portfolio Context:** Only use the 'portfolio_manager' tool if the query contains phrases like "my portfolio", "my bonds", "my holdings", or is clearly asking about their personal investments.
4.  **Use RAG for Deep Knowledge:** Use the 'rag_retriever' for queries about specific documents, historical analysis, or RBI policies.
5.  **News Queries:** ALWAYS use 'news_scraper' tool if the query asks for news, latest updates, recent developments, current events, or mentions words like "news", "latest", "recent", "update", "current", "today", "breaking". Extract relevant keywords from the query (e.g., company names, state names, bond types) for the news scraper.
6.  **Logical Agent Sequence:** Agents should follow a logical flow. A typical sequence is: `query_classifier` -> `ml_model` -> `analyst` -> `scoring` -> `advisory`. You can skip agents in the sequence if they are not needed. For example, a simple query might only need `query_classifier` and `advisory`.
7.  **Parameterize Tools:** When you select a tool, provide relevant parameters based on the query. For example, `news_scraper` should have `keywords` extracted from the query (e.g., ["Telangana", "bonds", "state bonds"] for "latest news on Telangana bonds").

**Output Format:**
CRITICAL: You MUST respond with valid JSON format only. Your response must be a JSON object with this structure:
{{
    "tools_needed": [
        {{
            "tool_type": "tool_name",
            "parameters": {{}},
            "priority": 1
        }}
    ],
    "agents_needed": ["agent1", "agent2"],
    "needs_explainability": false,
    "reasoning": "explanation"
}}

Return ONLY valid JSON. No additional text before or after the JSON object."""
        )

        return ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                (
                    "user",
                    "Query: {query}\n\nCreate the optimal execution plan. Decide which tools are needed based on the query content, not on whether a portfolio exists.",
                ),
            ]
        )

    def create_plan(
        self,
        query: str,
        has_portfolio: bool = False,  # Deprecated - planner decides based on query
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> ExecutionPlan:
        """
        Create execution plan for a query.
        Planner decides which tools are needed based on query content.
        """
        messages = self.planning_prompt.format_messages(query=query)

        response = self.llm.invoke(messages)

        try:
            content = response.content
            # The response might be wrapped in markdown
            if isinstance(content, str) and content.startswith("```json"):
                content = content.strip("```json\n").strip("```")

            plan_dict = json.loads(content)
        except (json.JSONDecodeError, TypeError) as e:
            print(
                f"Error parsing LLM response for plan: {e}. Falling back to default plan."
            )
            plan_dict = self._default_plan(query)

        # Convert to ExecutionPlan - filter out invalid tool types
        tools_needed = []
        for tool_spec in plan_dict.get("tools_needed", []):
            tool_type_str = tool_spec.get("tool_type", "")
            try:
                # Only add if it's a valid ToolType (not an AgentType)
                tool_type = ToolType(tool_type_str)
                tools_needed.append(
                    ToolCall(
                        tool_type=tool_type,
                        parameters=tool_spec.get("parameters", {}),
                        priority=tool_spec.get("priority", 1),
                    )
                )
            except (ValueError, KeyError):
                # Skip invalid tool types (might be agent names that LLM confused)
                print(f"Warning: Skipping invalid tool type: {tool_type_str}")
                continue

        # Filter out invalid agent types
        agents_needed = []
        for agent_name in plan_dict.get("agents_needed", []):
            try:
                agents_needed.append(AgentType(agent_name))
            except (ValueError, KeyError):
                print(f"Warning: Skipping invalid agent type: {agent_name}")
                continue

        # Determine data sources from tools
        data_sources = self._infer_data_sources(tools_needed)

        plan = ExecutionPlan(
            plan_id=f"plan_{hash(query) % 10000}",
            query=query,
            intent=plan_dict.get("intent", "custom"),
            tools_needed=tools_needed,
            agents_needed=agents_needed,
            data_sources=list(data_sources),
            needs_explainability=plan_dict.get("needs_explainability", False),
            needs_rag="rag_retriever" in [t.tool_type.value for t in tools_needed],
            needs_portfolio_access="portfolio_manager"
            in [t.tool_type.value for t in tools_needed],
            reasoning=plan_dict.get("reasoning", "No reasoning provided."),
        )

        return plan

    def _infer_data_sources(self, tools: list[ToolCall]) -> set[DataSource]:
        """Infers the required data sources based on the tools being called."""
        sources = {DataSource.NSE}  # Always assume NSE as a base
        tool_map = {
            ToolType.NEWS_SCRAPER: DataSource.NEWS,
            ToolType.CRISIL_SCRAPER: DataSource.CRISIL,
            ToolType.PORTFOLIO_MANAGER: DataSource.USER_PORTFOLIO,
            ToolType.RAG_RETRIEVER: DataSource.RAG_STORE,
        }
        for tool in tools:
            if tool.tool_type in tool_map:
                sources.add(tool_map[tool.tool_type])
        return sources

    def _default_plan(self, query: str) -> Dict:
        """
        Create a simple, robust default plan if the LLM fails.
        This is a fallback and should be used sparingly.
        """
        tools = [
            {
                "tool_type": "news_scraper",
                "parameters": {
                    "keywords": ["bonds", "interest rates"],
                    "hours_back": 48,
                },
            }
        ]
        agents = ["query_classifier", "analyst", "scoring", "advisory"]

        # Simple keyword checks for critical functions
        if any(kw in query.lower() for kw in ["why", "explain", "reason"]):
            agents.append("explainability")
        if any(kw in query.lower() for kw in ["my portfolio", "my holdings"]):
            tools.append({"tool_type": "portfolio_manager", "parameters": {}})

        return {
            "tools_needed": tools,
            "agents_needed": agents,
            "needs_explainability": "explainability" in agents,
            "reasoning": "Default fallback plan executed due to a planning error.",
        }


def create_planner_agent(
    api_key: str, model: str = "gpt-4-turbo-preview", config_path: Optional[str] = None
) -> PlannerAgent:
    """Factory function for the PlannerAgent."""
    llm = ChatOpenAI(
        model=model,
        temperature=0.0,
        api_key=api_key,
        model_kwargs={"response_format": {"type": "json_object"}},
    )

    # Use provided config path or construct default path
    if config_path is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, "..", "config", "planner_config.json")

    return PlannerAgent(llm=llm, config_path=config_path)
