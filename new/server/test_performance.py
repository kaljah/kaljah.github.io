import pytest
from calculations.uncertainty import propagate_uncertainty

# Micro-benchmark for uncertainty calculation engine
# This function handles the complex error propagation math that runs on every emission save.

def test_benchmark_uncertainty_propagation(benchmark):
    # Setup test data typical of a Scope 1 record
    base_emissions = 50000.0
    tier = 2
    # The engine expects (value, ef_uncertainty, activity_uncertainty, tier, process_category)
    # We will benchmark standard combustion error propagation
    result = benchmark(propagate_uncertainty, base_emissions, 0.05, 0.02, tier, "combustion")
    
    assert "ci_95_abs" in result
