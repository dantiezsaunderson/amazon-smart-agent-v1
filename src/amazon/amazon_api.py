"""
Amazon Product API client module
Provides functionality to check Amazon product prices, sales ranks, and other details
"""

import os
import logging
import json
import time
import random
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import requests
import bottlenose
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

@dataclass
class AmazonProduct:
    """Data class to store Amazon product information"""
    asin: str
    title: str
    price: float
    sales_rank: Optional[int] = None
    category: Optional[str] = None
    review_count: Optional[int] = None
    rating: Optional[float] = None
    image_url: Optional[str] = None
    url: Optional[str] = None
    features: Optional[List[str]] = None
    description: Optional[str] = None
    
    @property
    def is_valid(self) -> bool:
        """Check if the product has valid data"""
        return self.asin and self.title and self.price > 0

class AmazonProductAPI:
    """Client for Amazon Product Advertising API"""
    
    def __init__(self, access_key: str, secret_key: str, associate_tag: str, region: str = 'US'):
        self.access_key = access_key
        self.secret_key = secret_key
        self.associate_tag = associate_tag
        self.region = region
        
        # Initialize the bottlenose client
        self.amazon = bottlenose.Amazon(
            self.access_key,
            self.secret_key,
            self.associate_tag,
            Region=self.region,
            Parser=lambda text: text  # Return the raw response
        )
        
        # Set up error handling
        self.error_handlers = [
            self._handle_api_error,
            self._handle_throttling
        ]
    
    def search_products(self, keywords: str, category: Optional[str] = None, limit: int = 10) -> List[AmazonProduct]:
        """Search for products on Amazon by keywords"""
        logger.info(f"Searching Amazon products with keywords: {keywords}")
        
        search_index = "All"
        if category:
            # Map category to Amazon search index if possible
            category_map = {
                "books": "Books",
                "electronics": "Electronics",
                "toys": "Toys",
                "games": "VideoGames",
                "kitchen": "Kitchen",
                "home": "HomeGarden",
                "beauty": "Beauty",
                "clothing": "Apparel",
                "sports": "SportingGoods",
                "office": "OfficeProducts"
            }
            search_index = category_map.get(category.lower(), "All")
        
        try:
            response = self.amazon.ItemSearch(
                SearchIndex=search_index,
                Keywords=keywords,
                ResponseGroup="ItemAttributes,SalesRank,Images,Reviews",
                Sort="salesrank"
            )
            
            # Parse the XML response
            products = self._parse_item_search_response(response)
            
            # Limit the number of products
            return products[:limit]
            
        except Exception as e:
            logger.error(f"Error searching Amazon products: {e}")
            for handler in self.error_handlers:
                if handler(e):
                    return self.search_products(keywords, category, limit)
            return []
    
    def get_product_by_asin(self, asin: str) -> Optional[AmazonProduct]:
        """Get product details by ASIN"""
        logger.info(f"Getting Amazon product details for ASIN: {asin}")
        
        try:
            response = self.amazon.ItemLookup(
                ItemId=asin,
                ResponseGroup="ItemAttributes,SalesRank,Images,Reviews,EditorialReview"
            )
            
            # Parse the XML response
            products = self._parse_item_lookup_response(response)
            
            if products:
                return products[0]
            return None
            
        except Exception as e:
            logger.error(f"Error getting Amazon product details: {e}")
            for handler in self.error_handlers:
                if handler(e):
                    return self.get_product_by_asin(asin)
            return None
    
    def get_products_by_asins(self, asins: List[str]) -> List[AmazonProduct]:
        """Get multiple products by ASINs"""
        logger.info(f"Getting Amazon product details for {len(asins)} ASINs")
        
        products = []
        
        # Process in batches of 10 (API limitation)
        for i in range(0, len(asins), 10):
            batch_asins = asins[i:i+10]
            try:
                response = self.amazon.ItemLookup(
                    ItemId=','.join(batch_asins),
                    ResponseGroup="ItemAttributes,SalesRank,Images,Reviews"
                )
                
                # Parse the XML response
                batch_products = self._parse_item_lookup_response(response)
                products.extend(batch_products)
                
                # Add a small delay to avoid rate limiting
                time.sleep(random.uniform(1.0, 2.0))
                
            except Exception as e:
                logger.error(f"Error getting Amazon product details for batch: {e}")
                for handler in self.error_handlers:
                    if handler(e):
                        # Retry this batch
                        batch_products = self.get_products_by_asins(batch_asins)
                        products.extend(batch_products)
                        break
        
        return products
    
    def get_competitive_pricing(self, asin: str) -> Dict[str, Any]:
        """Get competitive pricing information for a product"""
        logger.info(f"Getting competitive pricing for ASIN: {asin}")
        
        try:
            response = self.amazon.ItemLookup(
                ItemId=asin,
                ResponseGroup="Offers"
            )
            
            # Parse the XML response
            root = ET.fromstring(response)
            
            # Extract pricing information
            pricing_info = {}
            
            # Check for errors
            errors = root.findall('.//Error')
            if errors:
                for error in errors:
                    code = error.find('Code')
                    message = error.find('Message')
                    if code is not None and message is not None:
                        logger.error(f"Amazon API Error: {code.text} - {message.text}")
                return pricing_info
            
            # Extract offers
            items = root.findall('.//Item')
            if not items:
                return pricing_info
                
            for item in items:
                # Get lowest new price
                lowest_new_price = item.find('.//OfferSummary/LowestNewPrice/Amount')
                if lowest_new_price is not None:
                    pricing_info['lowest_new_price'] = float(lowest_new_price.text) / 100
                
                # Get lowest used price
                lowest_used_price = item.find('.//OfferSummary/LowestUsedPrice/Amount')
                if lowest_used_price is not None:
                    pricing_info['lowest_used_price'] = float(lowest_used_price.text) / 100
                
                # Get total new offers
                total_new = item.find('.//OfferSummary/TotalNew')
                if total_new is not None:
                    pricing_info['total_new_offers'] = int(total_new.text)
                
                # Get total used offers
                total_used = item.find('.//OfferSummary/TotalUsed')
                if total_used is not None:
                    pricing_info['total_used_offers'] = int(total_used.text)
                
                # Get buy box price if available
                buy_box = item.find('.//Offers/Offer/OfferListing/Price/Amount')
                if buy_box is not None:
                    pricing_info['buy_box_price'] = float(buy_box.text) / 100
            
            return pricing_info
            
        except Exception as e:
            logger.error(f"Error getting competitive pricing: {e}")
            for handler in self.error_handlers:
                if handler(e):
                    return self.get_competitive_pricing(asin)
            return {}
    
    def get_sales_rank_percentile(self, sales_rank: int, category: str) -> float:
        """
        Calculate the percentile of a sales rank within its category
        Lower percentile is better (e.g., 5% means top 5% of products)
        """
        # This is a simplified implementation
        # In a real-world scenario, you would need category-specific data
        # to accurately calculate percentiles
        
        # Approximate category thresholds (these would need to be updated regularly)
        category_thresholds = {
            "Books": 2000000,
            "Electronics": 500000,
            "Toys": 400000,
            "VideoGames": 150000,
            "Kitchen": 600000,
            "HomeGarden": 800000,
            "Beauty": 300000,
            "Apparel": 1000000,
            "SportingGoods": 400000,
            "OfficeProducts": 300000,
            # Default for unknown categories
            "All": 1000000
        }
        
        threshold = category_thresholds.get(category, category_thresholds["All"])
        
        # Calculate percentile (lower rank is better)
        if sales_rank <= 0:
            return 100.0  # Invalid rank
        
        percentile = (sales_rank / threshold) * 100
        
        # Cap at 100%
        return min(percentile, 100.0)
    
    def _parse_item_search_response(self, response: str) -> List[AmazonProduct]:
        """Parse the XML response from ItemSearch"""
        products = []
        
        try:
            root = ET.fromstring(response)
            
            # Check for errors
            errors = root.findall('.//Error')
            if errors:
                for error in errors:
                    code = error.find('Code')
                    message = error.find('Message')
                    if code is not None and message is not None:
                        logger.error(f"Amazon API Error: {code.text} - {message.text}")
                return products
            
            # Extract items
            items = root.findall('.//Item')
            if not items:
                return products
                
            for item in items:
                try:
                    # Extract ASIN
                    asin_elem = item.find('ASIN')
                    if asin_elem is None:
                        continue
                    asin = asin_elem.text
                    
                    # Extract title
                    title_elem = item.find('.//ItemAttributes/Title')
                    title = title_elem.text if title_elem is not None else "Unknown Title"
                    
                    # Extract price
                    price = 0.0
                    list_price_elem = item.find('.//ItemAttributes/ListPrice/Amount')
                    if list_price_elem is not None:
                        price = float(list_price_elem.text) / 100
                    else:
                        offer_price_elem = item.find('.//Offers/Offer/OfferListing/Price/Amount')
                        if offer_price_elem is not None:
                            price = float(offer_price_elem.text) / 100
                    
                    # Extract sales rank
                    sales_rank = None
                    sales_rank_elem = item.find('SalesRank')
                    if sales_rank_elem is not None:
                        try:
                            sales_rank = int(sales_rank_elem.text)
                        except ValueError:
                            pass
                    
                    # Extract category
                    category = None
                    browse_node = item.find('.//BrowseNodes/BrowseNode/Name')
                    if browse_node is not None:
                        category = browse_node.text
                    
                    # Extract review count and rating
                    review_count = None
                    rating = None
                    reviews_elem = item.find('.//CustomerReviews/IFrameURL')
                    if reviews_elem is not None:
                        # We would need to fetch and parse the reviews page
                        # This is a simplified implementation
                        pass
                    
                    # Extract image URL
                    image_url = None
                    image_elem = item.find('.//LargeImage/URL')
                    if image_elem is not None:
                        image_url = image_elem.text
                    
                    # Create product URL
                    url = f"https://www.amazon.com/dp/{asin}"
                    
                    # Extract features
                    features = []
                    feature_elems = item.findall('.//ItemAttributes/Feature')
                    for feature_elem in feature_elems:
                        if feature_elem.text:
                            features.append(feature_elem.text)
                    
                    # Create product object
                    product = AmazonProduct(
                        asin=asin,
                        title=title,
                        price=price,
                        sales_rank=sales_rank,
                        category=category,
                        review_count=review_count,
                        rating=rating,
                        image_url=image_url,
                        url=url,
                        features=features if features else None
                    )
                    
                    if product.is_valid:
                        products.append(product)
                
                except Exception as e:
                    logger.error(f"Error parsing Amazon product: {e}")
            
        except Exception as e:
            logger.error(f"Error parsing Amazon API response: {e}")
        
        return products
    
    def _parse_item_lookup_response(self, response: str) -> List[AmazonProduct]:
        """Parse the XML response from ItemLookup"""
        # Similar to _parse_item_search_response but for ItemLookup
        # The main difference is handling multiple items vs. single item
        return self._parse_item_search_response(response)
    
    def _handle_api_error(self, error: Exception) -> bool:
        """Handle API errors and return True if retry is possible"""
        error_str = str(error)
        
        if "AWS.InvalidParameterValue" in error_str:
            logger.error("Invalid parameter value, cannot retry")
            return False
        
        if "AWS.InvalidAssociate" in error_str:
            logger.error("Invalid Associate Tag, cannot retry")
            return False
        
        if "AWS.AccessDenied" in error_str:
            logger.error("Access denied, cannot retry")
            return False
        
        return False  # Don't retry by default
    
    def _handle_throttling(self, error: Exception) -> bool:
        """Handle throttling errors and return True if retry is possible"""
        error_str = str(error)
        
        if "AWS.ECommerceService.RequestThrottled" in error_str:
            logger.warning("Request throttled, retrying after delay")
            time.sleep(random.uniform(2.0, 5.0))
            return True
        
        return False


class AmazonScraper:
    """Fallback scraper for Amazon product data when API is not available"""
    
    BASE_URL = "https://www.amazon.com"
    
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
        }
        self.session.headers.update(self.headers)
    
    def search_products(self, keywords: str, category: Optional[str] = None, limit: int = 10) -> List[AmazonProduct]:
        """Search for products on Amazon by keywords"""
        logger.info(f"Scraping Amazon products with keywords: {keywords}")
        
        search_url = f"{self.BASE_URL}/s?k={keywords.replace(' ', '+')}"
        if category:
            # Add category to search URL if provided
            pass
        
        products = []
        
        try:
            response = self.session.get(search_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find product elements
            product_elements = soup.select('div[data-asin]:not([data-asin=""])')
            
            for element in product_elements[:limit]:
                try:
                    # Extract ASIN
                    asin = element.get('data-asin')
                    if not asin:
                        continue
                    
                    # Extract title
                    title_elem = element.select_one('h2 a span')
                    title = title_elem.text.strip() if title_elem else "Unknown Title"
                    
                    # Extract price
                    price_elem = element.select_one('span.a-price span.a-offscreen')
                    price = 0.0
                    if price_elem:
                        price_text = price_elem.text.strip()
                        try:
                            price = float(price_text.replace('$', '').replace(',', ''))
                        except ValueError:
                            pass
                    
                    # Extract image URL
                    image_elem = element.select_one('img.s-image')
                    image_url = image_elem.get('src') if image_elem else None
                    
                    # Create product URL
                    url = f"{self.BASE_URL}/dp/{asin}"
                    
                    # Create product object
                    product = AmazonProduct(
                        asin=asin,
                        title=title,
                        price=price,
                        image_url=image_url,
                        url=url
                    )
                    
                    if product.is_valid:
                        products.append(product)
                
                except Exception as e:
                    logger.error(f"Error parsing Amazon product: {e}")
            
        except Exception as e:
            logger.error(f"Error scraping Amazon products: {e}")
        
        return products
    
    def get_product_by_asin(self, asin: str) -> Optional[AmazonProduct]:
        """Get product details by ASIN"""
        logger.info(f"Scraping Amazon product details for ASIN: {asin}")
        
        url = f"{self.BASE_URL}/dp/{asin}"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title
            title_elem = soup.select_one('#productTitle')
            title = title_elem.text.strip() if title_elem else "Unknown Title"
            
            # Extract price
            price_elem = soup.select_one('#priceblock_ourprice, #priceblock_dealprice, .a-price .a-offscreen')
            price = 0.0
            if price_elem:
                price_text = price_elem.text.strip()
                try:
                    price = float(price_text.replace('$', '').replace(',', ''))
                except ValueError:
                    pass
            
            # Extract sales rank
            sales_rank = None
            for elem in soup.select('#productDetails_detailBullets_sections1 tr'):
                if 'Best Sellers Rank' in elem.text:
                    rank_text = elem.select_one('td').text.strip()
                    rank_match = re.search(r'#([\d,]+)\s+in', rank_text)
                    if rank_match:
                        try:
                            sales_rank = int(rank_match.group(1).replace(',', ''))
                        except ValueError:
                            pass
                    break
            
            # Extract category
            category = None
            category_elem = soup.select_one('#wayfinding-breadcrumbs_feature_div ul li:nth-last-child(2)')
            if category_elem:
                category = category_elem.text.strip()
            
            # Extract review count and rating
            review_count = None
            rating = None
            reviews_elem = soup.select_one('#acrCustomerReviewText')
            if reviews_elem:
                review_text = reviews_elem.text.strip()
                count_match = re.search(r'([\d,]+)\s+ratings', review_text)
                if count_match:
                    try:
                        review_count = int(count_match.group(1).replace(',', ''))
                    except ValueError:
                        pass
            
            rating_elem = soup.select_one('span[data-hook="rating-out-of-text"]')
            if rating_elem:
                rating_text = rating_elem.text.strip()
                rating_match = re.search(r'([\d.]+)\s+out of', rating_text)
                if rating_match:
                    try:
                        rating = float(rating_match.group(1))
                    except ValueError:
                        pass
            
            # Extract image URL
            image_elem = soup.select_one('#landingImage')
            image_url = None
            if image_elem:
                image_url = image_elem.get('src')
                if not image_url:
                    image_url = image_elem.get('data-old-hires')
            
            # Extract features
            features = []
            feature_elems = soup.select('#feature-bullets ul li')
            for feature_elem in feature_elems:
                feature_text = feature_elem.text.strip()
                if feature_text and not feature_text.startswith('›'):
                    features.append(feature_text)
            
            # Extract description
            description = None
            description_elem = soup.select_one('#productDescription')
            if description_elem:
                description = description_elem.text.strip()
            
            # Create product object
            product = AmazonProduct(
                asin=asin,
                title=title,
                price=price,
                sales_rank=sales_rank,
                category=category,
                review_count=review_count,
                rating=rating,
                image_url=image_url,
                url=url,
                features=features if features else None,
                description=description
            )
            
            return product if product.is_valid else None
            
        except Exception as e:
            logger.error(f"Error scraping Amazon product details: {e}")
            return None
    
    def get_products_by_asins(self, asins: List[str]) -> List[AmazonProduct]:
        """Get multiple products by ASINs"""
        logger.info(f"Scraping Amazon product details for {len(asins)} ASINs")
        
        products = []
        
        for asin in asins:
            try:
                product = self.get_product_by_asin(asin)
                if product:
                    products.append(product)
                
                # Add a small delay to avoid rate limiting
                time.sleep(random.uniform(2.0, 5.0))
                
            except Exception as e:
                logger.error(f"Error scraping Amazon product details for ASIN {asin}: {e}")
        
        return products
