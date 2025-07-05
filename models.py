from app import db
from datetime import datetime
import json

class ScrapingJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(50), default='pending')  # pending, running, paused, completed, failed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    
    # Progress tracking fields
    total_products_found = db.Column(db.Integer, default=0)
    products_processed = db.Column(db.Integer, default=0)
    products_ai_enhanced = db.Column(db.Integer, default=0)
    current_page = db.Column(db.Integer, default=1)
    total_pages = db.Column(db.Integer, default=1)
    current_step = db.Column(db.String(100), default='Starting')  # Starting, Scraping, AI Enhancement, Completing
    step_detail = db.Column(db.String(200))  # Detailed status message
    
    # Relationship to products
    products = db.relationship('Product', backref='job', lazy=True, cascade='all, delete-orphan')

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('scraping_job.id'), nullable=False)
    
    # Basic product information
    title = db.Column(db.String(500))
    description = db.Column(db.Text)
    price = db.Column(db.String(100))
    original_price = db.Column(db.String(100))
    currency = db.Column(db.String(10))
    availability = db.Column(db.String(100))
    
    # Product details
    brand = db.Column(db.String(200))
    category = db.Column(db.String(200))
    subcategory = db.Column(db.String(200))
    sku = db.Column(db.String(100))
    rating = db.Column(db.Float)
    review_count = db.Column(db.Integer)
    
    # Images and media
    main_image_url = db.Column(db.String(1000))
    image_urls = db.Column(db.Text)  # JSON array of URLs
    
    # AI-enhanced fields
    ai_summary = db.Column(db.Text)
    ai_tags = db.Column(db.Text)  # JSON array of tags
    ai_normalized_category = db.Column(db.String(200))
    ai_normalized_brand = db.Column(db.String(200))
    ai_woocommerce_type = db.Column(db.String(50))  # simple, variable, grouped
    
    # Metadata
    source_url = db.Column(db.String(1000))
    scraped_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert product to dictionary for export"""
        image_urls = []
        if self.image_urls:
            try:
                image_urls = json.loads(self.image_urls)
            except:
                image_urls = []
                
        ai_tags = []
        if self.ai_tags:
            try:
                ai_tags = json.loads(self.ai_tags)
            except:
                ai_tags = []
        
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'ai_summary': self.ai_summary,
            'price': self.price,
            'original_price': self.original_price,
            'currency': self.currency,
            'availability': self.availability,
            'brand': self.brand,
            'ai_normalized_brand': self.ai_normalized_brand,
            'category': self.category,
            'subcategory': self.subcategory,
            'ai_normalized_category': self.ai_normalized_category,
            'sku': self.sku,
            'rating': self.rating,
            'review_count': self.review_count,
            'main_image_url': self.main_image_url,
            'image_urls': image_urls,
            'ai_tags': ai_tags,
            'ai_woocommerce_type': self.ai_woocommerce_type,
            'source_url': self.source_url,
            'scraped_at': self.scraped_at.isoformat() if self.scraped_at else None
        }
