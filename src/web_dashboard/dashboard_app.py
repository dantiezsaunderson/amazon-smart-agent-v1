"""
Web dashboard module for displaying arbitrage opportunities
Provides a Flask-based web interface for viewing and managing arbitrage opportunities
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_cors import CORS

from src.retail_scanners import RetailProduct, WalmartScanner, TargetScanner, DollarTreeScanner, EbayScanner
from src.amazon import AmazonProduct, AmazonProductAPI, AmazonScraper
from src.profit_calculator import ArbitrageOpportunity, ProfitCalculator
from src.product_filter import ProductFilter, SalesRankAnalyzer
from src.database import ProductDatabase

logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
            static_folder=os.path.join(os.path.dirname(__file__), 'static'))
CORS(app)

# Initialize components
db = ProductDatabase()
profit_calculator = ProfitCalculator()
product_filter = ProductFilter()
sales_rank_analyzer = SalesRankAnalyzer()

# Initialize scanners
scanners = {
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
    amazon_client = AmazonProductAPI(
        amazon_access_key, amazon_secret_key, amazon_associate_tag, amazon_region
    )
else:
    logger.warning("Amazon API credentials not found, using scraper as fallback")
    amazon_client = AmazonScraper()

# Routes
@app.route('/')
def index():
    """Render dashboard home page"""
    return render_template('index.html')

@app.route('/opportunities')
def opportunities():
    """Render opportunities page"""
    # Get filter parameters
    min_roi = request.args.get('min_roi', type=float, default=40.0)
    min_profit = request.args.get('min_profit', type=float, default=5.0)
    store = request.args.get('store', default=None)
    
    # Get opportunities from database
    if store:
        opps = db.get_opportunities_by_store(store, limit=100)
    else:
        opps = db.get_opportunities(min_roi=min_roi, min_profit=min_profit, limit=100)
    
    return render_template('opportunities.html', opportunities=opps, min_roi=min_roi, min_profit=min_profit, store=store)

@app.route('/opportunity/<int:opportunity_id>')
def opportunity_detail(opportunity_id):
    """Render opportunity detail page"""
    # Get opportunity from database
    opp = db.get_opportunity_by_id(opportunity_id)
    
    if not opp:
        flash(f"Opportunity #{opportunity_id} not found", "error")
        return redirect(url_for('opportunities'))
    
    return render_template('opportunity_detail.html', opportunity=opp)

@app.route('/scan', methods=['GET', 'POST'])
def scan():
    """Render scan page and handle scan requests"""
    if request.method == 'POST':
        # Get scan parameters
        store = request.form.get('store')
        category = request.form.get('category')
        discount = request.form.get('discount', type=float, default=0.0)
        
        # Validate parameters
        if not store:
            flash("Please select a store", "error")
            return redirect(url_for('scan'))
        
        # Convert category format
        if category == "all":
            category_param = None
        else:
            category_param = category.replace('_', ' ')
        
        try:
            # Get products from selected store(s)
            retail_products = []
            
            if store == "all":
                # Scan all stores
                for scanner_name, scanner in scanners.items():
                    try:
                        if discount > 0:
                            store_products = scanner.search_discounted(
                                min_discount=discount,
                                category=category_param,
                                limit=25  # Limit per store
                            )
                        else:
                            store_products = scanner.search_clearance(
                                category=category_param,
                                limit=25  # Limit per store
                            )
                        
                        retail_products.extend(store_products)
                    except Exception as e:
                        logger.error(f"Error scanning {scanner_name}: {e}")
            else:
                # Scan selected store
                scanner = scanners.get(store)
                if scanner:
                    if discount > 0:
                        retail_products = scanner.search_discounted(
                            min_discount=discount,
                            category=category_param,
                            limit=100
                        )
                    else:
                        retail_products = scanner.search_clearance(
                            category=category_param,
                            limit=100
                        )
            
            if not retail_products:
                flash("No products found for the selected criteria", "error")
                return redirect(url_for('scan'))
            
            # Get Amazon products
            amazon_products = {}
            
            for product in retail_products:
                try:
                    # Try to find by UPC first
                    if product.upc:
                        results = amazon_client.search_products(f"upc:{product.upc}", limit=1)
                        if results:
                            amazon_products[product.upc] = results[0]
                            continue
                    
                    # Try to find by SKU
                    if product.sku:
                        results = amazon_client.search_products(f"sku:{product.sku}", limit=1)
                        if results:
                            amazon_products[product.sku] = results[0]
                            continue
                    
                    # Try to find by title
                    # Remove brand name from title to improve search
                    search_title = product.title
                    if product.brand and product.brand in product.title:
                        search_title = product.title.replace(product.brand, "").strip()
                    
                    results = amazon_client.search_products(search_title, limit=1)
                    if results:
                        # Use product ID as key
                        amazon_products[product.product_id] = results[0]
                
                except Exception as e:
                    logger.error(f"Error getting Amazon product for {product.title}: {e}")
            
            # Calculate opportunities
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
                        opportunity = profit_calculator.calculate_opportunity(
                            retail_product=retail_product,
                            amazon_product=amazon_product,
                            fulfillment_method='FBA'  # Default to FBA
                        )
                        
                        opportunities.append(opportunity)
                
                except Exception as e:
                    logger.error(f"Error calculating opportunity for {retail_product.title}: {e}")
            
            # Filter opportunities
            category_percentiles = sales_rank_analyzer.get_category_percentiles()
            filtered_opportunities = product_filter.apply_all_filters(
                opportunities=opportunities,
                category_percentiles=category_percentiles
            )
            
            if not filtered_opportunities:
                flash("No profitable opportunities found for the selected criteria", "warning")
                return redirect(url_for('scan'))
            
            # Save opportunities to database
            try:
                db.add_opportunities(filtered_opportunities)
            except Exception as e:
                logger.error(f"Error saving opportunities to database: {e}")
            
            # Redirect to opportunities page
            flash(f"Found {len(filtered_opportunities)} profitable opportunities", "success")
            return redirect(url_for('opportunities'))
        
        except Exception as e:
            logger.error(f"Error during scan: {e}")
            flash(f"An error occurred during the scan: {str(e)}", "error")
            return redirect(url_for('scan'))
    
    # GET request - render scan form
    return render_template('scan.html')

@app.route('/api/opportunities')
def api_opportunities():
    """API endpoint for opportunities"""
    # Get filter parameters
    min_roi = request.args.get('min_roi', type=float, default=40.0)
    min_profit = request.args.get('min_profit', type=float, default=5.0)
    store = request.args.get('store', default=None)
    limit = request.args.get('limit', type=int, default=100)
    
    # Get opportunities from database
    if store:
        opps = db.get_opportunities_by_store(store, limit=limit)
    else:
        opps = db.get_opportunities(min_roi=min_roi, min_profit=min_profit, limit=limit)
    
    # Convert to JSON-serializable format
    result = []
    for opp in opps:
        opp_dict = {
            'id': opp['id'],
            'retail_product': {
                'title': opp['retail_product'].title,
                'price': opp['retail_product'].price,
                'original_price': opp['retail_product'].original_price,
                'url': opp['retail_product'].url,
                'image_url': opp['retail_product'].image_url,
                'store': opp['retail_product'].store
            },
            'amazon_product': {
                'asin': opp['amazon_product'].asin,
                'title': opp['amazon_product'].title,
                'price': opp['amazon_product'].price,
                'sales_rank': opp['amazon_product'].sales_rank,
                'review_count': opp['amazon_product'].review_count,
                'url': opp['amazon_product'].url
            },
            'profit': opp['profit'],
            'roi': opp['roi'],
            'fulfillment_method': opp['fulfillment_method'],
            'created_at': opp['created_at'].isoformat() if opp['created_at'] else None
        }
        result.append(opp_dict)
    
    return jsonify(result)

@app.route('/api/opportunity/<int:opportunity_id>')
def api_opportunity_detail(opportunity_id):
    """API endpoint for opportunity detail"""
    # Get opportunity from database
    opp = db.get_opportunity_by_id(opportunity_id)
    
    if not opp:
        return jsonify({'error': f"Opportunity #{opportunity_id} not found"}), 404
    
    # Convert to JSON-serializable format
    opp_dict = {
        'id': opp['id'],
        'retail_product': {
            'title': opp['retail_product'].title,
            'price': opp['retail_product'].price,
            'original_price': opp['retail_product'].original_price,
            'url': opp['retail_product'].url,
            'image_url': opp['retail_product'].image_url,
            'store': opp['retail_product'].store,
            'brand': opp['retail_product'].brand,
            'category': opp['retail_product'].category,
            'upc': opp['retail_product'].upc,
            'sku': opp['retail_product'].sku,
            'description': opp['retail_product'].description
        },
        'amazon_product': {
            'asin': opp['amazon_product'].asin,
            'title': opp['amazon_product'].title,
            'price': opp['amazon_product'].price,
            'sales_rank': opp['amazon_product'].sales_rank,
            'category': opp['amazon_product'].category,
            'review_count': opp['amazon_product'].review_count,
            'rating': opp['amazon_product'].rating,
            'url': opp['amazon_product'].url,
            'image_url': opp['amazon_product'].image_url,
            'features': opp['amazon_product'].features,
            'description': opp['amazon_product'].description
        },
        'costs': {
            'buy_price': opp['costs'].buy_price,
            'amazon_fees': opp['costs'].amazon_fees,
            'fulfillment_cost': opp['costs'].fulfillment_cost,
            'shipping_to_amazon': opp['costs'].shipping_to_amazon,
            'other_costs': opp['costs'].other_costs,
            'total_cost': opp['costs'].total_cost
        },
        'profit': opp['profit'],
        'roi': opp['roi'],
        'fulfillment_method': opp['fulfillment_method'],
        'created_at': opp['created_at'].isoformat() if opp['created_at'] else None,
        'updated_at': opp['updated_at'].isoformat() if opp['updated_at'] else None
    }
    
    return jsonify(opp_dict)

@app.route('/api/stats')
def api_stats():
    """API endpoint for dashboard statistics"""
    try:
        # Get today's opportunities
        today_opps = db.get_today_opportunities(limit=1000)
        
        # Calculate statistics
        total_opps = len(today_opps)
        total_profit = sum(opp['profit'] for opp in today_opps)
        avg_roi = sum(opp['roi'] for opp in today_opps) / total_opps if total_opps > 0 else 0
        
        # Count by store
        store_counts = {}
        for opp in today_opps:
            store = opp['retail_product'].store
            store_counts[store] = store_counts.get(store, 0) + 1
        
        # Get top opportunities
        top_opps = sorted(today_opps, key=lambda x: x['roi'], reverse=True)[:5]
        top_opps_data = []
        
        for opp in top_opps:
            top_opps_data.append({
                'id': opp['id'],
                'title': opp['retail_product'].title,
                'store': opp['retail_product'].store,
                'retail_price': opp['retail_product'].price,
                'amazon_price': opp['amazon_product'].price,
                'profit': opp['profit'],
                'roi': opp['roi']
            })
        
        stats = {
            'total_opportunities': total_opps,
            'total_profit': total_profit,
            'average_roi': avg_roi,
            'store_counts': store_counts,
            'top_opportunities': top_opps_data
        }
        
        return jsonify(stats)
    
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500

def run():
    """Run the web dashboard"""
    try:
        host = os.getenv('DASHBOARD_HOST', '0.0.0.0')
        port = int(os.getenv('DASHBOARD_PORT', 8080))
        debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
        
        # Create template and static directories if they don't exist
        os.makedirs(os.path.join(os.path.dirname(__file__), 'templates'), exist_ok=True)
        os.makedirs(os.path.join(os.path.dirname(__file__), 'static'), exist_ok=True)
        
        # Run the app
        app.run(host=host, port=port, debug=debug)
    except Exception as e:
        logger.error(f"Error running web dashboard: {e}")
        raise
