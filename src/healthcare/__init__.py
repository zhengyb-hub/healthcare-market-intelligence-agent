"""Healthcare IT data foundation exposed to the Streamlit application."""

from .bootstrap import (
    bootstrap_data_foundation,
    bootstrap_market_intelligence,
    bootstrap_product_workflow,
)
from .database import Database
from .services import DataFoundationService, EvidenceService, VendorService

__version__ = "1.1.0"

__all__ = [
    "Database",
    "DataFoundationService",
    "EvidenceService",
    "VendorService",
    "bootstrap_data_foundation",
    "bootstrap_market_intelligence",
    "bootstrap_product_workflow",
    "__version__",
]
