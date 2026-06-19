"""
Agent Bond V2 - Main Demo Script
Tests all features: Planner, RAG, Tools, Conditional Explainability
"""
import asyncio
import os
from datetime import datetime

from schemas_v2 import SystemConfigV2, NewsArticle
from rag.rag_system import create_rag_system
from orchestrator_v2 import create_orchestrator_v2
from dotenv import load_dotenv
load_dotenv()


async def setup_rag_demo_data(rag):
    """
    Index some demo data into RAG
    """
    print("\n" + "=" * 80)
    print("Setting up RAG with demo data...")
    print("=" * 80)

    # Index sample news
    news_articles = [
        NewsArticle(
            title="RBI holds repo rate at 6.5%, maintains hawkish stance",
            url="https://example.com/rbi-rate-decision",
            source="Economic Times",
            content="The Reserve Bank of India kept the repo rate unchanged at 6.5% citing persistent inflation concerns. The MPC voted 5-1 to maintain rates while remaining focused on withdrawal of accommodation.",
            sentiment_score=0.2,
            relevance_score=0.95,
            entities=["RBI", "repo rate", "inflation"],
            published_at=datetime.now(),
        ),
        NewsArticle(
            title="Bond yields surge after CPI data shows sticky inflation",
            url="https://example.com/bond-yields-surge",
            source="Moneycontrol",
            content="Government bond yields jumped sharply following higher-than-expected CPI inflation of 4.87%, up from 4.70% expectations. The 10-year benchmark yield rose 8 basis points to 7.18%.",
            sentiment_score=-0.3,
            relevance_score=0.90,
            entities=["bonds", "yields", "CPI", "inflation"],
            published_at=datetime.now(),
        ),
        NewsArticle(
            title="HDFC Bank raises $1B through bond issuance",
            url="https://example.com/hdfc-bond-issuance",
            source="Business Standard",
            content="HDFC Bank successfully raised $1 billion through a bond issuance with strong investor demand. The AAA-rated bonds were priced at 7.4% for 5-year tenor.",
            sentiment_score=0.6,
            relevance_score=0.85,
            entities=["HDFC Bank", "bonds", "AAA"],
            published_at=datetime.now(),
        ),
    ]

    for article in news_articles:
        doc_id = rag.index_news_article(article)
        print(f"   Indexed: {article.title[:60]}... (ID: {doc_id[:8]})")

    print(f"\n Indexed {len(news_articles)} news articles")

    # Show RAG stats
    stats = rag.get_collection_stats()
    print(f"\nRAG Statistics:")
    for collection, data in stats.items():
        print(f"  - {collection}: {data['count']} documents")

    print("=" * 80 + "\n")


async def run_demo_query(orchestrator, query_num, query, user_id="demo_user"):
    """
    Run a single demo query
    """
    print(f"\n{'=' * 80}")
    print(f"QUERY {query_num}: {query}")
    print(f"{'=' * 80}")

    start_time = datetime.now()

    # Run query
    result = await orchestrator.run_async(query=query, user_id=user_id)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Display results
    print(f"\nRESULTS:")
    print(f"  Processing Time: {duration:.2f}s")
    print(f"  Plan:")
    if result.execution_plan:
        print(
            f"     - Tools: {[t.tool_type.value for t in result.execution_plan.tools_needed]}"
        )
        print(
            f"     - Agents: {[a.value for a in result.execution_plan.agents_needed]}"
        )
        print(f"     - Explainability: {result.execution_plan.needs_explainability}")
        print(f"     - Reasoning: {result.execution_plan.reasoning}")

    print(f"  💾 Cache Hits: {result.cache_hits}/{result.total_tool_calls}")

    if result.advisory and result.advisory.recommendations:
        print(f"\n  RECOMMENDATIONS ({len(result.advisory.recommendations)}):")
        for i, rec in enumerate(result.advisory.recommendations[:3], 1):
            print(f"     {i}. {rec.action}: {rec.name}")
            print(f"        Rationale: {rec.rationale[:100]}...")
            print(f"        Expected Return: {rec.expected_return:.2%}")
            print(f"        Confidence: {rec.confidence:.2%}")
    if result.explanations:
        print(f"\n  EXPLANATIONS ({len(result.explanations)}):")
        for i, exp in enumerate(result.explanations[:1], 1):
            print(f"     {i}. {exp.explanation_text[:200]}...")
            print(f"        Top Positive Factors:")
            for factor in exp.top_positive_factors[:3]:
                print(f"          {factor}")
            print(f"        Top Negative Factors:")
            for factor in exp.top_negative_factors[:3]:
                print(f"          {factor}")

    print(f"\n{'=' * 80}\n")

    return result


async def main():
    """
    Main demo function
    """
    print(f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║                          AGENT BOND V2 DEMO                            ║
║                                                                               ║
║                    Production-Grade Multi-Agent System                        ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)

    # Check API keys
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        print("   Please set: export OPENAI_API_KEY='sk-...'")
        return

    serpapi_key = os.getenv("SERPAPI_KEY")
    if not serpapi_key:
        print("Warning: SERPAPI_KEY not set (web search disabled)")
        print("   Set: export SERPAPI_KEY='...' to enable")

    # Configuration
    config = SystemConfigV2(
        openai_api_key=api_key,
        serpapi_key=serpapi_key,
        rag_enabled=True,
        cache_enabled=True,
        enable_pathway_forecasts=False,  # Set to True if you have yield CSV files
        llm_model="gpt-4-turbo-preview",
        llm_temperature=0.0,
    )

    print(f"\nConfiguration:")
    print(f"   - LLM: {config.llm_model}")
    print(f"   - RAG: {'Enabled' if config.rag_enabled else 'Disabled'}")
    print(f"   - Cache: {'Enabled' if config.cache_enabled else 'Disabled'}")
    print(
        f"   - Pathway Forecasts: {'Enabled' if config.enable_pathway_forecasts else 'Disabled'}"
    )

    # Initialize RAG
    print(f"\nInitializing RAG system...")
    rag = create_rag_system(config)

    # Index demo data
    await setup_rag_demo_data(rag)

    # Initialize orchestrator
    print(f"Initializing Orchestrator V2...")
    orchestrator = create_orchestrator_v2(config, rag)

    print(f"\nSystem ready!\n")

    # Demo queries showing different features
    queries = [
        # Query 1: Simple (no explainability)
        "Find AAA bonds with good yields",
        # Query 2: With RBI context (uses RAG)
        "Given recent RBI hawkish stance, recommend defensive bonds",
        # Query 3: Explanation request (conditional explainability)
        "Explain why HDFC Bank bonds are recommended",
        # Query 4: Duration reduction (specific strategy)
        "My portfolio has too much interest rate risk, suggest low duration alternatives",
        # Query 5: Complex (multiple features)
        "Find high-yield PSU bonds that will outperform if yield curve flattens",
    ]

    results = []

    for i, query in enumerate(queries, 1):
        result = await run_demo_query(orchestrator, i, query)
        results.append(result)

        # Small delay between queries
        if i < len(queries):
            await asyncio.sleep(1)

    # Summary
    print(f"\n{'=' * 80}")
    print(f"DEMO SUMMARY")
    print(f"{'=' * 80}")

    total_time = sum(r.processing_time for r in results)
    total_cache_hits = sum(r.cache_hits for r in results)
    total_tool_calls = sum(r.total_tool_calls for r in results)

    print(f"\nQueries Processed: {len(results)}")
    print(f"Total Time: {total_time:.2f}s")
    print(f"Average Time: {total_time / len(results):.2f}s per query")
    print(
        f"Cache Hit Rate: {total_cache_hits}/{total_tool_calls} ({total_cache_hits / max(total_tool_calls, 1) * 100:.1f}%)"
    )

    print(f"\nPerformance vs V1:")
    v1_avg_time = 23  # V1 average from docs
    speedup = v1_avg_time / (total_time / len(results))
    print(f"   Speedup: {speedup:.1f}x faster")
    print(f"   Time saved: {v1_avg_time - (total_time / len(results)):.1f}s per query")

    # Feature showcase
    print(f"\nFeatures Demonstrated:")
    features = [
        (" Intelligent Planner", "Decides what tools and agents to use"),
        (" Conditional Explainability", "Only runs when user asks"),
        (" RAG System", "Semantic search for RBI policies and news"),
        (" Smart Caching", f"{total_cache_hits} cache hits saved time"),
        (" Multi-Strategy", "Handles 5 different query types"),
        (" Production-Grade", "Ready for real deployment"),
    ]

    for feature, description in features:
        print(f"   {feature:30} {description}")

    print(f"\n{'=' * 80}")
    print(f"Agent Bond V2 Demo Complete!")
    print(f"{'=' * 80}\n")

    # Next steps
    print(f"Next Steps:")
    print(f"   1. Index real data into RAG (CRISIL docs, RBI policies)")
    print(f"   2. Enable Pathway forecasts (add yield CSV files)")
    print(f"   3. Connect to real NSE bond data")
    print(f"   4. Deploy with FastAPI")
    print(f"   5. Add monitoring and logging")
    print(f"\nDocumentation:")
    print(f"   - README_V2.md - Full system guide")
    print(f"   - QUICK_START.md - 15-minute setup")
    print(f"   - ARCHITECTURE_DIAGRAM.md - 9 Mermaid diagrams")
    print(f"\n")


if __name__ == "__main__":
    asyncio.run(main())
