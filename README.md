# Amazon Smart Agent

An automated arbitrage bot that finds profitable products from retail stores and matches them with profitable Amazon listings.

## Features

- Scans retail websites (Walmart, Target, Dollar Tree, eBay) for clearance or discounted products
- Cross-checks product listings with Amazon prices and sales ranks
- Calculates profit margins using buy price vs. Amazon price and fulfillment costs
- Filters products based on ROI, review count, and sales velocity
- Outputs daily shortlist via Telegram bot or web dashboard
- Generates Amazon-optimized listing content
- CLI tool for manual scans

## Installation

1. Clone the repository:
```bash
git clone https://github.com/dantiezsaunderson/amazon-smart-agent.git
cd amazon-smart-agent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your API keys (see `.env.example` for required variables)

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

### Telegram Bot

The Telegram bot provides commands for scanning retail websites, viewing summaries, and listing profitable products.

- `/find` - Manually trigger a scan
- `/summary` - Show today's best items
- `/profit` - List ROI-positive products
- `/detail <id>` - Show detailed information for a specific opportunity

### Web Dashboard

The web dashboard provides a visual interface for viewing arbitrage opportunities, performing scans, and generating Amazon listings.

1. Start the web dashboard:
```bash
python -m src.web_dashboard
```

2. Open your browser and navigate to `http://localhost:8080`

## Project Structure

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

## Configuration

Create a `.env` file with the following variables:

```
# Amazon API credentials
AMAZON_ACCESS_KEY=your_amazon_access_key
AMAZON_SECRET_KEY=your_amazon_secret_key
AMAZON_ASSOCIATE_TAG=your_amazon_associate_tag
AMAZON_REGION=US

# Telegram bot credentials
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# OpenAI API for listing generation
OPENAI_API_KEY=your_openai_api_key

# Web dashboard settings
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8080
FLASK_DEBUG=False
```

## License

MIT
