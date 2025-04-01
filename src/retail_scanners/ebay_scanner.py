"""
eBay scanner module for retrieving clearance and discounted products
"""

import os
import logging
import json
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
import time
import random
import re

from .base_scanner import RetailScanner, RetailProduct

logger = logging.getLogger(__name__)

class EbayScanner(RetailScanner):
    """Scanner for eBay website to find clearance and discounted products"""
    
    BASE_URL = "https://www.ebay.com"
    SEARCH_URL = f"{BASE_URL}/deals"
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.store = "eBay"
        
        # Additional headers for eBay
        self.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Referer': 'https://www.ebay.com/deals',
        })
        self.session.headers.update(self.headers)
    
    def search_clearance(self, category: Optional[str] = None, limit: int = 50) -> List[RetailProduct]:
        """Search for clearance products in the given category"""
        logger.info(f"Searching eBay clearance products in category: {category or 'all'}")
        
        url = self.SEARCH_URL
        if category:
            url = f"{self.BASE_URL}/deals/{category}"
        
        products = []
        page = 1
        
        while len(products) < limit:
            try:
                page_url = f"{url}?_pgn={page}"
                response = self.session.get(page_url)
                self._handle_request_error(response, "eBay clearance search")
                
                soup = BeautifulSoup(response.text, 'html.parser')
                product_elements = soup.select('div.dne-itemtile')
                
                if not product_elements:
                    break
                
                for element in product_elements:
                    try:
                        # Extract product ID and URL
                        link_elem = element.select_one('a.dne-itemtile-link')
                        if not link_elem:
                            continue
                            
                        product_url = link_elem.get('href', '')
                        if not product_url:
                            continue
                            
                        # Extract product ID from URL
                        product_id_match = re.search(r'/itm/(\d+)', product_url)
                        if not product_id_match:
                            continue
                            
                        product_id = product_id_match.group(1)
                        
                        # Extract product data
                        title_elem = element.select_one('h3.dne-itemtile-title')
                        title = title_elem.text.strip() if title_elem else "Unknown Product"
                        
                        # Extract current price
                        price_elem = element.select_one('span.first')
                        price_text = price_elem.text.strip() if price_elem else "$0.00"
                        price = float(price_text.replace('$', '').replace(',', ''))
                        
                        # Extract original price
                        original_price_elem = element.select_one('span.itemtile-price-strikethrough')
                        original_price = None
                        if original_price_elem:
                            original_price_text = original_price_elem.text.strip().replace('$', '').replace(',', '')
                            try:
                                original_price = float(original_price_text)
                            except ValueError:
                                pass
                        
                        # Extract image URL
                        image_elem = element.select_one('img.slashui-image-cntr')
                        image_url = image_elem.get('src') if image_elem else ""
                        
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
                        logger.error(f"Error parsing eBay product: {e}")
                
                # Check if there's a next page
                next_page = soup.select_one('a.pagination__next')
                if not next_page:
                    break
                    
                page += 1
                # Add a small delay to avoid rate limiting
                time.sleep(random.uniform(1.0, 2.0))
                
            except Exception as e:
                logger.error(f"Error during eBay clearance search: {e}")
                break
        
        logger.info(f"Found {len(products)} eBay clearance products")
        return products
    
    def search_discounted(self, min_discount: float = 40.0, category: Optional[str] = None, limit: int = 50) -> List[RetailProduct]:
        """Search for discounted products with minimum discount percentage"""
        logger.info(f"Searching eBay discounted products with min discount: {min_discount}%")
        
        # For eBay, we can directly search for discounted products
        url = f"{self.BASE_URL}/deals"
        if category:
            url = f"{self.BASE_URL}/deals/{category}"
        
        products = []
        page = 1
        
        while len(products) < limit:
            try:
                page_url = f"{url}?_pgn={page}&_discount={int(min_discount)}"
                response = self.session.get(page_url)
                self._handle_request_error(response, "eBay discounted search")
                
                soup = BeautifulSoup(response.text, 'html.parser')
                product_elements = soup.select('div.dne-itemtile')
                
                if not product_elements:
                    break
                
                for element in product_elements:
                    try:
                        # Extract product ID and URL
                        link_elem = element.select_one('a.dne-itemtile-link')
                        if not link_elem:
                            continue
                            
                        product_url = link_elem.get('href', '')
                        if not product_url:
                            continue
                            
                        # Extract product ID from URL
                        product_id_match = re.search(r'/itm/(\d+)', product_url)
                        if not product_id_match:
                            continue
                            
                        product_id = product_id_match.group(1)
                        
                        # Extract product data
                        title_elem = element.select_one('h3.dne-itemtile-title')
                        title = title_elem.text.strip() if title_elem else "Unknown Product"
                        
                        # Extract current price
                        price_elem = element.select_one('span.first')
                        price_text = price_elem.text.strip() if price_elem else "$0.00"
                        price = float(price_text.replace('$', '').replace(',', ''))
                        
                        # Extract original price
                        original_price_elem = element.select_one('span.itemtile-price-strikethrough')
                        original_price = None
                        if original_price_elem:
                            original_price_text = original_price_elem.text.strip().replace('$', '').replace(',', '')
                            try:
                                original_price = float(original_price_text)
                            except ValueError:
                                pass
                        
                        # Extract image URL
                        image_elem = element.select_one('img.slashui-image-cntr')
                        image_url = image_elem.get('src') if image_elem else ""
                        
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
                        logger.error(f"Error parsing eBay product: {e}")
                
                # Check if there's a next page
                next_page = soup.select_one('a.pagination__next')
                if not next_page:
                    break
                    
                page += 1
                # Add a small delay to avoid rate limiting
                time.sleep(random.uniform(1.0, 2.0))
                
            except Exception as e:
                logger.error(f"Error during eBay discounted search: {e}")
                break
        
        logger.info(f"Found {len(products)} eBay discounted products")
        return products
    
    def get_product_details(self, product_id: str) -> RetailProduct:
        """Get detailed information for a specific product"""
        logger.info(f"Getting eBay product details for ID: {product_id}")
        
        url = f"{self.BASE_URL}/itm/{product_id}"
        
        try:
            response = self.session.get(url)
            self._handle_request_error(response, "eBay product details")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract product data
            title_elem = soup.select_one('h1.x-item-title__mainTitle')
            title = title_elem.text.strip() if title_elem else "Unknown Product"
            
            # Extract current price
            price_elem = soup.select_one('span.x-price-primary')
            price_text = price_elem.text.strip() if price_elem else "$0.00"
            price = float(price_text.replace('$', '').replace(',', ''))
            
            # Extract original price
            original_price_elem = soup.select_one('span.x-price-original')
            original_price = None
            if original_price_elem:
                original_price_text = original_price_elem.text.strip().replace('$', '').replace(',', '')
                try:
                    original_price = float(original_price_text)
                except ValueError:
                    pass
            
            # Extract image URL
            image_elem = soup.select_one('img.ux-image-carousel-item')
            image_url = image_elem.get('src') if image_elem else ""
            
            # Extract UPC/SKU
            upc = None
            sku = None
            
            # Look for product details in item specifics
            item_specifics = soup.select('div.ux-layout-section__item-table div.ux-labels-values')
            for item in item_specifics:
                label_elem = item.select_one('div.ux-labels-values__labels')
                value_elem = item.select_one('div.ux-labels-values__values')
                
                if label_elem and value_elem:
                    label = label_elem.text.strip()
                    value = value_elem.text.strip()
                    
                    if 'UPC' in label:
                        upc = value
                    elif 'MPN' in label or 'Part Number' in label:
                        sku = value
            
            # Extract description
            description_elem = soup.select_one('div.x-item-description')
            description = description_elem.text.strip() if description_elem else None
            
            # Extract brand
            brand = None
            for item in item_specifics:
                label_elem = item.select_one('div.ux-labels-values__labels')
                value_elem = item.select_one('div.ux-labels-values__values')
                
                if label_elem and value_elem and 'Brand' in label_elem.text:
                    brand = value_elem.text.strip()
            
            # Extract category
            category = None
            breadcrumb_elems = soup.select('nav.breadcrumbs li a')
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
            logger.error(f"Error getting eBay product details: {e}")
            # Return a minimal product object if details can't be retrieved
            return RetailProduct(
                product_id=product_id,
                title="Unknown eBay Product",
                price=0.0,
                original_price=None,
                url=url,
                image_url="",
                store=self.store
            )
