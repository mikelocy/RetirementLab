"""
Helper utilities for test cleanup.
This module provides functions to identify and clean up test scenarios
while preserving user-created scenarios.
"""
from sqlmodel import Session, text, select
from backend.models import Scenario, Asset, IncomeSource


def is_test_scenario(scenario_name: str) -> bool:
    """
    Determine if a scenario name indicates it's an automated test scenario.
    Only deletes scenarios that clearly look like automated tests (with timestamps
    or specific test prefixes), not user scenarios that might contain "test" in the name.
    """
    name_lower = scenario_name.lower()
    
    # Check for specific automated test patterns (must match exactly or with timestamp)
    automated_test_patterns = [
        'export test',
        'imported copy',
        'tax sim test',
        'roth test',
        'comprehensive tax test',
        'filing status test',
        'ss low income test',
        'ss high income test',
    ]
    
    # Check if name starts with or contains these specific test patterns
    for pattern in automated_test_patterns:
        if pattern in name_lower:
            return True
    
    # Check for timestamp patterns (ISO format dates) combined with "test"
    # This catches scenarios like "Test 2025-12-01T15:03:13.627748"
    has_timestamp = '2025-' in scenario_name or '2024-' in scenario_name or '2026-' in scenario_name
    has_test_keyword = 'test' in name_lower
    
    # Only consider it a test if it has BOTH a timestamp AND "test" keyword
    # OR if it's a very long name with timestamp (likely auto-generated)
    if has_timestamp and (has_test_keyword or len(scenario_name) > 40):
        return True
    
    # Simple "Test" followed by timestamp (e.g., "Test 2025-12-01T...")
    if name_lower.startswith('test ') and has_timestamp:
        return True
    
    return False


def cleanup_test_scenarios(session: Session):
    """
    Delete all test scenarios and their associated data (assets, income sources).
    Preserves non-test scenarios.
    """
    # Find all test scenarios
    all_scenarios = session.exec(select(Scenario)).all()
    test_scenario_ids = []
    
    for scenario in all_scenarios:
        if is_test_scenario(scenario.name):
            test_scenario_ids.append(scenario.id)
    
    if not test_scenario_ids:
        return 0
    
    # Delete in correct order (foreign key constraints)
    deleted_count = 0
    
    # Delete income sources
    for scenario_id in test_scenario_ids:
        session.exec(text("DELETE FROM incomesource WHERE scenario_id = :id").bindparams(id=scenario_id))
    
    # Delete assets (this will cascade to detail tables via foreign keys)
    for scenario_id in test_scenario_ids:
        session.exec(text("DELETE FROM asset WHERE scenario_id = :id").bindparams(id=scenario_id))
    
    # Delete scenarios
    for scenario_id in test_scenario_ids:
        session.exec(text("DELETE FROM scenario WHERE id = :id").bindparams(id=scenario_id))
        deleted_count += 1
    
    session.commit()
    return deleted_count

