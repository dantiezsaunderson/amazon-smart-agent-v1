"""
Database module for product storage
Provides functionality to store and retrieve arbitrage opportunities
"""

import os
import logging
import json
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import sqlite3
from dataclasses import asdict, dataclass

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session

from src.retail_scanners import RetailProduct
from src.amazon import AmazonProduct
from src.profit_calculator import ArbitrageOpportunity, ArbitrageCosts

logger = logging.getLogger(__name__)

Base = declarative_base()

class RetailProductModel(Base):
    """SQLAlchemy model for retail products"""
    __tablename__ = 'retail_products'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    original_price = Column(Float, nullable=True)
    url = Column(String(255), nullable=False)
    image_url = Column(String(255), nullable=True)
    brand = Column(String(100), nullable=True)
    category = Column(String(100), nullable=True)
    upc = Column(String(50), nullable=True, index=True)
    sku = Column(String(50), nullable=True, index=True)
    description = Column(Text, nullable=True)
    store = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with opportunities
    opportunities = relationship("ArbitrageOpportunityModel", back_populates="retail_product")
    
    @classmethod
    def from_retail_product(cls, product: RetailProduct) -> 'RetailProductModel':
        """Create model from RetailProduct object"""
        return cls(
            product_id=product.product_id,
            title=product.title,
            price=product.price,
            original_price=product.original_price,
            url=product.url,
            image_url=product.image_url,
            brand=product.brand,
            category=product.category,
            upc=product.upc,
            sku=product.sku,
            description=product.description,
            store=product.store
        )
    
    def to_retail_product(self) -> RetailProduct:
        """Convert model to RetailProduct object"""
        return RetailProduct(
            product_id=self.product_id,
            title=self.title,
            price=self.price,
            original_price=self.original_price,
            url=self.url,
            image_url=self.image_url,
            brand=self.brand,
            category=self.category,
            upc=self.upc,
            sku=self.sku,
            description=self.description,
            store=self.store
        )


class AmazonProductModel(Base):
    """SQLAlchemy model for Amazon products"""
    __tablename__ = 'amazon_products'
    
    id = Column(Integer, primary_key=True)
    asin = Column(String(20), nullable=False, index=True, unique=True)
    title = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    sales_rank = Column(Integer, nullable=True)
    category = Column(String(100), nullable=True)
    review_count = Column(Integer, nullable=True)
    rating = Column(Float, nullable=True)
    image_url = Column(String(255), nullable=True)
    url = Column(String(255), nullable=True)
    features = Column(Text, nullable=True)  # Stored as JSON
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with opportunities
    opportunities = relationship("ArbitrageOpportunityModel", back_populates="amazon_product")
    
    @classmethod
    def from_amazon_product(cls, product: AmazonProduct) -> 'AmazonProductModel':
        """Create model from AmazonProduct object"""
        return cls(
            asin=product.asin,
            title=product.title,
            price=product.price,
            sales_rank=product.sales_rank,
            category=product.category,
            review_count=product.review_count,
            rating=product.rating,
            image_url=product.image_url,
            url=product.url,
            features=json.dumps(product.features) if product.features else None,
            description=product.description
        )
    
    def to_amazon_product(self) -> AmazonProduct:
        """Convert model to AmazonProduct object"""
        return AmazonProduct(
            asin=self.asin,
            title=self.title,
            price=self.price,
            sales_rank=self.sales_rank,
            category=self.category,
            review_count=self.review_count,
            rating=self.rating,
            image_url=self.image_url,
            url=self.url,
            features=json.loads(self.features) if self.features else None,
            description=self.description
        )


class ArbitrageCostsModel(Base):
    """SQLAlchemy model for arbitrage costs"""
    __tablename__ = 'arbitrage_costs'
    
    id = Column(Integer, primary_key=True)
    opportunity_id = Column(Integer, ForeignKey('arbitrage_opportunities.id'), nullable=False)
    buy_price = Column(Float, nullable=False)
    amazon_fees = Column(Float, nullable=False)
    fulfillment_cost = Column(Float, nullable=False)
    shipping_to_amazon = Column(Float, nullable=False)
    other_costs = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with opportunity
    opportunity = relationship("ArbitrageOpportunityModel", back_populates="costs")
    
    @classmethod
    def from_arbitrage_costs(cls, costs: ArbitrageCosts) -> 'ArbitrageCostsModel':
        """Create model from ArbitrageCosts object"""
        return cls(
            buy_price=costs.buy_price,
            amazon_fees=costs.amazon_fees,
            fulfillment_cost=costs.fulfillment_cost,
            shipping_to_amazon=costs.shipping_to_amazon,
            other_costs=costs.other_costs
        )
    
    def to_arbitrage_costs(self) -> ArbitrageCosts:
        """Convert model to ArbitrageCosts object"""
        return ArbitrageCosts(
            buy_price=self.buy_price,
            amazon_fees=self.amazon_fees,
            fulfillment_cost=self.fulfillment_cost,
            shipping_to_amazon=self.shipping_to_amazon,
            other_costs=self.other_costs
        )


class ArbitrageOpportunityModel(Base):
    """SQLAlchemy model for arbitrage opportunities"""
    __tablename__ = 'arbitrage_opportunities'
    
    id = Column(Integer, primary_key=True)
    retail_product_id = Column(Integer, ForeignKey('retail_products.id'), nullable=False)
    amazon_product_id = Column(Integer, ForeignKey('amazon_products.id'), nullable=False)
    fulfillment_method = Column(String(10), nullable=False)  # 'FBA' or 'FBM'
    profit = Column(Float, nullable=False)
    roi = Column(Float, nullable=False)
    is_profitable = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    retail_product = relationship("RetailProductModel", back_populates="opportunities")
    amazon_product = relationship("AmazonProductModel", back_populates="opportunities")
    costs = relationship("ArbitrageCostsModel", back_populates="opportunity", uselist=False)
    
    @classmethod
    def from_arbitrage_opportunity(cls, opportunity: ArbitrageOpportunity, 
                                  retail_product_id: int, amazon_product_id: int) -> 'ArbitrageOpportunityModel':
        """Create model from ArbitrageOpportunity object"""
        return cls(
            retail_product_id=retail_product_id,
            amazon_product_id=amazon_product_id,
            fulfillment_method=opportunity.fulfillment_method,
            profit=opportunity.profit,
            roi=opportunity.roi,
            is_profitable=opportunity.is_profitable
        )


class ProductDatabase:
    """Database manager for product storage"""
    
    def __init__(self, db_path: str = None, db_url: str = None):
        """
        Initialize database manager
        
        Args:
            db_path: Path to SQLite database file (for testing)
            db_url: SQLAlchemy database URL (e.g., 'sqlite:///database/products.db')
        """
        # Handle special case for in-memory database (for testing)
        if db_path == ":memory:":
            db_url = "sqlite:///:memory:"
        # Use provided db_url if specified
        elif db_url is not None:
            pass
        # Use environment variable if available
        elif os.getenv('DATABASE_URL'):
            db_url = os.getenv('DATABASE_URL')
        # Otherwise, determine appropriate path based on environment
        else:
            if os.getenv('RENDER') == 'true':
                # Use /tmp directory on Render
                db_path = os.path.join('/tmp', 'amazon_smart_agent.db')
                db_url = f'sqlite:///{db_path}'
                logger.info(f"Running on Render, using database at {db_path}")
            else:
                # Use local path for development
                db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
                db_path = os.path.join(db_dir, 'amazon_smart_agent.db')
                db_url = f'sqlite:///{db_path}'
                
                # Create directory if it doesn't exist
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"Using database at {db_path}")
        
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
        
        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.Session()
    
    def add_retail_product(self, product: RetailProduct) -> RetailProductModel:
        """
        Add retail product to database
        
        Args:
            product: RetailProduct object
            
        Returns:
            RetailProductModel object
        """
        session = self.get_session()
        try:
            # Check if product already exists
            existing = session.query(RetailProductModel).filter_by(
                product_id=product.product_id,
                store=product.store
            ).first()
            
            if existing:
                # Update existing product
                existing.title = product.title
                existing.price = product.price
                existing.original_price = product.original_price
                existing.url = product.url
                existing.image_url = product.image_url
                existing.brand = product.brand
                existing.category = product.category
                existing.upc = product.upc
                existing.sku = product.sku
                existing.description = product.description
                existing.updated_at = datetime.utcnow()
                model = existing
            else:
                # Create new product
                model = RetailProductModel.from_retail_product(product)
                session.add(model)
            
            session.commit()
            return model
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding retail product: {e}")
            raise
        finally:
            session.close()
    
    def add_amazon_product(self, product: AmazonProduct) -> AmazonProductModel:
        """
        Add Amazon product to database
        
        Args:
            product: AmazonProduct object
            
        Returns:
            AmazonProductModel object
        """
        session = self.get_session()
        try:
            # Check if product already exists
            existing = session.query(AmazonProductModel).filter_by(asin=product.asin).first()
            
            if existing:
                # Update existing product
                existing.title = product.title
                existing.price = product.price
                existing.sales_rank = product.sales_rank
                existing.category = product.category
                existing.review_count = product.review_count
                existing.rating = product.rating
                existing.image_url = product.image_url
                existing.url = product.url
                existing.features = json.dumps(product.features) if product.features else None
                existing.description = product.description
                existing.updated_at = datetime.utcnow()
                model = existing
            else:
                # Create new product
                model = AmazonProductModel.from_amazon_product(product)
                session.add(model)
            
            session.commit()
            return model
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding Amazon product: {e}")
            raise
        finally:
            session.close()
    
    def add_arbitrage_opportunity(self, opportunity: ArbitrageOpportunity) -> ArbitrageOpportunityModel:
        """
        Add arbitrage opportunity to database
        
        Args:
            opportunity: ArbitrageOpportunity object
            
        Returns:
            ArbitrageOpportunityModel object
        """
        session = self.get_session()
        try:
            # Add retail product
            retail_model = self.add_retail_product(opportunity.retail_product)
            
            # Add Amazon product
            amazon_model = self.add_amazon_product(opportunity.amazon_product)
            
            # Check if opportunity already exists
            existing = session.query(ArbitrageOpportunityModel).filter_by(
                retail_product_id=retail_model.id,
                amazon_product_id=amazon_model.id
            ).first()
            
            if existing:
                # Update existing opportunity
                existing.fulfillment_method = opportunity.fulfillment_method
                existing.profit = opportunity.profit
                existing.roi = opportunity.roi
                existing.is_profitable = opportunity.is_profitable
                existing.updated_at = datetime.utcnow()
                
                # Update costs
                if existing.costs:
                    costs_model = existing.costs
                    costs_model.buy_price = opportunity.costs.buy_price
                    costs_model.amazon_fees = opportunity.costs.amazon_fees
                    costs_model.fulfillment_cost = opportunity.costs.fulfillment_cost
                    costs_model.shipping_to_amazon = opportunity.costs.shipping_to_amazon
                    costs_model.other_costs = opportunity.costs.other_costs
                else:
                    costs_model = ArbitrageCostsModel.from_arbitrage_costs(opportunity.costs)
                    costs_model.opportunity = existing
                    session.add(costs_model)
                
                model = existing
            else:
                # Create new opportunity
                model = ArbitrageOpportunityModel.from_arbitrage_opportunity(
                    opportunity, retail_model.id, amazon_model.id
                )
                session.add(model)
                
                # Add costs
                costs_model = ArbitrageCostsModel.from_arbitrage_costs(opportunity.costs)
                costs_model.opportunity = model
                session.add(costs_model)
            
            session.commit()
            return model
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding arbitrage opportunity: {e}")
            raise
        finally:
            session.close()
    
    def add_opportunities(self, opportunities: List[ArbitrageOpportunity]) -> List[ArbitrageOpportunityModel]:
        """
        Add multiple arbitrage opportunities to database
        
        Args:
            opportunities: List of ArbitrageOpportunity objects
            
        Returns:
            List of ArbitrageOpportunityModel objects
        """
        models = []
        for opportunity in opportunities:
            try:
                model = self.add_arbitrage_opportunity(opportunity)
                models.append(model)
            except Exception as e:
                logger.error(f"Error adding opportunity: {e}")
        
        return models
    
    def get_opportunities(self, min_roi: Optional[float] = None, 
                         min_profit: Optional[float] = None,
                         limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get arbitrage opportunities from database
        
        Args:
            min_roi: Minimum ROI percentage
            min_profit: Minimum profit amount
            limit: Maximum number of opportunities to return
            
        Returns:
            List of opportunity dictionaries
        """
        session = self.get_session()
        try:
            query = session.query(ArbitrageOpportunityModel)
            
            # Apply filters
            if min_roi is not None:
                query = query.filter(ArbitrageOpportunityModel.roi >= min_roi)
            
            if min_profit is not None:
                query = query.filter(ArbitrageOpportunityModel.profit >= min_profit)
            
            # Order by ROI (highest first)
            query = query.order_by(ArbitrageOpportunityModel.roi.desc())
            
            # Limit results
            query = query.limit(limit)
            
            # Execute query
            models = query.all()
            
            # Convert to dictionaries
            opportunities = []
            for model in models:
                opportunity = {
                    'id': model.id,
                    'retail_product': model.retail_product.to_retail_product(),
                    'amazon_product': model.amazon_product.to_amazon_product(),
                    'fulfillment_method': model.fulfillment_method,
                    'profit': model.profit,
                    'roi': model.roi,
                    'is_profitable': model.is_profitable,
                    'costs': model.costs.to_arbitrage_costs() if model.costs else None,
                    'created_at': model.created_at,
                    'updated_at': model.updated_at
                }
                opportunities.append(opportunity)
            
            return opportunities
        except Exception as e:
            logger.error(f"Error getting opportunities: {e}")
            return []
        finally:
            session.close()
    
    def get_opportunity_by_id(self, opportunity_id: int) -> Optional[Dict[str, Any]]:
        """
        Get arbitrage opportunity by ID
        
        Args:
            opportunity_id: Opportunity ID
            
        Returns:
            Opportunity dictionary or None if not found
        """
        session = self.get_session()
        try:
            model = session.query(ArbitrageOpportunityModel).filter_by(id=opportunity_id).first()
            
            if not model:
                return None
            
            opportunity = {
                'id': model.id,
                'retail_product': model.retail_product.to_retail_product(),
                'amazon_product': model.amazon_product.to_amazon_product(),
                'fulfillment_method': model.fulfillment_method,
                'profit': model.profit,
                'roi': model.roi,
                'is_profitable': model.is_profitable,
                'costs': model.costs.to_arbitrage_costs() if model.costs else None,
                'created_at': model.created_at,
                'updated_at': model.updated_at
            }
            
            return opportunity
        except Exception as e:
            logger.error(f"Error getting opportunity by ID: {e}")
            return None
        finally:
            session.close()
    
    def get_opportunities_by_store(self, store: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get arbitrage opportunities by retail store
        
        Args:
            store: Retail store name
            limit: Maximum number of opportunities to return
            
        Returns:
            List of opportunity dictionaries
        """
        session = self.get_session()
        try:
            query = session.query(ArbitrageOpportunityModel).join(
                RetailProductModel, ArbitrageOpportunityModel.retail_product_id == RetailProductModel.id
            ).filter(RetailProductModel.store == store)
            
            # Order by ROI (highest first)
            query = query.order_by(ArbitrageOpportunityModel.roi.desc())
            
            # Limit results
            query = query.limit(limit)
            
            # Execute query
            models = query.all()
            
            # Convert to dictionaries
            opportunities = []
            for model in models:
                opportunity = {
                    'id': model.id,
                    'retail_product': model.retail_product.to_retail_product(),
                    'amazon_product': model.amazon_product.to_amazon_product(),
                    'fulfillment_method': model.fulfillment_method,
                    'profit': model.profit,
                    'roi': model.roi,
                    'is_profitable': model.is_profitable,
                    'costs': model.costs.to_arbitrage_costs() if model.costs else None,
                    'created_at': model.created_at,
                    'updated_at': model.updated_at
                }
                opportunities.append(opportunity)
            
            return opportunities
        except Exception as e:
            logger.error(f"Error getting opportunities by store: {e}")
            return []
        finally:
            session.close()
    
    def get_today_opportunities(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get arbitrage opportunities created today
        
        Args:
            limit: Maximum number of opportunities to return
            
        Returns:
            List of opportunity dictionaries
        """
        session = self.get_session()
        try:
            today = datetime.utcnow().date()
            query = session.query(ArbitrageOpportunityModel).filter(
                ArbitrageOpportunityModel.created_at >= today
            )
            
            # Order by ROI (highest first)
            query = query.order_by(ArbitrageOpportunityModel.roi.desc())
            
            # Limit results
            query = query.limit(limit)
            
            # Execute query
            models = query.all()
            
            # Convert to dictionaries
            opportunities = []
            for model in models:
                opportunity = {
                    'id': model.id,
                    'retail_product': model.retail_product.to_retail_product(),
                    'amazon_product': model.amazon_product.to_amazon_product(),
                    'fulfillment_method': model.fulfillment_method,
                    'profit': model.profit,
                    'roi': model.roi,
                    'is_profitable': model.is_profitable,
                    'costs': model.costs.to_arbitrage_costs() if model.costs else None,
                    'created_at': model.created_at,
                    'updated_at': model.updated_at
                }
                opportunities.append(opportunity)
            
            return opportunities
        except Exception as e:
            logger.error(f"Error getting today's opportunities: {e}")
            return []
        finally:
            session.close()
    
    def delete_opportunity(self, opportunity_id: int) -> bool:
        """
        Delete arbitrage opportunity by ID
        
        Args:
            opportunity_id: Opportunity ID
            
        Returns:
            True if successful, False otherwise
        """
        session = self.get_session()
        try:
            model = session.query(ArbitrageOpportunityModel).filter_by(id=opportunity_id).first()
            
            if not model:
                return False
            
            # Delete costs
            if model.costs:
                session.delete(model.costs)
            
            # Delete opportunity
            session.delete(model)
            session.commit()
            
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting opportunity: {e}")
            return False
        finally:
            session.close()
