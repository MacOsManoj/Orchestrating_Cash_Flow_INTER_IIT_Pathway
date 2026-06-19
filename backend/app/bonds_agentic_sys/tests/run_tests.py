"""
Test Runner Script
Run all agent tests using mock data
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

import unittest
from test_agents_comprehensive import (
    TestMLModelAgent,
    TestQueryClassifierAgent,
    TestAnalystAgent,
    TestScoringAgent,
    TestAdvisoryAgent,
    TestExplainabilityAgent,
    TestPlannerAgent,
    TestPortfolioManager,
    TestPipelineIntegration,
)

# Note: E2E test is run separately as it requires async execution
# Run with: python tests/test_pipeline_e2e.py


def run_all_tests():
    """Run all test suites"""
    print("=" * 70)
    print("BOND PIPELINE - COMPREHENSIVE AGENT TEST SUITE")
    print("=" * 70)
    print(f"Project Root: {project_root}")
    print(f"Mock Data: {project_root / 'files-mock'}")
    print("=" * 70)
    print()

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    test_classes = [
        ("ML Model Agent", TestMLModelAgent),
        ("Query Classifier Agent", TestQueryClassifierAgent),
        ("Analyst Agent", TestAnalystAgent),
        ("Scoring Agent", TestScoringAgent),
        ("Advisory Agent", TestAdvisoryAgent),
        ("Explainability Agent", TestExplainabilityAgent),
        ("Planner Agent", TestPlannerAgent),
        ("Portfolio Manager", TestPortfolioManager),
        ("Pipeline Integration", TestPipelineIntegration),
    ]

    for name, test_class in test_classes:
        print(f"Adding {name} tests...")
        suite.addTests(loader.loadTestsFromTestCase(test_class))

    print(f"\nTotal test cases: {suite.countTestCases()}")
    print("=" * 70)
    print()

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)

    # Print summary
    print()
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(
        f"Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%"
    )
    print("=" * 70)

    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"\n{test}:")
            print(traceback)

    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"\n{test}:")
            print(traceback)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
