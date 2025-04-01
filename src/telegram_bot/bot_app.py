"""
Telegram bot interface module
Provides functionality to interact with the arbitrage bot via Telegram
"""

import os
import logging
import json
from typing import List, Dict, Any, Optional, Callable, Union
from datetime import datetime
import asyncio
from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters, 
    CallbackContext, CallbackQueryHandler, ConversationHandler
)

from src.retail_scanners import RetailProduct, WalmartScanner, TargetScanner, DollarTreeScanner, EbayScanner
from src.amazon import AmazonProduct, AmazonProductAPI, AmazonScraper
from src.profit_calculator import ArbitrageOpportunity, ProfitCalculator
from src.product_filter import ProductFilter, SalesRankAnalyzer
from src.database import ProductDatabase

logger = logging.getLogger(__name__)

# Conversation states
SELECTING_STORE, SELECTING_CATEGORY, SELECTING_DISCOUNT = range(3)

class TelegramBot:
    """Telegram bot interface for the arbitrage bot"""
    
    def __init__(self, token: str = None, chat_id: str = None):
        """
        Initialize Telegram bot
        
        Args:
            token: Telegram bot token
            chat_id: Telegram chat ID for notifications
        """
        self.token = token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        
        if not self.token:
            raise ValueError("Telegram bot token is required")
        
        # Initialize components
        self.db = ProductDatabase()
        self.profit_calculator = ProfitCalculator()
        self.product_filter = ProductFilter()
        self.sales_rank_analyzer = SalesRankAnalyzer()
        
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
        
        # Initialize updater and dispatcher
        self.updater = Updater(self.token)
        self.dispatcher = self.updater.dispatcher
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register command and message handlers"""
        # Command handlers
        self.dispatcher.add_handler(CommandHandler("start", self.start_command))
        self.dispatcher.add_handler(CommandHandler("help", self.help_command))
        self.dispatcher.add_handler(CommandHandler("find", self.find_command))
        self.dispatcher.add_handler(CommandHandler("summary", self.summary_command))
        self.dispatcher.add_handler(CommandHandler("profit", self.profit_command))
        self.dispatcher.add_handler(CommandHandler("detail", self.detail_command))
        
        # Conversation handler for find command
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("find", self.find_command)],
            states={
                SELECTING_STORE: [CallbackQueryHandler(self.store_callback)],
                SELECTING_CATEGORY: [CallbackQueryHandler(self.category_callback)],
                SELECTING_DISCOUNT: [CallbackQueryHandler(self.discount_callback)]
            },
            fallbacks=[CommandHandler("cancel", self.cancel_command)]
        )
        self.dispatcher.add_handler(conv_handler)
        
        # Callback query handler for buttons
        self.dispatcher.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Error handler
        self.dispatcher.add_error_handler(self.error_handler)
    
    def start(self):
        """Start the bot"""
        logger.info("Starting Telegram bot")
        self.updater.start_polling()
        
        # Send startup message if chat_id is provided
        if self.chat_id:
            self.updater.bot.send_message(
                chat_id=self.chat_id,
                text="🤖 Amazon Smart Agent is now online!\n\nUse /help to see available commands."
            )
        
        # Run the bot until you press Ctrl-C
        self.updater.idle()
    
    def stop(self):
        """Stop the bot"""
        logger.info("Stopping Telegram bot")
        self.updater.stop()
    
    async def start_command(self, update: Update, context: CallbackContext):
        """Handle /start command"""
        user = update.effective_user
        await update.message.reply_text(
            f"👋 Hello {user.first_name}!\n\n"
            f"I'm Amazon Smart Agent, your arbitrage assistant. I can help you find profitable "
            f"products from retail stores to sell on Amazon.\n\n"
            f"Use /help to see available commands."
        )
    
    async def help_command(self, update: Update, context: CallbackContext):
        """Handle /help command"""
        help_text = (
            "🤖 *Amazon Smart Agent Commands*\n\n"
            "/find - Manually trigger a scan for profitable products\n"
            "/summary - Show today's best arbitrage opportunities\n"
            "/profit - List ROI-positive products\n"
            "/detail <id> - Show detailed information for a specific opportunity\n"
            "/help - Show this help message\n\n"
            "To get started, try /find to scan for profitable products!"
        )
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def find_command(self, update: Update, context: CallbackContext):
        """Handle /find command to manually trigger a scan"""
        # Create keyboard with store options
        keyboard = [
            [
                InlineKeyboardButton("Walmart", callback_data="store_walmart"),
                InlineKeyboardButton("Target", callback_data="store_target")
            ],
            [
                InlineKeyboardButton("Dollar Tree", callback_data="store_dollartree"),
                InlineKeyboardButton("eBay", callback_data="store_ebay")
            ],
            [
                InlineKeyboardButton("All Stores", callback_data="store_all")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔍 Let's find some profitable products!\n\n"
            "Please select a store to scan:",
            reply_markup=reply_markup
        )
        
        return SELECTING_STORE
    
    async def store_callback(self, update: Update, context: CallbackContext):
        """Handle store selection callback"""
        query = update.callback_query
        await query.answer()
        
        # Get selected store
        store = query.data.split('_')[1]
        context.user_data['store'] = store
        
        # Create keyboard with category options
        if store == 'walmart':
            categories = ["Electronics", "Toys", "Home", "Clothing", "All Categories"]
        elif store == 'target':
            categories = ["Electronics", "Toys", "Home", "Clothing", "All Categories"]
        elif store == 'dollartree':
            categories = ["Home", "Party", "Crafts", "All Categories"]
        elif store == 'ebay':
            categories = ["Electronics", "Collectibles", "Fashion", "All Categories"]
        else:  # all
            categories = ["All Categories"]
        
        keyboard = []
        for i in range(0, len(categories), 2):
            row = []
            for j in range(i, min(i+2, len(categories))):
                category = categories[j]
                callback_data = f"category_{category.lower().replace(' ', '_')}"
                row.append(InlineKeyboardButton(category, callback_data=callback_data))
            keyboard.append(row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        store_name = "All Stores" if store == "all" else store.capitalize()
        await query.edit_message_text(
            f"🔍 Scanning {store_name}\n\n"
            f"Please select a category:",
            reply_markup=reply_markup
        )
        
        return SELECTING_CATEGORY
    
    async def category_callback(self, update: Update, context: CallbackContext):
        """Handle category selection callback"""
        query = update.callback_query
        await query.answer()
        
        # Get selected category
        category = query.data.split('_', 1)[1]
        context.user_data['category'] = category
        
        # Create keyboard with discount options
        keyboard = [
            [
                InlineKeyboardButton("30%+", callback_data="discount_30"),
                InlineKeyboardButton("40%+", callback_data="discount_40"),
                InlineKeyboardButton("50%+", callback_data="discount_50")
            ],
            [
                InlineKeyboardButton("60%+", callback_data="discount_60"),
                InlineKeyboardButton("70%+", callback_data="discount_70"),
                InlineKeyboardButton("All", callback_data="discount_all")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        store = context.user_data['store']
        store_name = "All Stores" if store == "all" else store.capitalize()
        category_name = "All Categories" if category == "all_categories" else category.replace('_', ' ').capitalize()
        
        await query.edit_message_text(
            f"🔍 Scanning {store_name} - {category_name}\n\n"
            f"Please select minimum discount percentage:",
            reply_markup=reply_markup
        )
        
        return SELECTING_DISCOUNT
    
    async def discount_callback(self, update: Update, context: CallbackContext):
        """Handle discount selection callback and start scan"""
        query = update.callback_query
        await query.answer()
        
        # Get selected discount
        discount_str = query.data.split('_')[1]
        if discount_str == 'all':
            discount = 0
        else:
            discount = int(discount_str)
        
        context.user_data['discount'] = discount
        
        # Get store and category
        store = context.user_data['store']
        category = context.user_data['category']
        
        # Format names for display
        store_name = "All Stores" if store == "all" else store.capitalize()
        category_name = "All Categories" if category == "all_categories" else category.replace('_', ' ').capitalize()
        discount_name = "Any Discount" if discount == 0 else f"{discount}%+"
        
        # Update message to show scan is in progress
        await query.edit_message_text(
            f"🔍 Scanning in progress...\n\n"
            f"Store: {store_name}\n"
            f"Category: {category_name}\n"
            f"Discount: {discount_name}\n\n"
            f"This may take a few minutes. I'll notify you when the scan is complete."
        )
        
        # Start scan in background
        context.application.create_task(
            self.perform_scan(update, context, store, category, discount)
        )
        
        return ConversationHandler.END
    
    async def perform_scan(self, update: Update, context: CallbackContext, 
                          store: str, category: str, discount: int):
        """Perform scan for profitable products"""
        query = update.callback_query
        
        try:
            # Format names for display
            store_name = "All Stores" if store == "all" else store.capitalize()
            category_name = "All Categories" if category == "all_categories" else category.replace('_', ' ').capitalize()
            discount_name = "Any Discount" if discount == 0 else f"{discount}%+"
            
            # Get retail products
            await query.edit_message_text(
                f"🔍 Scanning in progress...\n\n"
                f"Store: {store_name}\n"
                f"Category: {category_name}\n"
                f"Discount: {discount_name}\n\n"
                f"Step 1/4: Retrieving products from retail stores..."
            )
            
            retail_products = await self.get_retail_products(store, category, discount)
            
            if not retail_products:
                await query.edit_message_text(
                    f"❌ No products found for the selected criteria.\n\n"
                    f"Store: {store_name}\n"
                    f"Category: {category_name}\n"
                    f"Discount: {discount_name}\n\n"
                    f"Please try again with different criteria."
                )
                return
            
            # Get Amazon products
            await query.edit_message_text(
                f"🔍 Scanning in progress...\n\n"
                f"Store: {store_name}\n"
                f"Category: {category_name}\n"
                f"Discount: {discount_name}\n\n"
                f"Step 2/4: Checking {len(retail_products)} products on Amazon..."
            )
            
            amazon_products = await self.get_amazon_products(retail_products)
            
            # Calculate opportunities
            await query.edit_message_text(
                f"🔍 Scanning in progress...\n\n"
                f"Store: {store_name}\n"
                f"Category: {category_name}\n"
                f"Discount: {discount_name}\n\n"
                f"Step 3/4: Calculating profit and ROI for {len(amazon_products)} products..."
            )
            
            opportunities = await self.calculate_opportunities(retail_products, amazon_products)
            
            # Filter opportunities
            await query.edit_message_text(
                f"🔍 Scanning in progress...\n\n"
                f"Store: {store_name}\n"
                f"Category: {category_name}\n"
                f"Discount: {discount_name}\n\n"
                f"Step 4/4: Filtering {len(opportunities)} opportunities..."
            )
            
            filtered_opportunities = await self.filter_opportunities(opportunities)
            
            # Save opportunities to database
            await self.save_opportunities(filtered_opportunities)
            
            # Show results
            if filtered_opportunities:
                # Create keyboard with options to view details
                keyboard = []
                for i, opp in enumerate(filtered_opportunities[:5]):
                    keyboard.append([
                        InlineKeyboardButton(
                            f"{opp.retail_product.title[:30]}... ({opp.roi:.1f}% ROI)",
                            callback_data=f"detail_{i}"
                        )
                    ])
                
                keyboard.append([
                    InlineKeyboardButton("View All Results", callback_data="view_all")
                ])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"✅ Scan complete!\n\n"
                    f"Found {len(filtered_opportunities)} profitable opportunities.\n\n"
                    f"Top 5 opportunities:",
                    reply_markup=reply_markup
                )
                
                # Store opportunities in context for later use
                context.user_data['opportunities'] = filtered_opportunities
            else:
                await query.edit_message_text(
                    f"❌ No profitable opportunities found for the selected criteria.\n\n"
                    f"Store: {store_name}\n"
                    f"Category: {category_name}\n"
                    f"Discount: {discount_name}\n\n"
                    f"Please try again with different criteria."
                )
        
        except Exception as e:
            logger.error(f"Error during scan: {e}")
            await query.edit_message_text(
                f"❌ An error occurred during the scan: {str(e)}\n\n"
                f"Please try again later."
            )
    
    async def get_retail_products(self, store: str, category: str, discount: int) -> List[RetailProduct]:
        """Get products from retail stores"""
        products = []
        
        # Convert category format
        if category == "all_categories":
            category_param = None
        else:
            category_param = category.replace('_', ' ')
        
        # Get products from selected store(s)
        if store == "all":
            # Scan all stores
            for scanner_name, scanner in self.scanners.items():
                try:
                    if discount > 0:
                        store_products = scanner.search_discounted(
                            min_discount=float(discount),
                            category=category_param,
                            limit=25  # Limit per store
                        )
                    else:
                        store_products = scanner.search_clearance(
                            category=category_param,
                            limit=25  # Limit per store
                        )
                    
                    products.extend(store_products)
                except Exception as e:
                    logger.error(f"Error scanning {scanner_name}: {e}")
        else:
            # Scan selected store
            scanner = self.scanners.get(store)
            if scanner:
                if discount > 0:
                    products = scanner.search_discounted(
                        min_discount=float(discount),
                        category=category_param,
                        limit=100
                    )
                else:
                    products = scanner.search_clearance(
                        category=category_param,
                        limit=100
                    )
        
        return products
    
    async def get_amazon_products(self, retail_products: List[RetailProduct]) -> Dict[str, AmazonProduct]:
        """Get matching Amazon products"""
        amazon_products = {}
        
        for product in retail_products:
            try:
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
        
        return amazon_products
    
    async def calculate_opportunities(self, retail_products: List[RetailProduct], 
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
        
        return opportunities
    
    async def filter_opportunities(self, opportunities: List[ArbitrageOpportunity]) -> List[ArbitrageOpportunity]:
        """Filter opportunities based on criteria"""
        # Get category percentiles for sales rank filtering
        category_percentiles = self.sales_rank_analyzer.get_category_percentiles()
        
        # Apply all filters
        filtered_opportunities = self.product_filter.apply_all_filters(
            opportunities=opportunities,
            category_percentiles=category_percentiles
        )
        
        return filtered_opportunities
    
    async def save_opportunities(self, opportunities: List[ArbitrageOpportunity]):
        """Save opportunities to database"""
        try:
            self.db.add_opportunities(opportunities)
        except Exception as e:
            logger.error(f"Error saving opportunities to database: {e}")
    
    async def summary_command(self, update: Update, context: CallbackContext):
        """Handle /summary command to show today's best items"""
        await update.message.reply_text("🔍 Fetching today's best arbitrage opportunities...")
        
        try:
            # Get today's opportunities from database
            opportunities = self.db.get_today_opportunities(limit=10)
            
            if not opportunities:
                await update.message.reply_text(
                    "❌ No arbitrage opportunities found for today.\n\n"
                    "Try running a scan with /find to discover new opportunities."
                )
                return
            
            # Format summary message
            summary = "📊 *Today's Top Arbitrage Opportunities*\n\n"
            
            for i, opp in enumerate(opportunities):
                retail_product = opp['retail_product']
                amazon_product = opp['amazon_product']
                
                summary += (
                    f"*{i+1}. {retail_product.title[:40]}...*\n"
                    f"Store: {retail_product.store} - ${retail_product.price:.2f}\n"
                    f"Amazon: ${amazon_product.price:.2f}\n"
                    f"Profit: ${opp['profit']:.2f} (ROI: {opp['roi']:.1f}%)\n"
                    f"ID: {opp['id']}\n\n"
                )
            
            summary += "Use /detail <id> to see more information about a specific opportunity."
            
            await update.message.reply_text(summary, parse_mode=ParseMode.MARKDOWN)
        
        except Exception as e:
            logger.error(f"Error getting summary: {e}")
            await update.message.reply_text(
                f"❌ An error occurred while fetching the summary: {str(e)}\n\n"
                f"Please try again later."
            )
    
    async def profit_command(self, update: Update, context: CallbackContext):
        """Handle /profit command to list ROI-positive products"""
        # Check if min_roi parameter is provided
        args = context.args
        min_roi = 40.0  # Default
        
        if args and args[0].isdigit():
            min_roi = float(args[0])
        
        await update.message.reply_text(f"🔍 Fetching arbitrage opportunities with {min_roi}%+ ROI...")
        
        try:
            # Get opportunities from database
            opportunities = self.db.get_opportunities(min_roi=min_roi, limit=10)
            
            if not opportunities:
                await update.message.reply_text(
                    f"❌ No arbitrage opportunities found with {min_roi}%+ ROI.\n\n"
                    f"Try running a scan with /find to discover new opportunities."
                )
                return
            
            # Format profit message
            profit_msg = f"📊 *Top Arbitrage Opportunities ({min_roi}%+ ROI)*\n\n"
            
            for i, opp in enumerate(opportunities):
                retail_product = opp['retail_product']
                amazon_product = opp['amazon_product']
                
                profit_msg += (
                    f"*{i+1}. {retail_product.title[:40]}...*\n"
                    f"Store: {retail_product.store} - ${retail_product.price:.2f}\n"
                    f"Amazon: ${amazon_product.price:.2f}\n"
                    f"Profit: ${opp['profit']:.2f} (ROI: {opp['roi']:.1f}%)\n"
                    f"ID: {opp['id']}\n\n"
                )
            
            profit_msg += "Use /detail <id> to see more information about a specific opportunity."
            
            await update.message.reply_text(profit_msg, parse_mode=ParseMode.MARKDOWN)
        
        except Exception as e:
            logger.error(f"Error getting profit list: {e}")
            await update.message.reply_text(
                f"❌ An error occurred while fetching the profit list: {str(e)}\n\n"
                f"Please try again later."
            )
    
    async def detail_command(self, update: Update, context: CallbackContext):
        """Handle /detail command to show detailed information for a specific opportunity"""
        # Check if ID parameter is provided
        args = context.args
        
        if not args or not args[0].isdigit():
            await update.message.reply_text(
                "❌ Please provide an opportunity ID.\n\n"
                "Usage: /detail <id>"
            )
            return
        
        opportunity_id = int(args[0])
        
        await update.message.reply_text(f"🔍 Fetching details for opportunity #{opportunity_id}...")
        
        try:
            # Get opportunity from database
            opportunity = self.db.get_opportunity_by_id(opportunity_id)
            
            if not opportunity:
                await update.message.reply_text(
                    f"❌ Opportunity #{opportunity_id} not found.\n\n"
                    f"Please check the ID and try again."
                )
                return
            
            # Format detail message
            retail_product = opportunity['retail_product']
            amazon_product = opportunity['amazon_product']
            costs = opportunity['costs']
            
            detail_msg = f"📋 *Arbitrage Opportunity #{opportunity_id}*\n\n"
            
            # Retail product details
            detail_msg += "*Retail Product:*\n"
            detail_msg += f"Title: {retail_product.title}\n"
            detail_msg += f"Store: {retail_product.store}\n"
            detail_msg += f"Price: ${retail_product.price:.2f}"
            
            if retail_product.original_price:
                discount = ((retail_product.original_price - retail_product.price) / retail_product.original_price) * 100
                detail_msg += f" (Was: ${retail_product.original_price:.2f}, {discount:.1f}% off)"
            
            detail_msg += f"\nURL: {retail_product.url}\n\n"
            
            # Amazon product details
            detail_msg += "*Amazon Product:*\n"
            detail_msg += f"Title: {amazon_product.title}\n"
            detail_msg += f"ASIN: {amazon_product.asin}\n"
            detail_msg += f"Price: ${amazon_product.price:.2f}\n"
            
            if amazon_product.sales_rank:
                detail_msg += f"Sales Rank: #{amazon_product.sales_rank}"
                
                if amazon_product.category:
                    detail_msg += f" in {amazon_product.category}"
                
                detail_msg += "\n"
            
            if amazon_product.review_count:
                detail_msg += f"Reviews: {amazon_product.review_count}"
                
                if amazon_product.rating:
                    detail_msg += f" ({amazon_product.rating} stars)"
                
                detail_msg += "\n"
            
            detail_msg += f"URL: {amazon_product.url}\n\n"
            
            # Profit details
            detail_msg += "*Profit Analysis:*\n"
            detail_msg += f"Buy Price: ${costs.buy_price:.2f}\n"
            detail_msg += f"Sell Price: ${amazon_product.price:.2f}\n"
            detail_msg += f"Amazon Fees: ${costs.amazon_fees:.2f}\n"
            detail_msg += f"Fulfillment: ${costs.fulfillment_cost:.2f} ({opportunity['fulfillment_method']})\n"
            
            if opportunity['fulfillment_method'] == 'FBA':
                detail_msg += f"Shipping to Amazon: ${costs.shipping_to_amazon:.2f}\n"
            
            detail_msg += f"Other Costs: ${costs.other_costs:.2f}\n"
            detail_msg += f"Total Cost: ${costs.buy_price + costs.amazon_fees + costs.fulfillment_cost + costs.shipping_to_amazon + costs.other_costs:.2f}\n"
            detail_msg += f"Profit: ${opportunity['profit']:.2f}\n"
            detail_msg += f"ROI: {opportunity['roi']:.1f}%\n"
            
            # Create keyboard with URL buttons
            keyboard = [
                [
                    InlineKeyboardButton("View on Amazon", url=amazon_product.url),
                    InlineKeyboardButton("View on Retail Site", url=retail_product.url)
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(detail_msg, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        
        except Exception as e:
            logger.error(f"Error getting opportunity details: {e}")
            await update.message.reply_text(
                f"❌ An error occurred while fetching the opportunity details: {str(e)}\n\n"
                f"Please try again later."
            )
    
    async def button_callback(self, update: Update, context: CallbackContext):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("detail_"):
            # Show opportunity details
            try:
                index = int(data.split("_")[1])
                opportunities = context.user_data.get('opportunities', [])
                
                if not opportunities or index >= len(opportunities):
                    await query.edit_message_text(
                        "❌ Opportunity not found.\n\n"
                        "The scan results may have expired. Please run a new scan with /find."
                    )
                    return
                
                opportunity = opportunities[index]
                
                # Format detail message
                retail_product = opportunity.retail_product
                amazon_product = opportunity.amazon_product
                costs = opportunity.costs
                
                detail_msg = f"📋 *Arbitrage Opportunity Details*\n\n"
                
                # Retail product details
                detail_msg += "*Retail Product:*\n"
                detail_msg += f"Title: {retail_product.title}\n"
                detail_msg += f"Store: {retail_product.store}\n"
                detail_msg += f"Price: ${retail_product.price:.2f}"
                
                if retail_product.original_price:
                    discount = ((retail_product.original_price - retail_product.price) / retail_product.original_price) * 100
                    detail_msg += f" (Was: ${retail_product.original_price:.2f}, {discount:.1f}% off)"
                
                detail_msg += f"\nURL: {retail_product.url}\n\n"
                
                # Amazon product details
                detail_msg += "*Amazon Product:*\n"
                detail_msg += f"Title: {amazon_product.title}\n"
                detail_msg += f"ASIN: {amazon_product.asin}\n"
                detail_msg += f"Price: ${amazon_product.price:.2f}\n"
                
                if amazon_product.sales_rank:
                    detail_msg += f"Sales Rank: #{amazon_product.sales_rank}"
                    
                    if amazon_product.category:
                        detail_msg += f" in {amazon_product.category}"
                    
                    detail_msg += "\n"
                
                if amazon_product.review_count:
                    detail_msg += f"Reviews: {amazon_product.review_count}"
                    
                    if amazon_product.rating:
                        detail_msg += f" ({amazon_product.rating} stars)"
                    
                    detail_msg += "\n"
                
                detail_msg += f"URL: {amazon_product.url}\n\n"
                
                # Profit details
                detail_msg += "*Profit Analysis:*\n"
                detail_msg += f"Buy Price: ${costs.buy_price:.2f}\n"
                detail_msg += f"Sell Price: ${amazon_product.price:.2f}\n"
                detail_msg += f"Amazon Fees: ${costs.amazon_fees:.2f}\n"
                detail_msg += f"Fulfillment: ${costs.fulfillment_cost:.2f} ({opportunity.fulfillment_method})\n"
                
                if opportunity.fulfillment_method == 'FBA':
                    detail_msg += f"Shipping to Amazon: ${costs.shipping_to_amazon:.2f}\n"
                
                detail_msg += f"Other Costs: ${costs.other_costs:.2f}\n"
                detail_msg += f"Total Cost: ${costs.total_cost:.2f}\n"
                detail_msg += f"Profit: ${opportunity.profit:.2f}\n"
                detail_msg += f"ROI: {opportunity.roi:.1f}%\n"
                
                # Create keyboard with URL buttons and back button
                keyboard = [
                    [
                        InlineKeyboardButton("View on Amazon", url=amazon_product.url),
                        InlineKeyboardButton("View on Retail Site", url=retail_product.url)
                    ],
                    [
                        InlineKeyboardButton("« Back to Results", callback_data="view_all")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    detail_msg, 
                    parse_mode=ParseMode.MARKDOWN, 
                    reply_markup=reply_markup
                )
            
            except Exception as e:
                logger.error(f"Error showing opportunity details: {e}")
                await query.edit_message_text(
                    f"❌ An error occurred while showing the opportunity details: {str(e)}\n\n"
                    f"Please try again later."
                )
        
        elif data == "view_all":
            # Show all opportunities
            try:
                opportunities = context.user_data.get('opportunities', [])
                
                if not opportunities:
                    await query.edit_message_text(
                        "❌ No opportunities found.\n\n"
                        "The scan results may have expired. Please run a new scan with /find."
                    )
                    return
                
                # Format results message
                results_msg = f"📊 *Scan Results - {len(opportunities)} Opportunities*\n\n"
                
                for i, opp in enumerate(opportunities[:10]):  # Show top 10
                    retail_product = opp.retail_product
                    amazon_product = opp.amazon_product
                    
                    results_msg += (
                        f"*{i+1}. {retail_product.title[:40]}...*\n"
                        f"Store: {retail_product.store} - ${retail_product.price:.2f}\n"
                        f"Amazon: ${amazon_product.price:.2f}\n"
                        f"Profit: ${opp.profit:.2f} (ROI: {opp.roi:.1f}%)\n\n"
                    )
                
                # Create keyboard with detail buttons
                keyboard = []
                for i in range(min(10, len(opportunities))):
                    keyboard.append([
                        InlineKeyboardButton(f"Details #{i+1}", callback_data=f"detail_{i}")
                    ])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    results_msg, 
                    parse_mode=ParseMode.MARKDOWN, 
                    reply_markup=reply_markup
                )
            
            except Exception as e:
                logger.error(f"Error showing all opportunities: {e}")
                await query.edit_message_text(
                    f"❌ An error occurred while showing all opportunities: {str(e)}\n\n"
                    f"Please try again later."
                )
    
    async def cancel_command(self, update: Update, context: CallbackContext):
        """Handle /cancel command to cancel conversation"""
        await update.message.reply_text(
            "🛑 Operation cancelled.\n\n"
            "You can start a new scan with /find."
        )
        return ConversationHandler.END
    
    async def error_handler(self, update: Update, context: CallbackContext):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        try:
            if update.effective_message:
                await update.effective_message.reply_text(
                    "❌ An error occurred while processing your request.\n\n"
                    "Please try again later."
                )
        except:
            pass


def run():
    """Run the Telegram bot"""
    try:
        bot = TelegramBot()
        bot.start()
    except Exception as e:
        logger.error(f"Error starting Telegram bot: {e}")
        raise
