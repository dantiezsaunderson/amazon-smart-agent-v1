#!/usr/bin/env python3
"""
CLI tool for Amazon Smart Agent
Allows manual scanning for arbitrage opportunities
"""

import os
import sys
import argparse
import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import time
from tabulate import tabulate

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.retail_scanners import RetailProduct, WalmartScanner, TargetScanner, DollarTreeScanner, EbayScanner
from src.amazon import AmazonProduct, AmazonProductAPI, AmazonScraper
from src.profit_calculator import ArbitrageOpportunity, ProfitCalculator
from src.product_filter import ProductFilter, SalesRankAnalyzer
from src.database import ProductDatabase
from src.listing_generator import ListingContentGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('amazon_smart_agent_cli.log')
    ]
)

logger = logging.getLogger(__name__)

class AmazonSmartAgentCLI:
    """Command-line interface for Amazon Smart Agent"""
    
    def __init__(self):
        """Initialize CLI tool"""
        # Initialize components
        self.db = ProductDatabase()
        self.profit_calculator = ProfitCalculator()
        self.product_filter = ProductFilter()
        self.sales_rank_analyzer = SalesRankAnalyzer()
        self.listing_generator = ListingContentGenerator()
        
        # Initialize scanners
        self.scanners = {
            'walmart': WalmartScanner(),
            'target': TargetScanner(),
            'dollartree': DollarTreeScanner(),
            'ebay': EbayScanner()
        }
        
        # Initialize Amazon API client
        amazon_access_key = os.getenv('AMAZON_ACCESS_KEY')
        amazon_secret_key = os.getenv('AMAZON_SECRET_KEY')
        amazon_associate_tag = os.getenv('AMAZON_ASSOCIATE_TAG')
        amazon_region = os.getenv('AMAZON_REGION', 'US')
        
        if amazon_access_key and amazon_secret_key and amazon_associate_tag:
            self.amazon_client = AmazonProductAPI(
                amazon_access_key, amazon_secret_key, amazon_associate_tag, amazon_region
            )
        else:
            logger.warning("Amazon API credentials not found, using scraper as fallback")
            self.amazon_client = AmazonScraper()
    
    def scan(self, store: str, category: str = None, discount: float = 0.0, 
             limit: int = 100, min_roi: float = 40.0, max_reviews: int = 20,
             output_format: str = 'table') -> List[Dict[str, Any]]:
        """
        Scan for arbitrage opportunities
        
        Args:
            store: Store to scan ('walmart', 'target', 'dollartree', 'ebay', 'all')
            category: Category to scan (None for all categories)
            discount: Minimum discount percentage (0 for all products)
            limit: Maximum number of products to scan
            min_roi: Minimum ROI percentage for filtering
            max_reviews: Maximum number of reviews for filtering
            output_format: Output format ('table', 'json', 'csv')
            
        Returns:
            List of arbitrage opportunities
        """
        logger.info(f"Starting scan for store: {store}, category: {category}, discount: {discount}%")
        
        # Step 1: Get retail products
        print(f"Step 1/4: Retrieving products from retail stores...")
        retail_products = self._get_retail_products(store, category, discount, limit)
        
        if not retail_products:
            logger.warning("No retail products found")
            print("No products found for the selected criteria.")
            return []
        
        print(f"Found {len(retail_products)} retail products.")
        
        # Step 2: Get Amazon products
        print(f"Step 2/4: Checking products on Amazon...")
        amazon_products = self._get_amazon_products(retail_products)
        
        if not amazon_products:
            logger.warning("No matching Amazon products found")
            print("No matching Amazon products found.")
            return []
        
        print(f"Found {len(amazon_products)} matching Amazon products.")
        
        # Step 3: Calculate opportunities
        print(f"Step 3/4: Calculating profit and ROI...")
        opportunities = self._calculate_opportunities(retail_products, amazon_products)
        
        if not opportunities:
            logger.warning("No arbitrage opportunities found")
            print("No arbitrage opportunities found.")
            return []
        
        print(f"Calculated {len(opportunities)} potential opportunities.")
        
        # Step 4: Filter opportunities
        print(f"Step 4/4: Filtering opportunities...")
        filtered_opportunities = self._filter_opportunities(
            opportunities, min_roi, max_reviews
        )
        
        if not filtered_opportunities:
            logger.warning("No profitable opportunities found after filtering")
            print("No profitable opportunities found after filtering.")
            return []
        
        print(f"Found {len(filtered_opportunities)} profitable opportunities.")
        
        # Save opportunities to database
        self._save_opportunities(filtered_opportunities)
        
        # Format and display results
        results = self._format_results(filtered_opportunities, output_format)
        
        return filtered_opportunities
    
    def _get_retail_products(self, store: str, category: str = None, 
                            discount: float = 0.0, limit: int = 100) -> List[RetailProduct]:
        """Get products from retail stores"""
        products = []
        
        # Convert category format
        category_param = category
        
        try:
            # Get products from selected store(s)
            if store == "all":
                # Scan all stores
                for scanner_name, scanner in self.scanners.items():
                    try:
                        logger.info(f"Scanning {scanner_name}...")
                        if discount > 0:
                            store_products = scanner.search_discounted(
                                min_discount=discount,
                                category=category_param,
                                limit=limit // len(self.scanners)  # Divide limit among stores
                            )
                        else:
                            store_products = scanner.search_clearance(
                                category=category_param,
                                limit=limit // len(self.scanners)  # Divide limit among stores
                            )
                        
                        products.extend(store_products)
                        logger.info(f"Found {len(store_products)} products from {scanner_name}")
                    except Exception as e:
                        logger.error(f"Error scanning {scanner_name}: {e}")
                        print(f"Error scanning {scanner_name}: {e}")
            else:
                # Scan selected store
                scanner = self.scanners.get(store)
                if scanner:
                    logger.info(f"Scanning {store}...")
                    if discount > 0:
                        products = scanner.search_discounted(
                            min_discount=discount,
                            category=category_param,
                            limit=limit
                        )
                    else:
                        products = scanner.search_clearance(
                            category=category_param,
                            limit=limit
                        )
                    logger.info(f"Found {len(products)} products from {store}")
                else:
                    logger.error(f"Invalid store: {store}")
                    print(f"Invalid store: {store}")
        except Exception as e:
            logger.error(f"Error getting retail products: {e}")
            print(f"Error getting retail products: {e}")
        
        return products
    
    def _get_amazon_products(self, retail_products: List[RetailProduct]) -> Dict[str, AmazonProduct]:
        """Get matching Amazon products"""
        amazon_products = {}
        total = len(retail_products)
        
        for i, product in enumerate(retail_products):
            try:
                # Show progress
                if i % 5 == 0 or i == total - 1:
                    print(f"Checking Amazon for product {i+1}/{total}...")
                
                # Try to find by UPC first
                if product.upc:
                    results = self.amazon_client.search_products(f"upc:{product.upc}", limit=1)
                    if results:
                        amazon_products[product.upc] = results[0]
                        continue
                
                # Try to find by SKU
                if product.sku:
                    results = self.amazon_client.search_products(f"sku:{product.sku}", limit=1)
                    if results:
                        amazon_products[product.sku] = results[0]
                        continue
                
                # Try to find by title
                # Remove brand name from title to improve search
                search_title = product.title
                if product.brand and product.brand in product.title:
                    search_title = product.title.replace(product.brand, "").strip()
                
                results = self.amazon_client.search_products(search_title, limit=1)
                if results:
                    # Use product ID as key
                    amazon_products[product.product_id] = results[0]
            
            except Exception as e:
                logger.error(f"Error getting Amazon product for {product.title}: {e}")
                print(f"Error checking Amazon for {product.title}: {e}")
        
        return amazon_products
    
    def _calculate_opportunities(self, retail_products: List[RetailProduct], 
                               amazon_products: Dict[str, AmazonProduct]) -> List[ArbitrageOpportunity]:
        """Calculate arbitrage opportunities"""
        opportunities = []
        
        for retail_product in retail_products:
            try:
                # Find matching Amazon product
                amazon_product = None
                
                if retail_product.upc and retail_product.upc in amazon_products:
                    amazon_product = amazon_products[retail_product.upc]
                elif retail_product.sku and retail_product.sku in amazon_products:
                    amazon_product = amazon_products[retail_product.sku]
                elif retail_product.product_id in amazon_products:
                    amazon_product = amazon_products[retail_product.product_id]
                
                if amazon_product:
                    # Calculate opportunity
                    opportunity = self.profit_calculator.calculate_opportunity(
                        retail_product=retail_product,
                        amazon_product=amazon_product,
                        fulfillment_method='FBA'  # Default to FBA
                    )
                    
                    opportunities.append(opportunity)
            
            except Exception as e:
                logger.error(f"Error calculating opportunity for {retail_product.title}: {e}")
                print(f"Error calculating opportunity for {retail_product.title}: {e}")
        
        return opportunities
    
    def _filter_opportunities(self, opportunities: List[ArbitrageOpportunity], 
                             min_roi: float = 40.0, max_reviews: int = 20) -> List[ArbitrageOpportunity]:
        """Filter opportunities based on criteria"""
        # Get category percentiles for sales rank filtering
        category_percentiles = self.sales_rank_analyzer.get_category_percentiles()
        
        # Apply all filters
        filtered_opportunities = self.product_filter.apply_all_filters(
            opportunities=opportunities,
            min_roi=min_roi,
            max_reviews=max_reviews,
            category_percentiles=category_percentiles
        )
        
        return filtered_opportunities
    
    def _save_opportunities(self, opportunities: List[ArbitrageOpportunity]):
        """Save opportunities to database"""
        try:
            self.db.add_opportunities(opportunities)
            logger.info(f"Saved {len(opportunities)} opportunities to database")
        except Exception as e:
            logger.error(f"Error saving opportunities to database: {e}")
            print(f"Error saving opportunities to database: {e}")
    
    def _format_results(self, opportunities: List[ArbitrageOpportunity], 
                       output_format: str = 'table') -> str:
        """Format results for display"""
        if not opportunities:
            return "No opportunities found."
        
        if output_format == 'json':
            # Convert to JSON
            results = []
            for opp in opportunities:
                results.append({
                    'retail_product': {
                        'title': opp.retail_product.title,
                        'store': opp.retail_product.store,
                        'price': opp.retail_product.price,
                        'url': opp.retail_product.url
                    },
                    'amazon_product': {
                        'title': opp.amazon_product.title,
                        'asin': opp.amazon_product.asin,
                        'price': opp.amazon_product.price,
                        'sales_rank': opp.amazon_product.sales_rank,
                        'review_count': opp.amazon_product.review_count,
                        'url': opp.amazon_product.url
                    },
                    'profit': opp.profit,
                    'roi': opp.roi,
                    'fulfillment_method': opp.fulfillment_method
                })
            
            print(json.dumps(results, indent=2))
            return json.dumps(results, indent=2)
        
        elif output_format == 'csv':
            # Create CSV
            csv_lines = ['Title,Store,Buy Price,Amazon Price,Profit,ROI,ASIN,Reviews,Sales Rank,URL']
            
            for opp in opportunities:
                csv_lines.append(
                    f'"{opp.retail_product.title}",{opp.retail_product.store},{opp.retail_product.price:.2f},'
                    f'{opp.amazon_product.price:.2f},{opp.profit:.2f},{opp.roi:.1f}%,{opp.amazon_product.asin},'
                    f'{opp.amazon_product.review_count or 0},{opp.amazon_product.sales_rank or 0},{opp.retail_product.url}'
                )
            
            csv_output = '\n'.join(csv_lines)
            print(csv_output)
            return csv_output
        
        else:  # table format
            # Create table
            table_data = []
            
            for opp in opportunities:
                table_data.append([
                    opp.retail_product.title[:40] + ('...' if len(opp.retail_product.title) > 40 else ''),
                    opp.retail_product.store,
                    f"${opp.retail_product.price:.2f}",
                    f"${opp.amazon_product.price:.2f}",
                    f"${opp.profit:.2f}",
                    f"{opp.roi:.1f}%",
                    opp.amazon_product.asin,
                    opp.amazon_product.review_count or 'N/A',
                    opp.amazon_product.sales_rank or 'N/A'
                ])
            
            headers = ['Title', 'Store', 'Buy Price', 'Amazon Price', 'Profit', 'ROI', 'ASIN', 'Reviews', 'Sales Rank']
            table = tabulate(table_data, headers=headers, tablefmt='grid')
            
            print("\nArbitrage Opportunities:\n")
            print(table)
            return table
    
    def generate_listing(self, opportunity_id: int, output_dir: str = None) -> Optional[str]:
        """
        Generate Amazon listing for an opportunity
        
        Args:
            opportunity_id: ID of the opportunity
            output_dir: Directory to save listing
            
        Returns:
            Path to HTML preview file
        """
        try:
            # Get opportunity from database
            opportunity = self.db.get_opportunity_by_id(opportunity_id)
            
            if not opportunity:
                logger.error(f"Opportunity #{opportunity_id} not found")
                print(f"Opportunity #{opportunity_id} not found")
                return None
            
            # Generate listing
            listing = self.listing_generator.generate_listing(
                retail_product=opportunity['retail_product'],
                amazon_product=opportunity['amazon_product']
            )
            
            # Save listing to file
            listing_file = self.listing_generator.save_listing(
                listing=listing,
                product_id=str(opportunity_id),
                output_dir=output_dir
            )
            
            # Generate HTML preview
            preview_file = self.listing_generator.generate_html_preview(
                listing=listing,
                product_id=str(opportunity_id),
                output_dir=output_dir
            )
            
            logger.info(f"Generated listing for opportunity #{opportunity_id}")
            print(f"Generated listing saved to: {listing_file}")
            print(f"HTML preview saved to: {preview_file}")
            
            return preview_file
        
        except Exception as e:
            logger.error(f"Error generating listing: {e}")
            print(f"Error generating listing: {e}")
            return None
    
    def list_opportunities(self, min_roi: float = 0.0, limit: int = 10, 
                          output_format: str = 'table') -> List[Dict[str, Any]]:
        """
        List arbitrage opportunities from database
        
        Args:
            min_roi: Minimum ROI percentage
            limit: Maximum number of opportunities to list
            output_format: Output format ('table', 'json', 'csv')
            
        Returns:
            List of arbitrage opportunities
        """
        try:
            # Get opportunities from database
            opportunities = self.db.get_opportunities(min_roi=min_roi, limit=limit)
            
            if not opportunities:
                logger.warning(f"No opportunities found with {min_roi}%+ ROI")
                print(f"No opportunities found with {min_roi}%+ ROI")
                return []
            
            # Format and display results
            self._format_results(opportunities, output_format)
            
            return opportunities
        
        except Exception as e:
            logger.error(f"Error listing opportunities: {e}")
            print(f"Error listing opportunities: {e}")
            return []
    
    def show_opportunity(self, opportunity_id: int) -> Optional[Dict[str, Any]]:
        """
        Show detailed information for a specific opportunity
        
        Args:
            opportunity_id: ID of the opportunity
            
        Returns:
            Opportunity details
        """
        try:
            # Get opportunity from database
            opportunity = self.db.get_opportunity_by_id(opportunity_id)
            
            if not opportunity:
                logger.error(f"Opportunity #{opportunity_id} not found")
                print(f"Opportunity #{opportunity_id} not found")
                return None
            
            # Display opportunity details
            retail_product = opportunity['retail_product']
            amazon_product = opportunity['amazon_product']
            costs = opportunity['costs']
            
            print("\n" + "=" * 80)
            print(f"Opportunity #{opportunity_id} Details")
            print("=" * 80)
            
            print("\nRetail Product:")
            print(f"Title: {retail_product.title}")
            print(f"Store: {retail_product.store}")
            print(f"Price: ${retail_product.price:.2f}")
            
            if retail_product.original_price:
                discount = ((retail_product.original_price - retail_product.price) / retail_product.original_price) * 100
                print(f"Original Price: ${retail_product.original_price:.2f} ({discount:.1f}% off)")
            
            if retail_product.upc:
                print(f"UPC: {retail_product.upc}")
            
            if retail_product.sku:
                print(f"SKU: {retail_product.sku}")
            
            print(f"URL: {retail_product.url}")
            
            print("\nAmazon Product:")
            print(f"Title: {amazon_product.title}")
            print(f"ASIN: {amazon_product.asin}")
            print(f"Price: ${amazon_product.price:.2f}")
            
            if amazon_product.sales_rank:
                print(f"Sales Rank: #{amazon_product.sales_rank}", end="")
                
                if amazon_product.category:
                    print(f" in {amazon_product.category}")
                else:
                    print()
            
            if amazon_product.review_count:
                print(f"Reviews: {amazon_product.review_count}", end="")
                
                if amazon_product.rating:
                    print(f" ({amazon_product.rating} stars)")
                else:
                    print()
            
            print(f"URL: {amazon_product.url}")
            
            print("\nProfit Analysis:")
            print(f"Buy Price: ${costs.buy_price:.2f}")
            print(f"Sell Price: ${amazon_product.price:.2f}")
            print(f"Amazon Fees: ${costs.amazon_fees:.2f}")
            print(f"Fulfillment: ${costs.fulfillment_cost:.2f} ({opportunity['fulfillment_method']})")
            
            if opportunity['fulfillment_method'] == 'FBA':
                print(f"Shipping to Amazon: ${costs.shipping_to_amazon:.2f}")
            
            print(f"Other Costs: ${costs.other_costs:.2f}")
            
            total_cost = costs.buy_price + costs.amazon_fees + costs.fulfillment_cost + costs.shipping_to_amazon + costs.other_costs
            print(f"Total Cost: ${total_cost:.2f}")
            print(f"Profit: ${opportunity['profit']:.2f}")
            print(f"ROI: {opportunity['roi']:.1f}%")
            
            print("\nActions:")
            print(f"1. Generate Amazon listing: python cli.py generate {opportunity_id}")
            print(f"2. View on Amazon: {amazon_product.url}")
            print(f"3. View on {retail_product.store}: {retail_product.url}")
            
            return opportunity
        
        except Exception as e:
            logger.error(f"Error showing opportunity: {e}")
            print(f"Error showing opportunity: {e}")
            return None


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description='Amazon Smart Agent CLI')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan for arbitrage opportunities')
    scan_parser.add_argument('--store', '-s', choices=['walmart', 'target', 'dollartree', 'ebay', 'all'], 
                            default='all', help='Store to scan')
    scan_parser.add_argument('--category', '-c', help='Category to scan')
    scan_parser.add_argument('--discount', '-d', type=float, default=0.0, 
                            help='Minimum discount percentage')
    scan_parser.add_argument('--limit', '-l', type=int, default=100, 
                            help='Maximum number of products to scan')
    scan_parser.add_argument('--min-roi', '-r', type=float, default=40.0, 
                            help='Minimum ROI percentage')
    scan_parser.add_argument('--max-reviews', '-m', type=int, default=20, 
                            help='Maximum number of reviews')
    scan_parser.add_argument('--output', '-o', choices=['table', 'json', 'csv'], 
                            default='table', help='Output format')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List arbitrage opportunities')
    list_parser.add_argument('--min-roi', '-r', type=float, default=0.0, 
                            help='Minimum ROI percentage')
    list_parser.add_argument('--limit', '-l', type=int, default=10, 
                            help='Maximum number of opportunities to list')
    list_parser.add_argument('--output', '-o', choices=['table', 'json', 'csv'], 
                            default='table', help='Output format')
    
    # Show command
    show_parser = subparsers.add_parser('show', help='Show opportunity details')
    show_parser.add_argument('id', type=int, help='Opportunity ID')
    
    # Generate command
    generate_parser = subparsers.add_parser('generate', help='Generate Amazon listing')
    generate_parser.add_argument('id', type=int, help='Opportunity ID')
    generate_parser.add_argument('--output-dir', '-o', help='Output directory')
    
    args = parser.parse_args()
    
    # Create CLI instance
    cli = AmazonSmartAgentCLI()
    
    # Execute command
    if args.command == 'scan':
        cli.scan(
            store=args.store,
            category=args.category,
            discount=args.discount,
            limit=args.limit,
            min_roi=args.min_roi,
            max_reviews=args.max_reviews,
            output_format=args.output
        )
    
    elif args.command == 'list':
        cli.list_opportunities(
            min_roi=args.min_roi,
            limit=args.limit,
            output_format=args.output
        )
    
    elif args.command == 'show':
        cli.show_opportunity(args.id)
    
    elif args.command == 'generate':
        cli.generate_listing(args.id, args.output_dir)
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
