

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
        """Validates that all required inputs are present, finite, and non-negative."""
        for key in required_keys:
            if key not in inputs:
                raise ValueError(f"Missing required input: {key}")
            val = inputs[key]
            if isinstance(val, (int, float)):
                if math.isnan(val) or math.isinf(val):
                    raise ValueError(f"Input {key} cannot be NaN or Infinite: {val}")
                if val < 0:
                    raise ValueError(f"Input {key} cannot be negative: {val}")
        return True

    def calculate_uncertainty(self, value, relative_uncertainty, coverage_factor=2.0):
        """
        Calculates absolute uncertainty and non-negative bounds at 95% CI (k=2.0 per ISO/IEC Guide 98-3 GUM §6.2).
        """
        abs_1sigma = value * relative_uncertainty
        abs_95 = abs_1sigma * coverage_factor
        return {
            "value": value,
            "uncertainty": relative_uncertainty,
            "abs_uncertainty": abs_1sigma,
            "abs_uncertainty_95": abs_95,
            "lower_bound": max(0.0, value - abs_95),
            "upper_bound": value + abs_95,
            "confidence_level_pct": 95,
            "coverage_factor": coverage_factor,
        }

    def format_result(
        self, co2=None, ch4=None, n2o=None, total_co2e=None, inputs=None, metadata=None
    ):
        """Formats the final calculation result into a standard structure."""
        return {
            "method": self.name,
            "api_reference": self.section_ref,
            "inputs": inputs or {},
            "total_co2e": total_co2e if total_co2e is not None else 0.0,
            "results": {
                "co2": co2 if co2 is not None else 0.0,
                "ch4": ch4 if ch4 is not None else 0.0,
                "n2o": n2o if n2o is not None else 0.0,
                "total_co2e": total_co2e if total_co2e is not None else 0.0,
            },
            "metadata": metadata or {},
        }
