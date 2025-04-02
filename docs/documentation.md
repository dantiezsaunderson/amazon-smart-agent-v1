# Amazon Smart Agent - Documentation

## Overview

Amazon Smart Agent is an automated arbitrage bot designed to find profitable products from retail stores and match them with profitable Amazon listings. This documentation provides detailed information about the system architecture, components, setup instructions, and usage guidelines.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Components](#components)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Usage](#usage)
6. [API Reference](#api-reference)
7. [Troubleshooting](#troubleshooting)
8. [Contributing](#contributing)

## System Architecture

The Amazon Smart Agent follows a modular architecture with the following key components:

```
amazon-smart-agent/
├── src/
│   ├── retail_scanners/     # Retail website scanners
│   ├── amazon/              # Amazon API client
│   ├── profit_calculator/   # Profit calculation module
│   ├── product_filter/      # Product filtering logic
│   ├── database/            # Database for product storage
│   ├── telegram_bot/        # Telegram bot interface
│   ├── web_dashboard/       # Web dashboard
│   ├── listing_generator/   # Amazon listing content generator
│   └── utils/               # Utility functions
├── cli.py                   # CLI tool
├── main.py                  # Main application entry point
├── requirements.txt         # Python dependencies
└── .env.example             # Example environment variables
```

### Data Flow

1. **Data Collection**: Retail scanners collect product data from Walmart, Target, Dollar Tree, and eBay.
2. **Amazon Matching**: Products are matched with Amazon listings using the Amazon Product API.
3. **Profit Calculation**: The profit calculator determines potential ROI for each product.
4. **Filtering**: Products are filtered based on ROI, review count, and sales rank.
5. **Storage**: Profitable opportunities are stored in the database.
6. **Output**: Results are accessible via Telegram bot, web dashboard, or CLI.

## Components

### Retail Scanners

The retail scanners module contains classes for scanning different retail websites:

- `WalmartScanner`: Scans Walmart for clearance and discounted products
- `TargetScanner`: Scans Target for clearance and discounted products
- `DollarTreeScanner`: Scans Dollar Tree for products
- `EbayScanner`: Scans eBay for deals and auctions

Each scanner implements the `BaseScanner` interface, which provides common methods for searching products.

### Amazon API Client

The Amazon API client provides access to Amazon product data:

- `AmazonProductAPI`: Uses the Amazon Product Advertising API to fetch product data
- `AmazonScraper`: Fallback scraper when API credentials are not available

### Profit Calculator

The profit calculator determines the potential profit and ROI for each product:

- Calculates Amazon fees
- Estimates shipping costs
- Determines FBA and FBM fulfillment costs
- Calculates net profit and ROI

### Product Filter

The product filter applies filtering criteria to identify the most profitable opportunities:

- Filters by minimum ROI (default: 40%)
- Filters by maximum review count (default: 20)
- Filters by sales rank percentile (default: top 5%)

### Database

The database module handles storage and retrieval of product data:

- Stores retail products
- Stores Amazon products
- Stores arbitrage opportunities
- Provides methods for querying and filtering data

### Telegram Bot

The Telegram bot provides a chat interface for interacting with the system:

- `/find`: Manually trigger a scan
- `/summary`: Show today's best items
- `/profit`: List ROI-positive products
- `/detail <id>`: Show detailed information for a specific opportunity

### Web Dashboard

The web dashboard provides a visual interface for viewing and managing opportunities:

- View all opportunities
- Filter by various criteria
- View detailed information for each opportunity
- Trigger scans
- Generate Amazon listings

### Listing Generator

The listing generator creates optimized Amazon listings for products:

- Generates optimized titles
- Creates bullet points highlighting key features
- Writes detailed product descriptions
- Suggests keywords for improved searchability
- Recommends pricing strategies

### CLI Tool

The CLI tool provides command-line access to the system:

- `scan`: Scan for arbitrage opportunities
- `list`: List existing opportunities
- `show`: Show detailed information for a specific opportunity
- `generate`: Generate an Amazon listing for a specific opportunity

## Installation

### Prerequisites

- Python 3.8 or higher
- Git
- pip (Python package manager)

### Steps

1. Clone the repository:
```bash
git clone https://github.com/dantiezsaunderson/amazon-smart-agent-v1.git
cd amazon-smart-agent-v1
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your API keys (see [Configuration](#configuration))

4. Initialize the database:
```bash
python -c "from src.database import ProductDatabase; ProductDatabase().initialize()"
```

## Configuration

Create a `.env` file in the root directory with the following variables:

```
# Amazon API credentials
AMAZON_ACCESS_KEY=your_amazon_access_key
AMAZON_SECRET_KEY=your_amazon_secret_key
AMAZON_ASSOCIATE_TAG=your_amazon_associate_tag
AMAZON_REGION=US

# Telegram bot credentials
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# OpenAI API for listing generation
OPENAI_API_KEY=your_openai_api_key

# Web dashboard settings
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8080
FLASK_DEBUG=False

# Database settings
DATABASE_URL=sqlite:///amazon_smart_agent.db

# Retail scanner settings
WALMART_API_KEY=your_walmart_api_key
TARGET_API_KEY=your_target_api_key
EBAY_API_KEY=your_ebay_api_key
```

### API Keys

#### Amazon Product Advertising API

1. Sign up for the Amazon Product Advertising API at https://affiliate-program.amazon.com/
2. Create API credentials in the Amazon Associates Central dashboard
3. Add your Access Key, Secret Key, and Associate Tag to the `.env` file

#### Telegram Bot

1. Create a new bot using BotFather on Telegram
2. Copy the bot token and add it to the `.env` file

#### OpenAI API

1. Sign up for an OpenAI API key at https://platform.openai.com/
2. Add your API key to the `.env` file

#### Retail APIs

1. Sign up for developer accounts at Walmart, Target, and eBay
2. Create API keys and add them to the `.env` file

## Usage

### CLI Tool

The CLI tool provides commands for scanning retail websites, listing opportunities, showing opportunity details, and generating Amazon listings.

```bash
# Scan for arbitrage opportunities
python cli.py scan --store walmart --category electronics --discount 30 --min-roi 40

# List existing opportunities
python cli.py list --min-roi 50 --limit 20

# Show opportunity details
python cli.py show 123

# Generate Amazon listing
python cli.py generate 123
```

#### CLI Options

**Scan Command:**
- `--store, -s`: Store to scan (walmart, target, dollartree, ebay, all)
- `--category, -c`: Category to scan
- `--discount, -d`: Minimum discount percentage
- `--limit, -l`: Maximum number of products to scan
- `--min-roi, -r`: Minimum ROI percentage
- `--max-reviews, -m`: Maximum number of reviews
- `--output, -o`: Output format (table, json, csv)

**List Command:**
- `--min-roi, -r`: Minimum ROI percentage
- `--limit, -l`: Maximum number of opportunities to list
- `--output, -o`: Output format (table, json, csv)

**Show Command:**
- `id`: Opportunity ID

**Generate Command:**
- `id`: Opportunity ID
- `--output-dir, -o`: Output directory

### Telegram Bot

The Telegram bot provides commands for scanning retail websites, viewing summaries, and listing profitable products.

- `/start`: Start the bot and get a welcome message
- `/help`: Show available commands
- `/find`: Manually trigger a scan
- `/summary`: Show today's best items
- `/profit`: List ROI-positive products
- `/detail <id>`: Show detailed information for a specific opportunity
- `/generate <id>`: Generate an Amazon listing for a specific opportunity

### Web Dashboard

The web dashboard provides a visual interface for viewing arbitrage opportunities, performing scans, and generating Amazon listings.

1. Start the web dashboard:
```bash
python -m src.web_dashboard
```

2. Open your browser and navigate to `http://localhost:8080`

#### Dashboard Features

- **Home**: Overview of recent opportunities and statistics
- **Opportunities**: List of all arbitrage opportunities with filtering options
- **Opportunity Detail**: Detailed information for a specific opportunity
- **Scan**: Trigger a new scan with custom parameters
- **Generate**: Generate Amazon listings for opportunities

## API Reference

### Retail Scanners

```python
from src.retail_scanners import WalmartScanner, TargetScanner, DollarTreeScanner, EbayScanner

# Create scanner instance
walmart_scanner = WalmartScanner()

# Search for clearance products
products = walmart_scanner.search_clearance(category="electronics", limit=100)

# Search for discounted products
products = walmart_scanner.search_discounted(min_discount=30, category="toys", limit=100)
```

### Amazon API Client

```python
from src.amazon import AmazonProductAPI

# Create API client
amazon_client = AmazonProductAPI(
    access_key="your_access_key",
    secret_key="your_secret_key",
    associate_tag="your_associate_tag",
    region="US"
)

# Search for products
products = amazon_client.search_products("wireless headphones", limit=10)

# Get product by ASIN
product = amazon_client.get_product_by_asin("B01EXAMPLE")
```

### Profit Calculator

```python
from src.profit_calculator import ProfitCalculator
from src.retail_scanners import RetailProduct
from src.amazon import AmazonProduct

# Create calculator instance
calculator = ProfitCalculator()

# Calculate opportunity
opportunity = calculator.calculate_opportunity(
    retail_product=retail_product,
    amazon_product=amazon_product,
    fulfillment_method="FBA"
)

# Get profit and ROI
profit = opportunity.profit
roi = opportunity.roi
```

### Product Filter

```python
from src.product_filter import ProductFilter

# Create filter instance
product_filter = ProductFilter()

# Apply filters
filtered_opportunities = product_filter.apply_all_filters(
    opportunities=opportunities,
    min_roi=40.0,
    max_reviews=20,
    category_percentiles=category_percentiles
)
```

### Database

```python
from src.database import ProductDatabase

# Create database instance
db = ProductDatabase()

# Add opportunities
db.add_opportunities(opportunities)

# Get opportunities
opportunities = db.get_opportunities(min_roi=40.0, limit=10)

# Get opportunity by ID
opportunity = db.get_opportunity_by_id(123)
```

### Listing Generator

```python
from src.listing_generator import ListingContentGenerator

# Create generator instance
generator = ListingContentGenerator()

# Generate listing
listing = generator.generate_listing(
    retail_product=retail_product,
    amazon_product=amazon_product
)

# Save listing to file
listing_file = generator.save_listing(
    listing=listing,
    product_id="123",
    output_dir="/path/to/output"
)

# Generate HTML preview
preview_file = generator.generate_html_preview(
    listing=listing,
    product_id="123",
    output_dir="/path/to/output"
)
```

## Troubleshooting

### Common Issues

#### API Connection Errors

**Problem**: Unable to connect to retail or Amazon APIs.

**Solution**:
1. Verify API credentials in the `.env` file
2. Check internet connection
3. Ensure API endpoints are correct
4. Check API rate limits

#### Database Errors

**Problem**: Database errors when storing or retrieving data.

**Solution**:
1. Ensure database file exists and is writable
2. Check database connection string in the `.env` file
3. Reinitialize the database if corrupted

#### Telegram Bot Issues

**Problem**: Telegram bot not responding.

**Solution**:
1. Verify bot token in the `.env` file
2. Ensure the bot process is running
3. Check for errors in the bot logs
4. Restart the bot service

#### Web Dashboard Issues

**Problem**: Web dashboard not loading or displaying errors.

**Solution**:
1. Check if the dashboard process is running
2. Verify port settings in the `.env` file
3. Check for errors in the dashboard logs
4. Restart the dashboard service

### Logging

The system uses a comprehensive logging system to track errors and activities:

- Main log file: `logs/amazon_smart_agent.log`
- Error log file: `logs/errors.log`
- Component-specific logs: `logs/<component_name>.log`

To increase logging verbosity, set the log level in the `.env` file:

```
LOG_LEVEL=DEBUG
```

## Contributing

Contributions to the Amazon Smart Agent are welcome! Here's how you can contribute:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature/your-feature-name`
5. Submit a pull request

### Development Guidelines

- Follow PEP 8 style guidelines
- Write unit tests for new features
- Update documentation for changes
- Keep dependencies minimal and well-documented

### Testing

Run tests using pytest:

```bash
pytest
```

Run tests with coverage:

```bash
pytest --cov=src
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
