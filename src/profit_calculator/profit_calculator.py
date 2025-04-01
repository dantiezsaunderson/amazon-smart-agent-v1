"""
Profit calculation module
Calculates potential profit and ROI for arbitrage opportunities
"""

import os
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import math

from src.retail_scanners import RetailProduct
from src.amazon import AmazonProduct

logger = logging.getLogger(__name__)

@dataclass
class FulfillmentCost:
    """Data class to store fulfillment cost information"""
    weight_handling: float  # Weight handling fee
    order_handling: float   # Order handling fee
    pick_pack: float        # Pick and pack fee
    thirty_day_storage: float  # 30-day storage fee per cubic foot
    
    @classmethod
    def get_fba_costs(cls, weight_lb: float, length_in: float, width_in: float, height_in: float) -> 'FulfillmentCost':
        """
        Calculate FBA fulfillment costs based on product dimensions and weight
        
        Args:
            weight_lb: Weight in pounds
            length_in: Length in inches
            width_in: Width in inches
            height_in: Height in inches
            
        Returns:
            FulfillmentCost object with calculated costs
        """
        # Calculate dimensional weight
        cubic_feet = (length_in * width_in * height_in) / 1728  # Convert cubic inches to cubic feet
        
        # Determine size tier
        if max(length_in, width_in, height_in) <= 15 and min(length_in, width_in, height_in) <= 0.75 and weight_lb <= 0.5:
            size_tier = "Small Standard"
        elif max(length_in, width_in, height_in) <= 18 and min(length_in, width_in, height_in) <= 8 and weight_lb <= 20:
            size_tier = "Large Standard"
        elif max(length_in, width_in, height_in) <= 60 and min(length_in, width_in, height_in) <= 30 and weight_lb <= 70:
            size_tier = "Small Oversize"
        elif max(length_in, width_in, height_in) <= 108 and weight_lb <= 150:
            size_tier = "Medium Oversize"
        elif max(length_in, width_in, height_in) <= 108 and weight_lb <= 150:
            size_tier = "Large Oversize"
        else:
            size_tier = "Special Oversize"
        
        # Calculate fees based on size tier
        if size_tier == "Small Standard":
            weight_handling = 2.16 if weight_lb <= 0.5 else 2.48
            order_handling = 0.0
            pick_pack = 0.99
            thirty_day_storage = 0.75 * cubic_feet
        elif size_tier == "Large Standard":
            if weight_lb <= 1:
                weight_handling = 2.73
            elif weight_lb <= 2:
                weight_handling = 3.47
            else:
                weight_handling = 4.21 + (weight_lb - 2) * 0.38
            order_handling = 0.0
            pick_pack = 1.20
            thirty_day_storage = 0.75 * cubic_feet
        elif size_tier == "Small Oversize":
            weight_handling = 8.26 + (weight_lb - 20) * 0.38 if weight_lb > 20 else 8.26
            order_handling = 0.0
            pick_pack = 4.72
            thirty_day_storage = 0.48 * cubic_feet
        elif size_tier == "Medium Oversize":
            weight_handling = 11.37 + (weight_lb - 40) * 0.39 if weight_lb > 40 else 11.37
            order_handling = 0.0
            pick_pack = 5.42
            thirty_day_storage = 0.48 * cubic_feet
        elif size_tier == "Large Oversize":
            weight_handling = 76.57 + (weight_lb - 90) * 0.79 if weight_lb > 90 else 76.57
            order_handling = 0.0
            pick_pack = 10.53
            thirty_day_storage = 0.48 * cubic_feet
        else:  # Special Oversize
            weight_handling = 137.32 + (weight_lb - 90) * 0.91 if weight_lb > 90 else 137.32
            order_handling = 0.0
            pick_pack = 13.34
            thirty_day_storage = 0.48 * cubic_feet
        
        return cls(
            weight_handling=weight_handling,
            order_handling=order_handling,
            pick_pack=pick_pack,
            thirty_day_storage=thirty_day_storage
        )
    
    @classmethod
    def get_fbm_costs(cls, weight_lb: float) -> 'FulfillmentCost':
        """
        Calculate FBM fulfillment costs based on product weight
        
        Args:
            weight_lb: Weight in pounds
            
        Returns:
            FulfillmentCost object with calculated costs
        """
        # Simplified FBM cost calculation
        # In reality, this would depend on shipping carrier, distance, etc.
        if weight_lb <= 1:
            shipping_cost = 3.99
        elif weight_lb <= 2:
            shipping_cost = 5.99
        elif weight_lb <= 5:
            shipping_cost = 8.99
        elif weight_lb <= 10:
            shipping_cost = 12.99
        else:
            shipping_cost = 12.99 + (weight_lb - 10) * 0.50
        
        # For FBM, we use weight_handling to store the shipping cost
        return cls(
            weight_handling=shipping_cost,
            order_handling=0.0,
            pick_pack=0.0,
            thirty_day_storage=0.0
        )

@dataclass
class ArbitrageCosts:
    """Data class to store all costs associated with an arbitrage opportunity"""
    buy_price: float  # Purchase price from retail store
    amazon_fees: float  # Amazon referral fee (percentage of sale price)
    fulfillment_cost: float  # Total fulfillment cost (FBA or FBM)
    shipping_to_amazon: float  # Cost to ship to Amazon (FBA only)
    other_costs: float  # Other costs (packaging, labels, etc.)
    
    @property
    def total_cost(self) -> float:
        """Calculate total cost"""
        return self.buy_price + self.amazon_fees + self.fulfillment_cost + self.shipping_to_amazon + self.other_costs

@dataclass
class ArbitrageOpportunity:
    """Data class to store arbitrage opportunity information"""
    retail_product: RetailProduct
    amazon_product: AmazonProduct
    costs: ArbitrageCosts
    fulfillment_method: str  # 'FBA' or 'FBM'
    
    @property
    def profit(self) -> float:
        """Calculate profit"""
        return self.amazon_product.price - self.costs.total_cost
    
    @property
    def roi(self) -> float:
        """Calculate ROI as percentage"""
        if self.costs.total_cost == 0:
            return 0.0
        return (self.profit / self.costs.total_cost) * 100
    
    @property
    def is_profitable(self) -> bool:
        """Check if opportunity is profitable"""
        return self.profit > 0
    
    @property
    def meets_roi_threshold(self, threshold: float = 40.0) -> bool:
        """Check if opportunity meets ROI threshold"""
        return self.roi >= threshold


class ProfitCalculator:
    """Calculator for arbitrage profit and ROI"""
    
    def __init__(self, amazon_fee_percentage: float = 15.0, default_weight_lb: float = 1.0,
                 default_dimensions: Tuple[float, float, float] = (8, 6, 2),
                 shipping_to_amazon_per_lb: float = 0.50, other_costs_percentage: float = 2.0):
        """
        Initialize profit calculator
        
        Args:
            amazon_fee_percentage: Amazon referral fee percentage
            default_weight_lb: Default weight in pounds when not provided
            default_dimensions: Default dimensions (length, width, height) in inches when not provided
            shipping_to_amazon_per_lb: Cost per pound to ship to Amazon FBA
            other_costs_percentage: Other costs as percentage of buy price
        """
        self.amazon_fee_percentage = amazon_fee_percentage
        self.default_weight_lb = default_weight_lb
        self.default_dimensions = default_dimensions
        self.shipping_to_amazon_per_lb = shipping_to_amazon_per_lb
        self.other_costs_percentage = other_costs_percentage
    
    def calculate_opportunity(self, retail_product: RetailProduct, amazon_product: AmazonProduct,
                              weight_lb: Optional[float] = None, dimensions: Optional[Tuple[float, float, float]] = None,
                              fulfillment_method: str = 'FBA') -> ArbitrageOpportunity:
        """
        Calculate arbitrage opportunity
        
        Args:
            retail_product: RetailProduct object
            amazon_product: AmazonProduct object
            weight_lb: Weight in pounds (optional)
            dimensions: Dimensions (length, width, height) in inches (optional)
            fulfillment_method: Fulfillment method ('FBA' or 'FBM')
            
        Returns:
            ArbitrageOpportunity object with calculated profit and ROI
        """
        # Use provided values or defaults
        weight = weight_lb if weight_lb is not None else self.default_weight_lb
        dims = dimensions if dimensions is not None else self.default_dimensions
        
        # Calculate Amazon fees
        amazon_fees = (amazon_product.price * self.amazon_fee_percentage) / 100
        
        # Calculate fulfillment costs
        if fulfillment_method == 'FBA':
            fulfillment = FulfillmentCost.get_fba_costs(weight, dims[0], dims[1], dims[2])
            fulfillment_cost = fulfillment.weight_handling + fulfillment.order_handling + fulfillment.pick_pack
            shipping_to_amazon = weight * self.shipping_to_amazon_per_lb
        else:  # FBM
            fulfillment = FulfillmentCost.get_fbm_costs(weight)
            fulfillment_cost = fulfillment.weight_handling  # For FBM, this is the shipping cost
            shipping_to_amazon = 0.0
        
        # Calculate other costs
        other_costs = (retail_product.price * self.other_costs_percentage) / 100
        
        # Create costs object
        costs = ArbitrageCosts(
            buy_price=retail_product.price,
            amazon_fees=amazon_fees,
            fulfillment_cost=fulfillment_cost,
            shipping_to_amazon=shipping_to_amazon,
            other_costs=other_costs
        )
        
        # Create opportunity object
        opportunity = ArbitrageOpportunity(
            retail_product=retail_product,
            amazon_product=amazon_product,
            costs=costs,
            fulfillment_method=fulfillment_method
        )
        
        return opportunity
    
    def calculate_bulk_opportunities(self, retail_products: List[RetailProduct], 
                                    amazon_products: Dict[str, AmazonProduct],
                                    fulfillment_method: str = 'FBA') -> List[ArbitrageOpportunity]:
        """
        Calculate arbitrage opportunities for multiple products
        
        Args:
            retail_products: List of RetailProduct objects
            amazon_products: Dictionary of AmazonProduct objects keyed by identifier (UPC, SKU, etc.)
            fulfillment_method: Fulfillment method ('FBA' or 'FBM')
            
        Returns:
            List of ArbitrageOpportunity objects
        """
        opportunities = []
        
        for retail_product in retail_products:
            # Try to find matching Amazon product by UPC or SKU
            amazon_product = None
            
            if retail_product.upc and retail_product.upc in amazon_products:
                amazon_product = amazon_products[retail_product.upc]
            elif retail_product.sku and retail_product.sku in amazon_products:
                amazon_product = amazon_products[retail_product.sku]
            
            if amazon_product:
                # Calculate opportunity
                opportunity = self.calculate_opportunity(
                    retail_product=retail_product,
                    amazon_product=amazon_product,
                    fulfillment_method=fulfillment_method
                )
                
                opportunities.append(opportunity)
        
        return opportunities
    
    def find_best_opportunities(self, opportunities: List[ArbitrageOpportunity], 
                               min_roi: float = 40.0, 
                               max_reviews: Optional[int] = 20,
                               min_bsr_percentile: Optional[float] = 5.0) -> List[ArbitrageOpportunity]:
        """
        Find best arbitrage opportunities based on criteria
        
        Args:
            opportunities: List of ArbitrageOpportunity objects
            min_roi: Minimum ROI percentage
            max_reviews: Maximum number of reviews (None to ignore)
            min_bsr_percentile: Minimum BSR percentile (None to ignore)
            
        Returns:
            Filtered list of ArbitrageOpportunity objects
        """
        filtered_opportunities = []
        
        for opportunity in opportunities:
            # Check ROI
            if opportunity.roi < min_roi:
                continue
            
            # Check reviews if specified
            if max_reviews is not None and opportunity.amazon_product.review_count is not None:
                if opportunity.amazon_product.review_count > max_reviews:
                    continue
            
            # Check BSR percentile if specified
            if min_bsr_percentile is not None and opportunity.amazon_product.sales_rank is not None:
                # This would require additional logic to calculate BSR percentile
                # For now, we'll assume the sales_rank is already a percentile
                pass
            
            filtered_opportunities.append(opportunity)
        
        # Sort by ROI (highest first)
        filtered_opportunities.sort(key=lambda x: x.roi, reverse=True)
        
        return filtered_opportunities
