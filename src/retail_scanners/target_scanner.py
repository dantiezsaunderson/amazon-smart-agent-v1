"""
Target scanner module for retrieving clearance and discounted products
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

class TargetScanner(RetailScanner):
    """Scanner for Target website to find clearance and discounted products"""
    
    BASE_URL = "https://www.target.com"
    SEARCH_URL = f"{BASE_URL}/c/clearance/-/N-5q0ga"
    API_URL = "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v1"
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.store = "Target"
        
        # Additional headers for Target
        self.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Referer': 'https://www.target.com/c/clearance/-/N-5q0ga',
        })
        self.session.headers.update(self.headers)
    
    def search_clearance(self, category: Optional[str] = None, limit: int = 50) -> List[RetailProduct]:
        """Search for clearance products in the given category"""
        logger.info(f"Searching Target clearance products in category: {category or 'all'}")
        
        url = self.SEARCH_URL
        if category:
            # Target uses category IDs, but for simplicity we'll just append the category name
            url = f"{self.BASE_URL}/c/clearance-{category}/-/N-5q0ga"
        
        products = []
        page = 1
        
        while len(products) < limit:
            try:
                page_url = f"{url}?lnk=snav_rd_clearance&Nao={(page-1)*24}"
                response = self.session.get(page_url)
                self._handle_request_error(response, "Target clearance search")
                
                soup = BeautifulSoup(response.text, 'html.parser')
                product_elements = soup.select('li[data-test="product-list-item"]')
                
                if not product_elements:
                    break
                
                for element in product_elements:
                    try:
                        # Extract product ID from the URL
                        link_elem = element.select_one('a[data-test="product-link"]')
                        if not link_elem:
                            continue
                            
                        product_url = link_elem.get('href', '')
                        if not product_url.startswith('/'):
                            product_url = '/' + product_url
                            
                        product_id = product_url.split('/')[-1]
                        if not product_id:
                            continue
                        
                        # Extract product data
                        title_elem = element.select_one('a[data-test="product-link"]')
                        title = title_elem.text.strip() if title_elem else "Unknown Product"
                        
                        price_elem = element.select_one('span[data-test="current-price"]')
                        price_text = price_elem.text.strip() if price_elem else "$0.00"
                        price = float(price_text.replace('$', '').replace(',', ''))
                        
                        original_price_elem = element.select_one('span[data-test="original-price"]')
                        original_price = None
                        if original_price_elem:
                            original_price_text = original_price_elem.text.strip().replace('$', '').replace(',', '')
                            try:
                                original_price = float(original_price_text)
                            except ValueError:
                                pass
                        
                        full_url = f"{self.BASE_URL}{product_url}"
                        
                        image_elem = element.select_one('img')
                        image_url = image_elem.get('src') if image_elem else ""
                        
                        product = RetailProduct(
                            product_id=product_id,
                            title=title,
                            price=price,
                            original_price=original_price,
                            url=full_url,
                            image_url=image_url,
                            store=self.store
                        )
                        
                        products.append(product)
                        
                        if len(products) >= limit:
                            break
                    
                    except Exception as e:
                        logger.error(f"Error parsing Target product: {e}")
                
                page += 1
                # Add a small delay to avoid rate limiting
                time.sleep(random.uniform(1.0, 2.0))
                
            except Exception as e:
                logger.error(f"Error during Target clearance search: {e}")
                break
        
        logger.info(f"Found {len(products)} Target clearance products")
        return products
    
    def search_discounted(self, min_discount: float = 40.0, category: Optional[str] = None, limit: int = 50) -> List[RetailProduct]:
        """Search for discounted products with minimum discount percentage"""
        logger.info(f"Searching Target discounted products with min discount: {min_discount}%")
        
        # For Target, we'll get clearance products and filter by discount percentage
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
        logger.info(f"Getting Target product details for ID: {product_id}")
        
        url = f"{self.BASE_URL}/p/A-{product_id}"
        
        try:
            response = self.session.get(url)
            self._handle_request_error(response, "Target product details")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract product data
            title_elem = soup.select_one('h1[data-test="product-title"]')
            title = title_elem.text.strip() if title_elem else "Unknown Product"
            
            price_elem = soup.select_one('span[data-test="product-price"]')
            price_text = price_elem.text.strip() if price_elem else "$0.00"
            price = float(price_text.replace('$', '').replace(',', ''))
            
            original_price_elem = soup.select_one('span[data-test="product-original-price"]')
            original_price = None
            if original_price_elem:
                original_price_text = original_price_elem.text.strip().replace('$', '').replace(',', '')
                try:
                    original_price = float(original_price_text)
                except ValueError:
                    pass
            
            image_elem = soup.select_one('img[data-test="product-image"]')
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
            description_elem = soup.select_one('div[data-test="product-description"]')
            description = description_elem.text.strip() if description_elem else None
            
            # Extract brand
            brand_elem = soup.select_one('a[data-test="product-brand"]')
            brand = brand_elem.text.strip() if brand_elem else None
            
            # Extract category
            category = None
            breadcrumb_elems = soup.select('li[data-test="breadcrumb"] a')
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
            logger.error(f"Error getting Target product details: {e}")
            # Return a minimal product object if details can't be retrieved
            return RetailProduct(
                product_id=product_id,
                title="Unknown Target Product",
                price=0.0,
                original_price=None,
                url=url,
                image_url="",
                store=self.store
            )
