"""
Emission Factors Package
Re-exports everything from root emission_factors.py and exposes submodules like eeio_factors.
"""
import os
import importlib.util
from .eeio_factors import EEIO_FACTORS, get_eeio_factor

_root_ef_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "emission_factors.py"))
if os.path.exists(_root_ef_file):
    _spec = importlib.util.spec_from_file_location("_root_ef", _root_ef_file)
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    for _k, _v in _mod.__dict__.items():
        if not _k.startswith("__"):
            globals()[_k] = _v
