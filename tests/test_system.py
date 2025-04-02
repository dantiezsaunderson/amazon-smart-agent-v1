#!/usr/bin/env python3
"""
Test script for Amazon Smart Agent
Runs tests to verify functionality of all components
"""

import os
import sys
import logging
import unittest
import json
from datetime import datetime
import time

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.retail_scanners import RetailProduct, WalmartScanner, TargetScanner, DollarTreeScanner, EbayScanner
from src.amazon import AmazonProduct, AmazonProductAPI, AmazonScraper
from src.profit_calculator import ArbitrageOpportunity, ProfitCalculator
from src.product_filter import ProductFilter, SalesRankAnalyzer
from src.database import ProductDatabase
from src.listing_generator import ListingContentGenerator
from src.utils import LoggingManager, ErrorHandler

# Configure logging
logging_manager = LoggingManager()
logger = logging_manager.get_logger('tests')

class TestRetailScanners(unittest.TestCase):
    """Test retail website scanners"""
    
    def setUp(self):
        """Set up test environment"""
        self.walmart_scanner = WalmartScanner()
        self.target_scanner = TargetScanner()
        self.dollar_tree_scanner = DollarTreeScanner()
        self.ebay_scanner = EbayScanner()
    
    def test_walmart_scanner_mock(self):
        """Test Walmart scanner with mock data"""
        # Create mock product
        product = RetailProduct(
            product_id="123",
            title="Test Product",
            brand="Test Brand",
            category="Electronics",
            price=10.99,
            original_price=19.99,
            url="https://www.walmart.com/ip/123",
            image_url="https://www.walmart.com/ip/123.jpg",
            store="Walmart"
        )
        
        # Mock search_clearance method
        original_method = self.walmart_scanner.search_clearance
        self.walmart_scanner.search_clearance = lambda **kwargs: [product]
        
        # Test search_clearance
        results = self.walmart_scanner.search_clearance(category="Electronics", limit=10)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Test Product")
        self.assertEqual(results[0].price, 10.99)
        
        # Restore original method
        self.walmart_scanner.search_clearance = original_method
    
    def test_target_scanner_mock(self):
        """Test Target scanner with mock data"""
        # Create mock product
        product = RetailProduct(
            product_id="456",
            title="Test Product",
            brand="Test Brand",
            category="Toys",
            price=15.99,
            original_price=24.99,
            url="https://www.target.com/p/456",
            image_url="https://www.target.com/p/456.jpg",
            store="Target"
        )
        
        # Mock search_clearance method
        original_method = self.target_scanner.search_clearance
        self.target_scanner.search_clearance = lambda **kwargs: [product]
        
        # Test search_clearance
        results = self.target_scanner.search_clearance(category="Toys", limit=10)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Test Product")
        self.assertEqual(results[0].price, 15.99)
        
        # Restore original method
        self.target_scanner.search_clearance = original_method
    
    def test_dollar_tree_scanner_mock(self):
        """Test Dollar Tree scanner with mock data"""
        # Create mock product
        product = RetailProduct(
            product_id="789",
            title="Test Product",
            brand="Test Brand",
            category="Home",
            price=1.00,
            original_price=1.00,
            url="https://www.dollartree.com/789",
            image_url="https://www.dollartree.com/789.jpg",
            store="Dollar Tree"
        )
        
        # Mock search_clearance method
        original_method = self.dollar_tree_scanner.search_clearance
        self.dollar_tree_scanner.search_clearance = lambda **kwargs: [product]
        
        # Test search_clearance
        results = self.dollar_tree_scanner.search_clearance(category="Home", limit=10)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Test Product")
        self.assertEqual(results[0].price, 1.00)
        
        # Restore original method
        self.dollar_tree_scanner.search_clearance = original_method
    
    def test_ebay_scanner_mock(self):
        """Test eBay scanner with mock data"""
        # Create mock product
        product = RetailProduct(
            product_id="101112",
            title="Test Product",
            brand="Test Brand",
            category="Collectibles",
            price=5.99,
            original_price=9.99,
            url="https://www.ebay.com/itm/101112",
            image_url="https://www.ebay.com/itm/101112.jpg",
            store="eBay"
        )
        
        # Mock search_clearance method
        original_method = self.ebay_scanner.search_clearance
        self.ebay_scanner.search_clearance = lambda **kwargs: [product]
        
        # Test search_clearance
        results = self.ebay_scanner.search_clearance(category="Collectibles", limit=10)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Test Product")
        self.assertEqual(results[0].price, 5.99)
        
        # Restore original method
        self.ebay_scanner.search_clearance = original_method


class TestAmazonAPI(unittest.TestCase):
    """Test Amazon API client"""
    
    def setUp(self):
        """Set up test environment"""
        self.amazon_scraper = AmazonScraper()
    
    def test_amazon_scraper_mock(self):
        """Test Amazon scraper with mock data"""
        # Create mock product
        product = AmazonProduct(
            asin="B01EXAMPLE",
            title="Amazon Test Product",
            brand="Amazon Brand",
            category="Electronics",
            price=29.99,
            sales_rank=1000,
            review_count=15,
            rating=4.5,
            url="https://www.amazon.com/dp/B01EXAMPLE",
            image_url="https://www.amazon.com/dp/B01EXAMPLE.jpg"
        )
        
        # Mock search_products method
        original_method = self.amazon_scraper.search_products
        self.amazon_scraper.search_products = lambda *args, **kwargs: [product]
        
        # Test search_products
        results = self.amazon_scraper.search_products("test product", limit=10)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Amazon Test Product")
        self.assertEqual(results[0].price, 29.99)
        
        # Restore original method
        self.amazon_scraper.search_products = original_method


class TestProfitCalculator(unittest.TestCase):
    """Test profit calculator"""
    
    def setUp(self):
        """Set up test environment"""
        self.calculator = ProfitCalculator()
    
    def test_calculate_opportunity(self):
        """Test opportunity calculation"""
        # Create retail product
        retail_product = RetailProduct(
            product_id="123",
            title="Test Product",
            brand="Test Brand",
            category="Electronics",
            price=10.99,
            original_price=19.99,
            url="https://www.walmart.com/ip/123",
            image_url="https://www.walmart.com/ip/123.jpg",
            store="Walmart"
        )
        
        # Create Amazon product
        amazon_product = AmazonProduct(
            asin="B01EXAMPLE",
            title="Amazon Test Product",
            brand="Amazon Brand",
            category="Electronics",
            price=29.99,
            sales_rank=1000,
            review_count=15,
            rating=4.5,
            url="https://www.amazon.com/dp/B01EXAMPLE",
            image_url="https://www.amazon.com/dp/B01EXAMPLE.jpg"
        )
        
        # Calculate opportunity
        opportunity = self.calculator.calculate_opportunity(
            retail_product=retail_product,
            amazon_product=amazon_product,
            fulfillment_method="FBA"
        )
        
        # Test opportunity values
        self.assertEqual(opportunity.retail_product, retail_product)
        self.assertEqual(opportunity.amazon_product, amazon_product)
        self.assertEqual(opportunity.fulfillment_method, "FBA")
        self.assertGreater(opportunity.profit, 0)
        self.assertGreater(opportunity.roi, 0)


class TestProductFilter(unittest.TestCase):
    """Test product filter"""
    
    def setUp(self):
        """Set up test environment"""
        self.product_filter = ProductFilter()
    
    def test_apply_all_filters(self):
        """Test applying all filters"""
        # Create retail product
        retail_product = RetailProduct(
            product_id="123",
            title="Test Product",
            brand="Test Brand",
            category="Electronics",
            price=10.99,
            original_price=19.99,
            url="https://www.walmart.com/ip/123",
            image_url="https://www.walmart.com/ip/123.jpg",
            store="Walmart"
        )
        
        # Create Amazon product
        amazon_product = AmazonProduct(
            asin="B01EXAMPLE",
            title="Amazon Test Product",
            brand="Amazon Brand",
            category="Electronics",
            price=29.99,
            sales_rank=1000,
            review_count=15,
            rating=4.5,
            url="https://www.amazon.com/dp/B01EXAMPLE",
            image_url="https://www.amazon.com/dp/B01EXAMPLE.jpg"
        )
        
        # Create opportunity
        opportunity = ArbitrageOpportunity(
            retail_product=retail_product,
            amazon_product=amazon_product,
            fulfillment_method="FBA",
            profit=10.00,
            roi=50.0,
            costs=None
        )
        
        # Create category percentiles
        category_percentiles = {
            "Electronics": {
                "5%": 2000,
                "10%": 5000,
                "25%": 10000,
                "50%": 20000
            }
        }
        
        # Apply filters
        filtered_opportunities = self.product_filter.apply_all_filters(
            opportunities=[opportunity],
            min_roi=40.0,
            max_reviews=20,
            category_percentiles=category_percentiles
        )
        
        # Test filtered opportunities
        self.assertEqual(len(filtered_opportunities), 1)
        self.assertEqual(filtered_opportunities[0], opportunity)


class TestDatabase(unittest.TestCase):
    """Test database"""
    
    def setUp(self):
        """Set up test environment"""
        # Use in-memory database for testing
        self.db = ProductDatabase(db_path=":memory:")
        self.db.initialize()
    
    def test_add_and_get_opportunities(self):
        """Test adding and retrieving opportunities"""
        # Create retail product
        retail_product = RetailProduct(
            product_id="123",
            title="Test Product",
            brand="Test Brand",
            category="Electronics",
            price=10.99,
            original_price=19.99,
            url="https://www.walmart.com/ip/123",
            image_url="https://www.walmart.com/ip/123.jpg",
            store="Walmart"
        )
        
        # Create Amazon product
        amazon_product = AmazonProduct(
            asin="B01EXAMPLE",
            title="Amazon Test Product",
            brand="Amazon Brand",
            category="Electronics",
            price=29.99,
            sales_rank=1000,
            review_count=15,
            rating=4.5,
            url="https://www.amazon.com/dp/B01EXAMPLE",
            image_url="https://www.amazon.com/dp/B01EXAMPLE.jpg"
        )
        
        # Create opportunity
        opportunity = ArbitrageOpportunity(
            retail_product=retail_product,
            amazon_product=amazon_product,
            fulfillment_method="FBA",
            profit=10.00,
            roi=50.0,
            costs=None
        )
        
        # Add opportunity to database
        self.db.add_opportunities([opportunity])
        
        # Get opportunities from database
        opportunities = self.db.get_opportunities(min_roi=40.0, limit=10)
        
        # Test retrieved opportunities
        self.assertEqual(len(opportunities), 1)
        self.assertEqual(opportunities[0]['retail_product'].title, "Test Product")
        self.assertEqual(opportunities[0]['amazon_product'].title, "Amazon Test Product")
        self.assertEqual(opportunities[0]['profit'], 10.00)
        self.assertEqual(opportunities[0]['roi'], 50.0)


class TestListingGenerator(unittest.TestCase):
    """Test listing generator"""
    
    def setUp(self):
        """Set up test environment"""
        self.generator = ListingContentGenerator()
    
    def test_generate_listing(self):
        """Test generating a listing"""
        # Create retail product
        retail_product = RetailProduct(
            product_id="123",
            title="Test Product",
            brand="Test Brand",
            category="Electronics",
            price=10.99,
            original_price=19.99,
            url="https://www.walmart.com/ip/123",
            image_url="https://www.walmart.com/ip/123.jpg",
            store="Walmart"
        )
        
        # Create Amazon product
        amazon_product = AmazonProduct(
            asin="B01EXAMPLE",
            title="Amazon Test Product",
            brand="Amazon Brand",
            category="Electronics",
            price=29.99,
            sales_rank=1000,
            review_count=15,
            rating=4.5,
            url="https://www.amazon.com/dp/B01EXAMPLE",
            image_url="https://www.amazon.com/dp/B01EXAMPLE.jpg"
        )
        
        # Generate listing
        listing = self.generator.generate_listing(
            retail_product=retail_product,
            amazon_product=amazon_product
        )
        
        # Test listing content
        self.assertIn('title', listing)
        self.assertIn('bullet_points', listing)
        self.assertIn('description', listing)
        self.assertIn('keywords', listing)
        self.assertIn('pricing', listing)
        self.assertIn('generated_at', listing)
        
        # Test title
        self.assertIn(retail_product.title, listing['title'])
        
        # Test bullet points
        self.assertEqual(len(listing['bullet_points']), 5)
        
        # Test pricing
        self.assertGreater(listing['pricing']['suggested_price'], retail_product.price)


def run_tests():
    """Run all tests"""
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestRetailScanners))
    test_suite.addTest(unittest.makeSuite(TestAmazonAPI))
    test_suite.addTest(unittest.makeSuite(TestProfitCalculator))
    test_suite.addTest(unittest.makeSuite(TestProductFilter))
    test_suite.addTest(unittest.makeSuite(TestDatabase))
    test_suite.addTest(unittest.makeSuite(TestListingGenerator))
    
    # Run tests
    test_runner = unittest.TextTestRunner(verbosity=2)
    test_result = test_runner.run(test_suite)
    
    # Return test result
    return test_result


if __name__ == '__main__':
    # Run tests
    test_result = run_tests()
    
    # Print summary
    print("\nTest Summary:")
    print(f"Ran {test_result.testsRun} tests")
    print(f"Failures: {len(test_result.failures)}")
    print(f"Errors: {len(test_result.errors)}")
    
    # Exit with appropriate code
    if test_result.wasSuccessful():
        print("\nAll tests passed!")
        sys.exit(0)
    else:
        print("\nTests failed!")
        sys.exit(1)
