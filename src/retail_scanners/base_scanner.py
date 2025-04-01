"""
Base scanner module for retail websites
Provides common functionality for all retail scanners
"""

import logging
import requests
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RetailProduct:
    """Data class to store retail product information"""
    product_id: str
    title: str
    price: float
    original_price: Optional[float]
    url: str
    image_url: str
    brand: Optional[str] = None
    category: Optional[str] = None
    upc: Optional[str] = None
    sku: Optional[str] = None
    description: Optional[str] = None
    store: str = ""
    
    @property
    def discount_percentage(self) -> Optional[float]:
        """Calculate discount percentage if original price is available"""
        if self.original_price and self.original_price > 0:
            return round(((self.original_price - self.price) / self.original_price) * 100, 2)
        return None

class RetailScanner(ABC):
    """Base class for retail website scanners"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        if api_key:
            self.headers['Authorization'] = f'Bearer {api_key}'
        self.session.headers.update(self.headers)
    
    @abstractmethod
    def search_clearance(self, category: Optional[str] = None, limit: int = 50) -> List[RetailProduct]:
        """Search for clearance products in the given category"""
        pass
    
    @abstractmethod
    def search_discounted(self, min_discount: float = 40.0, category: Optional[str] = None, limit: int = 50) -> List[RetailProduct]:
        """Search for discounted products with minimum discount percentage"""
        pass
    
    @abstractmethod
    def get_product_details(self, product_id: str) -> RetailProduct:
        """Get detailed information for a specific product"""
        pass
    
    def _handle_request_error(self, response: requests.Response, context: str):
        """Handle request errors with proper logging"""
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error during {context}: {e}")
            logger.debug(f"Response content: {response.text[:500]}...")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error during {context}: {e}")
            raise
