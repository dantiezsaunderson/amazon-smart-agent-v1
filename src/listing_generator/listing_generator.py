"""
Amazon listing content generator module
Generates optimized product listings for Amazon based on retail product data
"""

import os
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
import json
import random
from datetime import datetime

import openai
from nltk.tokenize import sent_tokenize
import nltk

from src.retail_scanners import RetailProduct
from src.amazon import AmazonProduct

# Download NLTK data if not already present
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

logger = logging.getLogger(__name__)

class ListingContentGenerator:
    """
    Generates optimized Amazon product listings based on retail product data
    and competitive analysis of existing Amazon listings
    """
    
    def __init__(self, openai_api_key: str = None):
        """
        Initialize the listing content generator
        
        Args:
            openai_api_key: OpenAI API key for content generation
        """
        self.openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        
        if self.openai_api_key:
            openai.api_key = self.openai_api_key
            self.use_ai = True
        else:
            logger.warning("OpenAI API key not found, using template-based generation")
            self.use_ai = False
        
        # Load keyword data
        self.keywords_by_category = self._load_keywords()
    
    def _load_keywords(self) -> Dict[str, List[str]]:
        """
        Load category-specific keywords from file or use default set
        
        Returns:
            Dictionary mapping categories to lists of keywords
        """
        try:
            keywords_file = os.path.join(os.path.dirname(__file__), 'data', 'amazon_keywords.json')
            
            if os.path.exists(keywords_file):
                with open(keywords_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading keywords: {e}")
        
        # Default keywords by category if file not found
        return {
            "Electronics": [
                "high quality", "durable", "wireless", "bluetooth", "rechargeable", 
                "fast charging", "long battery life", "HD", "4K", "smart", "compatible",
                "portable", "lightweight", "premium", "professional", "noise cancelling"
            ],
            "Toys": [
                "educational", "fun", "creative", "interactive", "colorful", "durable",
                "safe", "non-toxic", "developmental", "engaging", "award-winning",
                "STEM", "classic", "popular", "bestselling", "age-appropriate"
            ],
            "Home": [
                "premium", "durable", "easy to clean", "stylish", "modern", "elegant",
                "space-saving", "multifunctional", "high quality", "comfortable",
                "eco-friendly", "stain-resistant", "waterproof", "decorative", "practical"
            ],
            "Clothing": [
                "comfortable", "stylish", "premium", "soft", "breathable", "durable",
                "machine washable", "high quality", "trendy", "classic", "versatile",
                "lightweight", "stretchy", "moisture-wicking", "fashionable"
            ],
            "Beauty": [
                "natural", "organic", "cruelty-free", "vegan", "paraben-free", "effective",
                "gentle", "hydrating", "nourishing", "anti-aging", "dermatologist tested",
                "long-lasting", "premium", "professional", "salon quality"
            ],
            "Kitchen": [
                "durable", "easy to clean", "dishwasher safe", "premium", "professional",
                "high quality", "stainless steel", "non-stick", "BPA-free", "multifunctional",
                "space-saving", "ergonomic", "chef-recommended", "versatile"
            ],
            "Sports": [
                "durable", "high performance", "professional", "comfortable", "lightweight",
                "breathable", "water-resistant", "adjustable", "premium", "ergonomic",
                "versatile", "high quality", "training", "exercise", "fitness"
            ],
            "Books": [
                "bestselling", "award-winning", "critically acclaimed", "educational",
                "informative", "comprehensive", "illustrated", "practical", "essential",
                "definitive", "authoritative", "popular", "classic", "inspiring"
            ],
            "Generic": [
                "high quality", "premium", "durable", "versatile", "practical",
                "perfect gift", "essential", "popular", "bestselling", "value pack",
                "satisfaction guaranteed", "top rated", "multipurpose", "convenient"
            ]
        }
    
    def generate_listing(self, retail_product: RetailProduct, 
                         amazon_product: Optional[AmazonProduct] = None) -> Dict[str, Any]:
        """
        Generate optimized Amazon listing content based on retail product data
        
        Args:
            retail_product: Retail product data
            amazon_product: Existing Amazon product data (if available)
            
        Returns:
            Dictionary containing optimized listing content
        """
        try:
            # Extract product information
            title = self._generate_title(retail_product, amazon_product)
            bullet_points = self._generate_bullet_points(retail_product, amazon_product)
            description = self._generate_description(retail_product, amazon_product)
            keywords = self._generate_keywords(retail_product, amazon_product)
            pricing = self._generate_pricing_suggestions(retail_product, amazon_product)
            
            # Compile listing content
            listing = {
                "title": title,
                "bullet_points": bullet_points,
                "description": description,
                "keywords": keywords,
                "pricing": pricing,
                "generated_at": datetime.now().isoformat()
            }
            
            return listing
        
        except Exception as e:
            logger.error(f"Error generating listing content: {e}")
            
            # Return basic listing if error occurs
            return {
                "title": retail_product.title,
                "bullet_points": ["Product imported from retail store"],
                "description": f"This is a {retail_product.title} product.",
                "keywords": [retail_product.title.split()],
                "pricing": {
                    "suggested_price": retail_product.price * 1.5,
                    "min_price": retail_product.price * 1.3,
                    "max_price": retail_product.price * 2.0
                },
                "generated_at": datetime.now().isoformat()
            }
    
    def _generate_title(self, retail_product: RetailProduct, 
                       amazon_product: Optional[AmazonProduct] = None) -> str:
        """
        Generate optimized product title
        
        Args:
            retail_product: Retail product data
            amazon_product: Existing Amazon product data (if available)
            
        Returns:
            Optimized product title
        """
        if self.use_ai and self.openai_api_key:
            try:
                # Use AI to generate optimized title
                prompt = f"""
                Create an optimized Amazon product title for the following product:
                
                Product: {retail_product.title}
                Brand: {retail_product.brand or 'Unknown'}
                Category: {retail_product.category or 'General'}
                
                The title should:
                1. Be 150-200 characters long
                2. Include the brand name first
                3. Include key product features and benefits
                4. Include color, size, or quantity if applicable
                5. Include important keywords for searchability
                
                Return only the title text without any additional commentary.
                """
                
                response = openai.Completion.create(
                    engine="text-davinci-003",
                    prompt=prompt,
                    max_tokens=100,
                    n=1,
                    stop=None,
                    temperature=0.7
                )
                
                ai_title = response.choices[0].text.strip()
                
                # Ensure title is not too long for Amazon (max 200 characters)
                if len(ai_title) > 200:
                    ai_title = ai_title[:197] + "..."
                
                return ai_title
            
            except Exception as e:
                logger.error(f"Error generating AI title: {e}")
                # Fall back to template-based generation
        
        # Template-based title generation
        brand = retail_product.brand or ""
        title = retail_product.title
        
        # Remove brand from title if it's already there to avoid duplication
        if brand and brand in title:
            title = title.replace(brand, "").strip()
            title = re.sub(r'\s+', ' ', title)  # Remove extra spaces
        
        # Get category-specific keywords
        category = retail_product.category or "Generic"
        if category not in self.keywords_by_category:
            category = "Generic"
        
        keywords = self.keywords_by_category[category]
        selected_keywords = random.sample(keywords, min(3, len(keywords)))
        
        # Construct title with brand, product name, and keywords
        optimized_title = f"{brand} {title}"
        
        # Add color if available
        if hasattr(retail_product, 'color') and retail_product.color:
            optimized_title += f", {retail_product.color}"
        
        # Add size if available
        if hasattr(retail_product, 'size') and retail_product.size:
            optimized_title += f", {retail_product.size}"
        
        # Add selected keywords
        for keyword in selected_keywords:
            if keyword.lower() not in optimized_title.lower() and len(optimized_title) + len(keyword) + 2 <= 200:
                optimized_title += f", {keyword}"
        
        # Ensure title is not too long for Amazon (max 200 characters)
        if len(optimized_title) > 200:
            optimized_title = optimized_title[:197] + "..."
        
        return optimized_title
    
    def _generate_bullet_points(self, retail_product: RetailProduct, 
                               amazon_product: Optional[AmazonProduct] = None) -> List[str]:
        """
        Generate optimized bullet points (key features)
        
        Args:
            retail_product: Retail product data
            amazon_product: Existing Amazon product data (if available)
            
        Returns:
            List of optimized bullet points
        """
        if self.use_ai and self.openai_api_key:
            try:
                # Use AI to generate optimized bullet points
                prompt = f"""
                Create 5 optimized Amazon product bullet points for the following product:
                
                Product: {retail_product.title}
                Brand: {retail_product.brand or 'Unknown'}
                Category: {retail_product.category or 'General'}
                Description: {retail_product.description or 'No description available'}
                
                Each bullet point should:
                1. Highlight a key feature or benefit
                2. Be 150-200 characters long
                3. Start with a benefit in ALL CAPS
                4. Include important keywords for searchability
                
                Format each bullet point on a new line starting with a dash (-).
                Return only the bullet points without any additional commentary.
                """
                
                response = openai.Completion.create(
                    engine="text-davinci-003",
                    prompt=prompt,
                    max_tokens=500,
                    n=1,
                    stop=None,
                    temperature=0.7
                )
                
                ai_bullets = response.choices[0].text.strip().split('\n')
                
                # Clean up bullet points
                cleaned_bullets = []
                for bullet in ai_bullets:
                    bullet = bullet.strip()
                    if bullet.startswith('- '):
                        bullet = bullet[2:]
                    if bullet:
                        cleaned_bullets.append(bullet)
                
                # Ensure we have 5 bullet points
                while len(cleaned_bullets) < 5:
                    cleaned_bullets.append(f"PREMIUM QUALITY - This {retail_product.title} is designed to provide exceptional performance and durability for long-lasting use.")
                
                return cleaned_bullets[:5]  # Return max 5 bullet points
            
            except Exception as e:
                logger.error(f"Error generating AI bullet points: {e}")
                # Fall back to template-based generation
        
        # Template-based bullet point generation
        bullet_templates = [
            "PREMIUM QUALITY - This {product} is made with high-quality materials to ensure durability and long-lasting performance, providing excellent value for your investment.",
            "VERSATILE DESIGN - Perfect for {use_case}, this {product} offers exceptional versatility and convenience for everyday use in various situations.",
            "EASY TO USE - The {product} features a user-friendly design that makes it simple to operate, saving you time and effort while delivering outstanding results.",
            "PERFECT GIFT IDEA - This {product} makes an excellent gift for {occasion}, sure to impress with its quality and functionality.",
            "SATISFACTION GUARANTEED - We stand behind the quality of our {product}, offering complete customer satisfaction with reliable performance you can trust."
        ]
        
        # Get category-specific use cases and occasions
        category = retail_product.category or "Generic"
        use_cases = {
            "Electronics": "home entertainment, office work, or travel",
            "Toys": "playtime, learning activities, or child development",
            "Home": "home decoration, organization, or everyday household tasks",
            "Clothing": "casual outings, special occasions, or everyday wear",
            "Beauty": "daily skincare routines, special occasions, or professional use",
            "Kitchen": "cooking, baking, or entertaining guests",
            "Sports": "training, competitions, or casual exercise",
            "Books": "learning, entertainment, or professional development",
            "Generic": "various applications, daily use, or special occasions"
        }
        
        occasions = {
            "Electronics": "technology enthusiasts, students, or professionals",
            "Toys": "birthdays, holidays, or special achievements",
            "Home": "housewarming, weddings, or anniversaries",
            "Clothing": "birthdays, holidays, or special occasions",
            "Beauty": "birthdays, self-care enthusiasts, or beauty lovers",
            "Kitchen": "cooking enthusiasts, newlyweds, or new homeowners",
            "Sports": "fitness enthusiasts, athletes, or active individuals",
            "Books": "book lovers, students, or lifelong learners",
            "Generic": "birthdays, holidays, or any special occasion"
        }
        
        # Generate bullet points
        product_name = retail_product.title.split()[-1] if retail_product.title else "product"
        use_case = use_cases.get(category, use_cases["Generic"])
        occasion = occasions.get(category, occasions["Generic"])
        
        bullets = []
        for template in bullet_templates:
            bullet = template.format(
                product=product_name,
                use_case=use_case,
                occasion=occasion
            )
            bullets.append(bullet)
        
        return bullets
    
    def _generate_description(self, retail_product: RetailProduct, 
                             amazon_product: Optional[AmazonProduct] = None) -> str:
        """
        Generate optimized product description
        
        Args:
            retail_product: Retail product data
            amazon_product: Existing Amazon product data (if available)
            
        Returns:
            Optimized product description
        """
        if self.use_ai and self.openai_api_key:
            try:
                # Use AI to generate optimized description
                prompt = f"""
                Create an optimized Amazon product description for the following product:
                
                Product: {retail_product.title}
                Brand: {retail_product.brand or 'Unknown'}
                Category: {retail_product.category or 'General'}
                Description: {retail_product.description or 'No description available'}
                
                The description should:
                1. Be 1000-2000 characters long
                2. Start with an engaging introduction about the product
                3. Include 3-4 paragraphs highlighting features and benefits
                4. Use HTML formatting (<p>, <strong>, <em>, <ul>, <li>) for readability
                5. Include a call to action at the end
                6. Incorporate important keywords naturally
                
                Return only the description without any additional commentary.
                """
                
                response = openai.Completion.create(
                    engine="text-davinci-003",
                    prompt=prompt,
                    max_tokens=1000,
                    n=1,
                    stop=None,
                    temperature=0.7
                )
                
                ai_description = response.choices[0].text.strip()
                return ai_description
            
            except Exception as e:
                logger.error(f"Error generating AI description: {e}")
                # Fall back to template-based generation
        
        # Template-based description generation
        product_name = retail_product.title
        brand = retail_product.brand or "Our"
        category = retail_product.category or "Generic"
        
        # Get category-specific keywords
        if category not in self.keywords_by_category:
            category = "Generic"
        
        keywords = self.keywords_by_category[category]
        selected_keywords = random.sample(keywords, min(5, len(keywords)))
        
        # Create description paragraphs
        intro = f"""<p><strong>Introducing the {product_name}</strong> - a {selected_keywords[0]} addition to your {category.lower()} collection. {brand} is proud to offer this {selected_keywords[1]} product designed to enhance your experience and provide exceptional value.</p>"""
        
        features = f"""<p>This {product_name} features {selected_keywords[2]} construction for durability and long-lasting performance. The {selected_keywords[3]} design ensures it will integrate seamlessly into your lifestyle, providing convenience and satisfaction with every use.</p>"""
        
        benefits = f"""<p>Experience the benefits of owning this {selected_keywords[4]} {product_name}:</p>
        <ul>
            <li>Enhanced performance for optimal results</li>
            <li>Reliable durability for long-term use</li>
            <li>Versatile functionality for various applications</li>
            <li>User-friendly design for convenience and ease</li>
        </ul>"""
        
        conclusion = f"""<p>Don't miss this opportunity to own the {product_name}. <strong>Add to cart now</strong> and experience the quality and performance that {brand} products are known for. Your satisfaction is our priority!</p>"""
        
        # Combine paragraphs
        description = f"{intro}\n\n{features}\n\n{benefits}\n\n{conclusion}"
        
        return description
    
    def _generate_keywords(self, retail_product: RetailProduct, 
                          amazon_product: Optional[AmazonProduct] = None) -> List[str]:
        """
        Generate optimized search keywords
        
        Args:
            retail_product: Retail product data
            amazon_product: Existing Amazon product data (if available)
            
        Returns:
            List of optimized search keywords
        """
        if self.use_ai and self.openai_api_key:
            try:
                # Use AI to generate optimized keywords
                prompt = f"""
                Generate a list of 20 optimized Amazon search keywords for the following product:
                
                Product: {retail_product.title}
                Brand: {retail_product.brand or 'Unknown'}
                Category: {retail_product.category or 'General'}
                Description: {retail_product.description or 'No description available'}
                
                The keywords should:
                1. Include both short-tail and long-tail keywords
                2. Be relevant to the product and its features
                3. Include common search terms in this product category
                4. Include variations and synonyms
                
                Format each keyword on a new line.
                Return only the keywords without any additional commentary.
                """
                
                response = openai.Completion.create(
                    engine="text-davinci-003",
                    prompt=prompt,
                    max_tokens=500,
                    n=1,
                    stop=None,
                    temperature=0.7
                )
                
                ai_keywords = response.choices[0].text.strip().split('\n')
                
                # Clean up keywords
                cleaned_keywords = []
                for keyword in ai_keywords:
                    keyword = keyword.strip()
                    if keyword:
                        cleaned_keywords.append(keyword)
                
                return cleaned_keywords
            
            except Exception as e:
                logger.error(f"Error generating AI keywords: {e}")
                # Fall back to template-based generation
        
        # Template-based keyword generation
        keywords = []
        
        # Add product title and components
        keywords.append(retail_product.title)
        title_words = retail_product.title.split()
        if len(title_words) > 1:
            keywords.extend([word for word in title_words if len(word) > 3])
        
        # Add brand if available
        if retail_product.brand:
            keywords.append(retail_product.brand)
            keywords.append(f"{retail_product.brand} {title_words[-1]}")
        
        # Add category if available
        if retail_product.category:
            keywords.append(retail_product.category)
            keywords.append(f"{retail_product.category} {title_words[-1]}")
        
        # Get category-specific keywords
        category = retail_product.category or "Generic"
        if category not in self.keywords_by_category:
            category = "Generic"
        
        category_keywords = self.keywords_by_category[category]
        
        # Add category keywords combined with product
        for keyword in category_keywords:
            if len(keywords) < 20:  # Amazon allows up to 250 bytes of keywords
                keywords.append(f"{keyword} {title_words[-1]}")
        
        # Add remaining category keywords if needed
        remaining_slots = 20 - len(keywords)
        if remaining_slots > 0:
            keywords.extend(category_keywords[:remaining_slots])
        
        # Remove duplicates and limit to 20 keywords
        unique_keywords = list(dict.fromkeys(keywords))
        return unique_keywords[:20]
    
    def _generate_pricing_suggestions(self, retail_product: RetailProduct, 
                                     amazon_product: Optional[AmazonProduct] = None) -> Dict[str, float]:
        """
        Generate pricing suggestions
        
        Args:
            retail_product: Retail product data
            amazon_product: Existing Amazon product data (if available)
            
        Returns:
            Dictionary with pricing suggestions
        """
        # Base pricing on retail price and Amazon price (if available)
        retail_price = retail_product.price
        
        # If we have Amazon pricing, use it as a reference
        if amazon_product and amazon_product.price:
            amazon_price = amazon_product.price
            
            # Calculate suggested price based on both retail and Amazon prices
            suggested_price = max(retail_price * 1.4, amazon_price * 0.95)
            min_price = max(retail_price * 1.2, amazon_price * 0.85)
            max_price = max(retail_price * 1.8, amazon_price * 1.1)
        else:
            # Calculate based only on retail price
            suggested_price = retail_price * 1.5
            min_price = retail_price * 1.3
            max_price = retail_price * 2.0
        
        # Round prices to .99 for psychological pricing
        suggested_price = round(suggested_price - 0.01, 2)
        min_price = round(min_price - 0.01, 2)
        max_price = round(max_price - 0.01, 2)
        
        return {
            "suggested_price": suggested_price,
            "min_price": min_price,
            "max_price": max_price
        }
    
    def save_listing(self, listing: Dict[str, Any], product_id: str, output_dir: str = None) -> str:
        """
        Save generated listing to file
        
        Args:
            listing: Generated listing content
            product_id: Product ID for filename
            output_dir: Directory to save listing (default: current directory)
            
        Returns:
            Path to saved listing file
        """
        if not output_dir:
            output_dir = os.path.join(os.path.dirname(__file__), 'listings')
        
        # Create directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Create filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"listing_{product_id}_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        
        # Save listing to file
        with open(filepath, 'w') as f:
            json.dump(listing, f, indent=2)
        
        return filepath
    
    def generate_html_preview(self, listing: Dict[str, Any], product_id: str, output_dir: str = None) -> str:
        """
        Generate HTML preview of listing
        
        Args:
            listing: Generated listing content
            product_id: Product ID for filename
            output_dir: Directory to save preview (default: current directory)
            
        Returns:
            Path to saved HTML preview file
        """
        if not output_dir:
            output_dir = os.path.join(os.path.dirname(__file__), 'previews')
        
        # Create directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Create filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"preview_{product_id}_{timestamp}.html"
        filepath = os.path.join(output_dir, filename)
        
        # Generate HTML content
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Amazon Listing Preview - {listing['title']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; color: #333; }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        .header {{ background-color: #232f3e; color: white; padding: 10px 20px; }}
        .title {{ font-size: 24px; margin-bottom: 20px; }}
        .price {{ font-size: 28px; color: #B12704; margin-bottom: 20px; }}
        .bullets {{ margin-bottom: 20px; }}
        .bullets h3 {{ font-size: 18px; margin-bottom: 10px; }}
        .bullets ul {{ margin-left: 20px; }}
        .bullets li {{ margin-bottom: 8px; }}
        .description {{ margin-bottom: 20px; }}
        .description h3 {{ font-size: 18px; margin-bottom: 10px; }}
        .keywords {{ margin-bottom: 20px; background-color: #f8f8f8; padding: 15px; border-radius: 5px; }}
        .keywords h3 {{ font-size: 18px; margin-bottom: 10px; }}
        .keywords .tag {{ display: inline-block; background-color: #e7e7e7; padding: 5px 10px; margin: 5px; border-radius: 3px; }}
        .footer {{ margin-top: 30px; text-align: center; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Amazon Listing Preview</h1>
        </div>
        
        <div class="title">
            <h2>{listing['title']}</h2>
        </div>
        
        <div class="price">
            <span>${listing['pricing']['suggested_price']}</span>
            <span style="font-size: 14px; color: #555;"> (Min: ${listing['pricing']['min_price']} - Max: ${listing['pricing']['max_price']})</span>
        </div>
        
        <div class="bullets">
            <h3>Key Features:</h3>
            <ul>
                {''.join([f'<li>{bullet}</li>' for bullet in listing['bullet_points']])}
            </ul>
        </div>
        
        <div class="description">
            <h3>Product Description:</h3>
            <div>{listing['description']}</div>
        </div>
        
        <div class="keywords">
            <h3>Search Keywords:</h3>
            <div>
                {''.join([f'<span class="tag">{keyword}</span>' for keyword in listing['keywords']])}
            </div>
        </div>
        
        <div class="footer">
            <p>Generated by Amazon Smart Agent on {listing['generated_at']}</p>
        </div>
    </div>
</body>
</html>
"""
        
        # Save HTML to file
        with open(filepath, 'w') as f:
            f.write(html_content)
        
        return filepath
