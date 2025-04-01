"""
Amazon module initialization file
Makes Amazon API client and scraper available for import
"""

from .amazon_api import AmazonProduct, AmazonProductAPI, AmazonScraper

__all__ = [
    'AmazonProduct',
    'AmazonProductAPI',
    'AmazonScraper'
]
