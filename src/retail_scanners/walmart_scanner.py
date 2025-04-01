"""
Walmart scanner module for retrieving clearance and discounted products
"""

import os
import logging
import json
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
import time
import random

from .base_scanner import RetailScanner, RetailProduct

logger = logging.getLogger(__name__)

class WalmartScanner(RetailScanner):
    """Scanner for Walmart website to find clearance and discounted products"""
    
    BASE_URL = "https://www.walmart.com"
    SEARCH_URL = f"{BASE_URL}/browse/deals/clearance"
    API_URL = "https://www.walmart.com/orchestra/home/graphql"
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.store = "Walmart"
        
        # Additional headers for Walmart
        self.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Referer': 'https://www.walmart.com/browse/deals/clearance',
        })
        self.session.headers.update(self.headers)
    
    def search_clearance(self, category: Optional[str] = None, limit: int = 50) -> List[RetailProduct]:
        """Search for clearance products in the given category"""
        logger.info(f"Searching Walmart clearance products in category: {category or 'all'}")
        
        url = self.SEARCH_URL
        if category:
            url += f"/{category}"
        
        products = []
        page = 1
        
        while len(products) < limit:
            try:
                page_url = f"{url}?page={page}"
                response = self.session.get(page_url)
                self._handle_request_error(response, "Walmart clearance search")
                
                soup = BeautifulSoup(response.text, 'html.parser')
                product_elements = soup.select('div[data-item-id]')
                
                if not product_elements:
                    break
                
                for element in product_elements:
                    try:
                        product_id = element.get('data-item-id')
                        if not product_id:
                            continue
                        
                        # Extract product data
                        title_elem = element.select_one('span.product-title-link')
                        title = title_elem.text.strip() if title_elem else "Unknown Product"
                        
                        price_elem = element.select_one('span.price-main')
                        price_text = price_elem.text.strip() if price_elem else "0"
                        price = float(price_text.replace('$', '').replace(',', ''))
                        
                        original_price_elem = element.select_one('span.price-was')
                        original_price = None
                        if original_price_elem:
                            original_price_text = original_price_elem.text.strip().replace('$', '').replace(',', '')
                            try:
                                original_price = float(original_price_text)
                            except ValueError:
                                pass
                        
                        url = f"{self.BASE_URL}/ip/{product_id}"
                        
                        image_elem = element.select_one('img')
                        image_url = image_elem.get('src') if image_elem else ""
                        
                        product = RetailProduct(
                            product_id=product_id,
                            title=title,
                            price=price,
                            original_price=original_price,
                            url=url,
                            image_url=image_url,
                            store=self.store
                        )
                        
                        products.append(product)
                        
                        if len(products) >= limit:
                            break
                    
                    except Exception as e:
                        logger.error(f"Error parsing Walmart product: {e}")
                
                page += 1
                # Add a small delay to avoid rate limiting
                time.sleep(random.uniform(1.0, 2.0))
                
            except Exception as e:
                logger.error(f"Error during Walmart clearance search: {e}")
                break
        
        logger.info(f"Found {len(products)} Walmart clearance products")
        return products
    
    def search_discounted(self, min_discount: float = 40.0, category: Optional[str] = None, limit: int = 50) -> List[RetailProduct]:
        """Search for discounted products with minimum discount percentage"""
        logger.info(f"Searching Walmart discounted products with min discount: {min_discount}%")
        
        # For Walmart, we'll get clearance products and filter by discount percentage
        all_products = self.search_clearance(category, limit * 2)  # Get more products to filter
        
        # Filter products by discount percentage
        discounted_products = [
            product for product in all_products 
            if product.discount_percentage and product.discount_percentage >= min_discount
        ]
        
        # Limit the number of products
        return discounted_products[:limit]
    
    def get_product_details(self, product_id: str) -> RetailProduct:
        """Get detailed information for a specific product"""
        logger.info(f"Getting Walmart product details for ID: {product_id}")
        
        url = f"{self.BASE_URL}/ip/{product_id}"
        
        try:
            response = self.session.get(url)
            self._handle_request_error(response, "Walmart product details")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract product data
            title_elem = soup.select_one('h1.prod-ProductTitle')
            title = title_elem.text.strip() if title_elem else "Unknown Product"
            
            price_elem = soup.select_one('span.price-characteristic')
            price_fraction_elem = soup.select_one('span.price-mantissa')
            
            price = 0.0
            if price_elem:
                price_whole = price_elem.text.strip()
                price_fraction = price_fraction_elem.text.strip() if price_fraction_elem else "00"
                price = float(f"{price_whole}.{price_fraction}")
            
            original_price_elem = soup.select_one('span.price-was')
            original_price = None
            if original_price_elem:
                original_price_text = original_price_elem.text.strip().replace('$', '').replace(',', '')
                try:
                    original_price = float(original_price_text)
                except ValueError:
                    pass
            
            image_elem = soup.select_one('img.prod-hero-image')
            image_url = image_elem.get('src') if image_elem else ""
            
            # Try to extract UPC/SKU
            upc = None
            sku = None
            
            # Look for product details in script tags
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get('@type') == 'Product':
                        if 'gtin13' in data:
                            upc = data['gtin13']
                        if 'sku' in data:
                            sku = data['sku']
                        break
                except:
                    continue
            
            # Extract description
            description_elem = soup.select_one('div.about-product')
            description = description_elem.text.strip() if description_elem else None
            
            # Extract brand
            brand_elem = soup.select_one('a.prod-brandName')
            brand = brand_elem.text.strip() if brand_elem else None
            
            # Extract category
            category = None
            breadcrumb_elems = soup.select('li.breadcrumb span')
            if breadcrumb_elems and len(breadcrumb_elems) > 1:
                category = breadcrumb_elems[-2].text.strip()
            
            return RetailProduct(
                product_id=product_id,
                title=title,
                price=price,
                original_price=original_price,
                url=url,
                image_url=image_url,
                brand=brand,
                category=category,
                upc=upc,
                sku=sku,
                description=description,
                store=self.store
            )
            
        except Exception as e:
            logger.error(f"Error getting Walmart product details: {e}")
            # Return a minimal product object if details can't be retrieved
            return RetailProduct(
                product_id=product_id,
                title="Unknown Walmart Product",
                price=0.0,
                original_price=None,
                url=url,
                image_url="",
                store=self.store
            )
