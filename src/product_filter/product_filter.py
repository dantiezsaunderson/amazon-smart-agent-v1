"""
Product filtering module
Filters products based on ROI, review count, and sales rank criteria
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import math

from src.retail_scanners import RetailProduct
from src.amazon import AmazonProduct
from src.profit_calculator import ArbitrageOpportunity, ProfitCalculator

logger = logging.getLogger(__name__)

class ProductFilter:
    """Filter for arbitrage opportunities based on various criteria"""
    
    def __init__(self, min_roi: float = 40.0, max_reviews: int = 20, 
                 max_bsr_percentile: float = 5.0, min_profit: float = 5.0):
        """
        Initialize product filter
        
        Args:
            min_roi: Minimum ROI percentage
            max_reviews: Maximum number of reviews
            max_bsr_percentile: Maximum BSR percentile (lower is better, e.g., 5.0 means top 5%)
            min_profit: Minimum profit amount in dollars
        """
        self.min_roi = min_roi
        self.max_reviews = max_reviews
        self.max_bsr_percentile = max_bsr_percentile
        self.min_profit = min_profit
    
    def filter_by_roi(self, opportunities: List[ArbitrageOpportunity]) -> List[ArbitrageOpportunity]:
        """Filter opportunities by minimum ROI"""
        logger.info(f"Filtering opportunities by minimum ROI: {self.min_roi}%")
        return [opp for opp in opportunities if opp.roi >= self.min_roi]
    
    def filter_by_reviews(self, opportunities: List[ArbitrageOpportunity]) -> List[ArbitrageOpportunity]:
        """Filter opportunities by maximum review count"""
        logger.info(f"Filtering opportunities by maximum reviews: {self.max_reviews}")
        return [
            opp for opp in opportunities 
            if opp.amazon_product.review_count is None or opp.amazon_product.review_count <= self.max_reviews
        ]
    
    def filter_by_sales_rank(self, opportunities: List[ArbitrageOpportunity], 
                            category_percentiles: Dict[str, Dict[int, float]]) -> List[ArbitrageOpportunity]:
        """
        Filter opportunities by sales rank percentile
        
        Args:
            opportunities: List of arbitrage opportunities
            category_percentiles: Dictionary mapping categories to dictionaries of sales rank to percentile
            
        Returns:
            Filtered list of opportunities
        """
        logger.info(f"Filtering opportunities by BSR percentile: {self.max_bsr_percentile}%")
        
        filtered_opps = []
        
        for opp in opportunities:
            # Skip if no sales rank
            if opp.amazon_product.sales_rank is None:
                continue
                
            # Get category
            category = opp.amazon_product.category
            if not category:
                continue
                
            # Get percentile for this sales rank and category
            percentile = self._get_sales_rank_percentile(
                opp.amazon_product.sales_rank, 
                category, 
                category_percentiles
            )
            
            # Keep if percentile is below threshold (lower is better)
            if percentile <= self.max_bsr_percentile:
                filtered_opps.append(opp)
        
        return filtered_opps
    
    def filter_by_profit(self, opportunities: List[ArbitrageOpportunity]) -> List[ArbitrageOpportunity]:
        """Filter opportunities by minimum profit amount"""
        logger.info(f"Filtering opportunities by minimum profit: ${self.min_profit}")
        return [opp for opp in opportunities if opp.profit >= self.min_profit]
    
    def apply_all_filters(self, opportunities: List[ArbitrageOpportunity], 
                         category_percentiles: Optional[Dict[str, Dict[int, float]]] = None) -> List[ArbitrageOpportunity]:
        """
        Apply all filters to opportunities
        
        Args:
            opportunities: List of arbitrage opportunities
            category_percentiles: Dictionary mapping categories to dictionaries of sales rank to percentile
            
        Returns:
            Filtered list of opportunities
        """
        logger.info(f"Applying all filters to {len(opportunities)} opportunities")
        
        # Filter by ROI
        filtered_opps = self.filter_by_roi(opportunities)
        logger.info(f"After ROI filter: {len(filtered_opps)} opportunities")
        
        # Filter by profit
        filtered_opps = self.filter_by_profit(filtered_opps)
        logger.info(f"After profit filter: {len(filtered_opps)} opportunities")
        
        # Filter by reviews
        filtered_opps = self.filter_by_reviews(filtered_opps)
        logger.info(f"After reviews filter: {len(filtered_opps)} opportunities")
        
        # Filter by sales rank if category percentiles provided
        if category_percentiles:
            filtered_opps = self.filter_by_sales_rank(filtered_opps, category_percentiles)
            logger.info(f"After sales rank filter: {len(filtered_opps)} opportunities")
        
        # Sort by ROI (highest first)
        filtered_opps.sort(key=lambda x: x.roi, reverse=True)
        
        return filtered_opps
    
    def _get_sales_rank_percentile(self, sales_rank: int, category: str, 
                                  category_percentiles: Dict[str, Dict[int, float]]) -> float:
        """
        Get percentile for a sales rank in a category
        
        Args:
            sales_rank: Sales rank
            category: Product category
            category_percentiles: Dictionary mapping categories to dictionaries of sales rank to percentile
            
        Returns:
            Percentile (0-100, lower is better)
        """
        # If category not in percentiles, use approximation
        if category not in category_percentiles:
            return self._approximate_percentile(sales_rank, category)
        
        # Get percentiles for this category
        percentiles = category_percentiles[category]
        
        # If exact sales rank exists, return its percentile
        if sales_rank in percentiles:
            return percentiles[sales_rank]
        
        # Otherwise, find closest sales ranks and interpolate
        ranks = sorted(percentiles.keys())
        
        # If sales rank is lower than lowest rank, return lowest percentile
        if sales_rank < ranks[0]:
            return percentiles[ranks[0]]
        
        # If sales rank is higher than highest rank, return highest percentile
        if sales_rank > ranks[-1]:
            return percentiles[ranks[-1]]
        
        # Find ranks that sales_rank falls between
        for i in range(len(ranks) - 1):
            if ranks[i] <= sales_rank <= ranks[i + 1]:
                # Interpolate percentile
                rank1, rank2 = ranks[i], ranks[i + 1]
                perc1, perc2 = percentiles[rank1], percentiles[rank2]
                
                # Linear interpolation
                return perc1 + (perc2 - perc1) * (sales_rank - rank1) / (rank2 - rank1)
        
        # Fallback to approximation
        return self._approximate_percentile(sales_rank, category)
    
    def _approximate_percentile(self, sales_rank: int, category: str) -> float:
        """
        Approximate percentile for a sales rank in a category
        
        Args:
            sales_rank: Sales rank
            category: Product category
            
        Returns:
            Approximate percentile (0-100, lower is better)
        """
        # Simplified approximation based on category
        category_thresholds = {
            "Books": 2000000,
            "Electronics": 500000,
            "Toys": 400000,
            "Video Games": 150000,
            "Kitchen": 600000,
            "Home & Garden": 800000,
            "Beauty": 300000,
            "Clothing": 1000000,
            "Sports & Outdoors": 400000,
            "Office Products": 300000,
            # Default for unknown categories
            "default": 500000
        }
        
        # Get threshold for this category or use default
        for cat_key, threshold in category_thresholds.items():
            if cat_key.lower() in category.lower():
                return (sales_rank / threshold) * 100
        
        # Use default threshold
        return (sales_rank / category_thresholds["default"]) * 100


class SalesRankAnalyzer:
    """Analyzer for Amazon sales rank data"""
    
    def __init__(self):
        """Initialize sales rank analyzer"""
        # Pre-defined percentiles for common categories
        # These would ideally be updated regularly with real data
        self.category_percentiles = {
            "Books": self._generate_book_percentiles(),
            "Electronics": self._generate_electronics_percentiles(),
            "Toys & Games": self._generate_toys_percentiles(),
            "Home & Kitchen": self._generate_home_percentiles(),
        }
    
    def get_category_percentiles(self) -> Dict[str, Dict[int, float]]:
        """Get category percentiles dictionary"""
        return self.category_percentiles
    
    def _generate_book_percentiles(self) -> Dict[int, float]:
        """Generate percentiles for Books category"""
        return {
            100: 0.01,      # Top 0.01%
            500: 0.05,      # Top 0.05%
            1000: 0.1,      # Top 0.1%
            5000: 0.5,      # Top 0.5%
            10000: 1.0,     # Top 1%
            20000: 2.0,     # Top 2%
            50000: 5.0,     # Top 5%
            100000: 10.0,   # Top 10%
            200000: 20.0,   # Top 20%
            500000: 50.0,   # Top 50%
            1000000: 80.0,  # Top 80%
            2000000: 95.0,  # Top 95%
            5000000: 99.0   # Top 99%
        }
    
    def _generate_electronics_percentiles(self) -> Dict[int, float]:
        """Generate percentiles for Electronics category"""
        return {
            100: 0.01,      # Top 0.01%
            500: 0.05,      # Top 0.05%
            1000: 0.1,      # Top 0.1%
            2500: 0.5,      # Top 0.5%
            5000: 1.0,      # Top 1%
            10000: 2.0,     # Top 2%
            25000: 5.0,     # Top 5%
            50000: 10.0,    # Top 10%
            100000: 20.0,   # Top 20%
            250000: 50.0,   # Top 50%
            500000: 80.0,   # Top 80%
            1000000: 95.0,  # Top 95%
            2000000: 99.0   # Top 99%
        }
    
    def _generate_toys_percentiles(self) -> Dict[int, float]:
        """Generate percentiles for Toys & Games category"""
        return {
            100: 0.01,      # Top 0.01%
            250: 0.05,      # Top 0.05%
            500: 0.1,       # Top 0.1%
            1000: 0.5,      # Top 0.5%
            2500: 1.0,      # Top 1%
            5000: 2.0,      # Top 2%
            10000: 5.0,     # Top 5%
            25000: 10.0,    # Top 10%
            50000: 20.0,    # Top 20%
            100000: 50.0,   # Top 50%
            200000: 80.0,   # Top 80%
            400000: 95.0,   # Top 95%
            800000: 99.0    # Top 99%
        }
    
    def _generate_home_percentiles(self) -> Dict[int, float]:
        """Generate percentiles for Home & Kitchen category"""
        return {
            100: 0.01,      # Top 0.01%
            250: 0.05,      # Top 0.05%
            500: 0.1,       # Top 0.1%
            1000: 0.5,      # Top 0.5%
            2500: 1.0,      # Top 1%
            5000: 2.0,      # Top 2%
            15000: 5.0,     # Top 5%
            30000: 10.0,    # Top 10%
            60000: 20.0,    # Top 20%
            150000: 50.0,   # Top 50%
            300000: 80.0,   # Top 80%
            600000: 95.0,   # Top 95%
            1200000: 99.0   # Top 99%
        }
