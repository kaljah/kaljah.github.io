import math

class BaseCalculator:
    """
    Base class for all API Compendium 2021 calculation modules.
    Provides common validation and formatting methods.
    """
    def __init__(self, name, section_ref):
        self.name = name
        self.section_ref = section_ref

    def validate_inputs(self, inputs, required_keys):
        """Validates that all required inputs are present and non-negative."""
        for key in required_keys:
            if key not in inputs:
                raise ValueError(f"Missing required input: {key}")
            if isinstance(inputs[key], (int, float)) and inputs[key] < 0:
                raise ValueError(f"Input {key} cannot be negative: {inputs[key]}")
        return True

    def calculate_uncertainty(self, value, relative_uncertainty):
        """
        Calculates absolute uncertainty and non-negative bounds at 95% CI.
        """
        abs_uncertainty = value * relative_uncertainty
        return {
            "value": value,
            "uncertainty": relative_uncertainty,
            "abs_uncertainty": abs_uncertainty,
            "lower_bound": max(0.0, value - abs_uncertainty),
            "upper_bound": value + abs_uncertainty
        }

    def format_result(self, co2=None, ch4=None, n2o=None, total_co2e=None, inputs=None, metadata=None):
        """Formats the final calculation result into a standard structure."""
        return {
            "method": self.name,
            "api_reference": self.section_ref,
            "inputs": inputs or {},
            "total_co2e": total_co2e,
            "results": {
                "co2": co2,
                "ch4": ch4,
                "n2o": n2o,
                "total_co2e": total_co2e
            },
            "metadata": metadata or {}
        }
