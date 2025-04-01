"""
Dollar Tree scanner module for retrieving clearance and discounted products
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

class DollarTreeScanner(RetailScanner):
    """Scanner for Dollar Tree website to find clearance and discounted products"""
    
    BASE_URL = "https://www.dollartree.com"
    SEARCH_URL = f"{BASE_URL}/on-sale"
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.store = "Dollar Tree"
        
        # Additional headers for Dollar Tree
        self.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Referer': 'https://www.dollartree.com/on-sale',
        })
        self.session.headers.update(self.headers)
    
    def search_clearance(self, category: Optional[str] = None, limit: int = 50) -> List[RetailProduct]:
        """Search for clearance products in the given category"""
        logger.info(f"Searching Dollar Tree clearance products in category: {category or 'all'}")
        
        url = self.SEARCH_URL
        if category:
            url = f"{self.BASE_URL}/on-sale/{category}"
        
        products = []
        page = 1
        
        while len(products) < limit:
            try:
                page_url = f"{url}?currentPage={page}"
                response = self.session.get(page_url)
                self._handle_request_error(response, "Dollar Tree clearance search")
                
                soup = BeautifulSoup(response.text, 'html.parser')
                product_elements = soup.select('div.product-tile')
                
                if not product_elements:
                    break
                
                for element in product_elements:
                    try:
                        # Extract product ID
                        product_id_elem = element.get('data-pid')
                        if not product_id_elem:
                            continue
                        
                        product_id = product_id_elem
                        
                        # Extract product data
                        title_elem = element.select_one('a.link')
                        title = title_elem.text.strip() if title_elem else "Unknown Product"
                        
                        # Dollar Tree products are typically $1.25, but check for sale price
                        price_elem = element.select_one('span.sales')
                        if price_elem:
                            price_text = price_elem.text.strip()
                        else:
                            price_elem = element.select_one('span.price-sales')
                            price_text = price_elem.text.strip() if price_elem else "$1.25"
                        
                        price = float(price_text.replace('$', '').replace(',', ''))
                        
                        # Check for original price
                        original_price_elem = element.select_one('span.price-standard')
                        original_price = None
                        if original_price_elem:
                            original_price_text = original_price_elem.text.strip().replace('$', '').replace(',', '')
                            try:
                                original_price = float(original_price_text)
                            except ValueError:
                                pass
                        
                        # Get product URL
                        url_elem = element.select_one('a.link')
                        product_url = url_elem.get('href', '') if url_elem else ""
                        if product_url and not product_url.startswith('http'):
                            product_url = f"{self.BASE_URL}{product_url}"
                        
                        # Get image URL
                        image_elem = element.select_one('img.tile-image')
                        image_url = image_elem.get('src') if image_elem else ""
                        if image_url and not image_url.startswith('http'):
                            image_url = f"https:{image_url}"
                        
                        product = RetailProduct(
                            product_id=product_id,
                            title=title,
                            price=price,
                            original_price=original_price,
                            url=product_url,
                            image_url=image_url,
                            store=self.store
                        )
                        
                        products.append(product)
                        
                        if len(products) >= limit:
                            break
                    
                    except Exception as e:
                        logger.error(f"Error parsing Dollar Tree product: {e}")
                
                # Check if there's a next page
                next_page = soup.select_one('a.page-next')
                if not next_page:
                    break
                    
                page += 1
                # Add a small delay to avoid rate limiting
                time.sleep(random.uniform(1.0, 2.0))
                
            except Exception as e:
                logger.error(f"Error during Dollar Tree clearance search: {e}")
                break
        
        logger.info(f"Found {len(products)} Dollar Tree clearance products")
        return products
    
    def search_discounted(self, min_discount: float = 40.0, category: Optional[str] = None, limit: int = 50) -> List[RetailProduct]:
        """Search for discounted products with minimum discount percentage"""
        logger.info(f"Searching Dollar Tree discounted products with min discount: {min_discount}%")
        
        # For Dollar Tree, we'll get clearance products and filter by discount percentage
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
        logger.info(f"Getting Dollar Tree product details for ID: {product_id}")
        
        # For Dollar Tree, we need to search for the product since direct URL by ID is not available
        url = f"{self.BASE_URL}/search/go?p={product_id}"
        
        try:
            response = self.session.get(url)
            self._handle_request_error(response, "Dollar Tree product details")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the product element
            product_elem = soup.select_one(f'div.product-tile[data-pid="{product_id}"]')
            if not product_elem:
                raise ValueError(f"Product with ID {product_id} not found")
            
            # Extract product data
            title_elem = product_elem.select_one('a.link')
            title = title_elem.text.strip() if title_elem else "Unknown Product"
            
            # Dollar Tree products are typically $1.25, but check for sale price
            price_elem = product_elem.select_one('span.sales')
            if price_elem:
                price_text = price_elem.text.strip()
            else:
                price_elem = product_elem.select_one('span.price-sales')
                price_text = price_elem.text.strip() if price_elem else "$1.25"
            
            price = float(price_text.replace('$', '').replace(',', ''))
            
            # Check for original price
            original_price_elem = product_elem.select_one('span.price-standard')
            original_price = None
            if original_price_elem:
                original_price_text = original_price_elem.text.strip().replace('$', '').replace(',', '')
                try:
                    original_price = float(original_price_text)
                except ValueError:
                    pass
            
            # Get product URL
            url_elem = product_elem.select_one('a.link')
            product_url = url_elem.get('href', '') if url_elem else ""
            if product_url and not product_url.startswith('http'):
                product_url = f"{self.BASE_URL}{product_url}"
            
            # Get image URL
            image_elem = product_elem.select_one('img.tile-image')
            image_url = image_elem.get('src') if image_elem else ""
            if image_url and not image_url.startswith('http'):
                image_url = f"https:{image_url}"
            
            # For more details, we need to visit the product page
            if product_url:
                try:
                    product_response = self.session.get(product_url)
                    self._handle_request_error(product_response, "Dollar Tree product page")
                    
                    product_soup = BeautifulSoup(product_response.text, 'html.parser')
                    
                    # Extract description
                    description_elem = product_soup.select_one('div.product-description')
                    description = description_elem.text.strip() if description_elem else None
                    
                    # Extract brand
                    brand_elem = product_soup.select_one('div.product-brand')
                    brand = brand_elem.text.strip() if brand_elem else None
                    
                    # Extract category
                    category = None
                    breadcrumb_elems = product_soup.select('ol.breadcrumb li')
                    if breadcrumb_elems and len(breadcrumb_elems) > 1:
                        category = breadcrumb_elems[-2].text.strip()
                    
                    # Extract UPC/SKU
                    upc = None
                    sku = None
                    details_elems = product_soup.select('div.product-info div.attribute')
                    for elem in details_elems:
                        label = elem.select_one('strong')
                        if label and 'UPC' in label.text:
                            upc_elem = elem.select_one('span')
                            if upc_elem:
                                upc = upc_elem.text.strip()
                        elif label and 'SKU' in label.text:
                            sku_elem = elem.select_one('span')
                            if sku_elem:
                                sku = sku_elem.text.strip()
                    
                    return RetailProduct(
                        product_id=product_id,
                        title=title,
                        price=price,
                        original_price=original_price,
                        url=product_url,
                        image_url=image_url,
                        brand=brand,
                        category=category,
                        upc=upc,
                        sku=sku,
                        description=description,
                        store=self.store
                    )
                
                except Exception as e:
                    logger.error(f"Error getting Dollar Tree product page details: {e}")
            
            # Return basic product info if detailed page couldn't be processed
            return RetailProduct(
                product_id=product_id,
                title=title,
                price=price,
                original_price=original_price,
                url=product_url,
                image_url=image_url,
                store=self.store
            )
            
        except Exception as e:
            logger.error(f"Error getting Dollar Tree product details: {e}")
            # Return a minimal product object if details can't be retrieved
            return RetailProduct(
                product_id=product_id,
                title="Unknown Dollar Tree Product",
                price=0.0,
                original_price=None,
                url=f"{self.BASE_URL}/search/go?p={product_id}",
                image_url="",
                store=self.store
            )
