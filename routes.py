from flask import render_template, request, jsonify, send_file, flash, redirect, url_for
from app import app, db
from models import ScrapingJob, Product
from scraper import ProductScraper
from ai_enhancer import AIEnhancer
from export_utils import ExportUtils
import threading
import logging
import os
import time
from datetime import datetime

@app.route('/')
def index():
    """Main page with scraping form"""
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "message": "AI Product Scraper is running"})

@app.route('/scrape', methods=['POST'])
def start_scrape():
    """Start a new scraping job"""
    try:
        url = request.form.get('url', '').strip()
        if not url:
            flash('Please provide a valid URL', 'error')
            return redirect(url_for('index'))
        
        # Create new job
        job = ScrapingJob(url=url, status='pending')
        db.session.add(job)
        db.session.commit()
        
        # Start scraping in background thread
        thread = threading.Thread(target=run_scraping_job, args=(job.id,))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'job_id': job.id,
            'message': 'Scraping job started successfully'
        })
        
    except Exception as e:
        logging.error(f"Error starting scrape job: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/job/<int:job_id>/status')
def job_status(job_id):
    """Get job status and results"""
    try:
        job = ScrapingJob.query.get_or_404(job_id)
        
        response = {
            'id': job.id,
            'url': job.url,
            'status': job.status,
            'created_at': job.created_at.isoformat(),
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'error_message': job.error_message,
            'product_count': len(job.products),
            # Enhanced progress tracking fields
            'total_products_found': job.total_products_found or 0,
            'products_processed': job.products_processed or 0,
            'products_ai_enhanced': job.products_ai_enhanced or 0,
            'current_page': job.current_page or 1,
            'total_pages': job.total_pages or 1,
            'current_step': job.current_step or 'Starting',
            'step_detail': job.step_detail or 'Initializing...'
        }
        
        if job.status == 'completed':
            # Include product data
            response['products'] = [product.to_dict() for product in job.products]
        
        return jsonify(response)
        
    except Exception as e:
        logging.error(f"Error getting job status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/results/<int:job_id>')
def results(job_id):
    """Display results page"""
    job = ScrapingJob.query.get_or_404(job_id)
    return render_template('results.html', job=job)

@app.route('/export/<int:job_id>/<format>')
def export_job(job_id, format):
    """Export job results in specified format"""
    try:
        job = ScrapingJob.query.get_or_404(job_id)
        
        if not job.products:
            return jsonify({'error': 'No products found for this job'}), 404
        
        export_utils = ExportUtils()
        products_data = [product.to_dict() for product in job.products]
        
        if format == 'csv':
            file_path = export_utils.export_to_csv(products_data, job_id)
        elif format == 'json':
            file_path = export_utils.export_to_json(products_data, job_id)
        elif format == 'xml':
            file_path = export_utils.export_to_xml(products_data, job_id)
        else:
            return jsonify({'error': 'Invalid export format'}), 400
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=f'products_{job_id}.{format}'
        )
        
    except Exception as e:
        logging.error(f"Error exporting job {job_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/export/product/<int:product_id>/<format>')
def export_product(product_id, format):
    """Export single product in specified format"""
    try:
        product = Product.query.get_or_404(product_id)
        
        export_utils = ExportUtils()
        product_data = [product.to_dict()]
        
        if format == 'csv':
            file_path = export_utils.export_to_csv(product_data, f"product_{product_id}")
        elif format == 'json':
            file_path = export_utils.export_to_json(product_data, f"product_{product_id}")
        elif format == 'xml':
            file_path = export_utils.export_to_xml(product_data, f"product_{product_id}")
        else:
            return jsonify({'error': 'Invalid export format'}), 400
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=f'product_{product_id}.{format}'
        )
        
    except Exception as e:
        logging.error(f"Error exporting product {product_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/products')
def api_products():
    """API endpoint for paginated product search"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        category = request.args.get('category', '')
        brand = request.args.get('brand', '')
        job_id = request.args.get('job_id', type=int)
        
        query = Product.query
        
        # Filter by job_id if provided (this is the key fix)
        if job_id:
            query = query.filter(Product.job_id == job_id)
        
        if search:
            query = query.filter(Product.title.contains(search))
        if category:
            query = query.filter(Product.ai_normalized_category == category)
        if brand:
            query = query.filter(Product.ai_normalized_brand == brand)
        
        products = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'products': [product.to_dict() for product in products.items],
            'total': products.total,
            'pages': products.pages,
            'current_page': page,
            'per_page': per_page
        })
        
    except Exception as e:
        logging.error(f"Error in products API: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/job/<int:job_id>/pause', methods=['POST'])
def pause_job(job_id):
    """Pause a running scraping job"""
    try:
        job = ScrapingJob.query.get_or_404(job_id)
        if job.status == 'running':
            job.status = 'paused'
            db.session.commit()
            return jsonify({'message': 'Job paused successfully'})
        else:
            return jsonify({'error': 'Job is not running'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/job/<int:job_id>/resume', methods=['POST'])
def resume_job(job_id):
    """Resume a paused scraping job"""
    try:
        job = ScrapingJob.query.get_or_404(job_id)
        if job.status == 'paused':
            job.status = 'running'
            db.session.commit()
            # Restart the background job
            thread = threading.Thread(target=run_scraping_job, args=(job_id,))
            thread.daemon = True
            thread.start()
            return jsonify({'message': 'Job resumed successfully'})
        else:
            return jsonify({'error': 'Job is not paused'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/job/<int:job_id>/cancel', methods=['POST'])
def cancel_job(job_id):
    """Cancel a scraping job"""
    try:
        job = ScrapingJob.query.get_or_404(job_id)
        if job.status in ['running', 'paused', 'pending']:
            job.status = 'cancelled'
            job.completed_at = datetime.utcnow()
            db.session.commit()
            return jsonify({'message': 'Job cancelled successfully'})
        else:
            return jsonify({'error': 'Job cannot be cancelled'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def run_scraping_job(job_id):
    """Background function to run scraping job with detailed progress tracking"""
    with app.app_context():
        try:
            job = ScrapingJob.query.get(job_id)
            if not job:
                return
            
            # Update job status and initialize progress
            job.status = 'running'
            job.current_step = 'Starting'
            job.step_detail = 'Initializing scraper...'
            db.session.commit()
            
            # Initialize scraper and AI enhancer
            scraper = ProductScraper()
            ai_enhancer = AIEnhancer()
            
            # Update progress: Starting scrape - IMMEDIATE UPDATE
            job.current_step = 'Scraping'
            job.step_detail = f'Analyzing website: {job.url}'
            try:
                db.session.commit()
                logging.info(f"Progress: Started scraping {job.url}")
            except Exception as e:
                logging.error(f"Error updating initial progress: {e}")
                db.session.rollback()
            
            # Scrape products with progress tracking
            logging.info(f"Starting scrape for URL: {job.url}")
            products_data = scraper.scrape_products_with_progress(job.url, job_id)
            
            # Check if job was cancelled during scraping
            job = ScrapingJob.query.get(job_id)
            if job.status in ['cancelled', 'paused']:
                return
            
            if not products_data:
                job.status = 'failed'
                job.error_message = 'No products found on the provided URL'
                job.completed_at = datetime.utcnow()
                job.step_detail = 'No products found'
                db.session.commit()
                return
            
            # Update progress: Starting AI enhancement
            job.total_products_found = len(products_data)
            job.current_step = 'AI Enhancement'
            job.step_detail = f'Found {len(products_data)} products. Starting AI enhancement...'
            db.session.commit()
            
            # Process and enhance each product with progress tracking
            for index, product_data in enumerate(products_data, 1):
                # Check for pause/cancel before each product
                job = ScrapingJob.query.get(job_id)
                if job.status == 'cancelled':
                    return
                elif job.status == 'paused':
                    # Wait for resume
                    while job.status == 'paused':
                        time.sleep(1)
                        job = ScrapingJob.query.get(job_id)
                        if job.status == 'cancelled':
                            return
                
                try:
                    # Update detailed progress - IMMEDIATE UPDATE
                    job.products_processed = index
                    job.step_detail = f'Processing product {index} of {len(products_data)}: {product_data.get("title", "Unknown")[:50]}...'
                    try:
                        db.session.commit()
                        logging.info(f"Processing product {index}/{len(products_data)}: {product_data.get('title', 'Unknown')[:30]}")
                    except Exception as e:
                        logging.error(f"Error updating product progress: {e}")
                        db.session.rollback()
                    
                    # Enhance product data with AI
                    enhanced_data = ai_enhancer.enhance_product(product_data)
                    
                    # Update AI enhancement progress
                    job.products_ai_enhanced = index
                    job.step_detail = f'AI enhancing product {index} of {len(products_data)}: {enhanced_data.get("title", "Unknown")[:50]}...'
                    db.session.commit()
                    
                    # Create product record
                    product = Product(
                        job_id=job.id,
                        title=enhanced_data.get('title'),
                        description=enhanced_data.get('description'),
                        price=enhanced_data.get('price'),
                        original_price=enhanced_data.get('original_price'),
                        currency=enhanced_data.get('currency'),
                        availability=enhanced_data.get('availability'),
                        brand=enhanced_data.get('brand'),
                        category=enhanced_data.get('category'),
                        subcategory=enhanced_data.get('subcategory'),
                        sku=enhanced_data.get('sku'),
                        rating=enhanced_data.get('rating'),
                        review_count=enhanced_data.get('review_count'),
                        main_image_url=enhanced_data.get('main_image_url'),
                        image_urls=enhanced_data.get('image_urls_json'),
                        ai_summary=enhanced_data.get('ai_summary'),
                        ai_tags=enhanced_data.get('ai_tags_json'),
                        ai_normalized_category=enhanced_data.get('ai_normalized_category'),
                        ai_normalized_brand=enhanced_data.get('ai_normalized_brand'),
                        ai_woocommerce_type=enhanced_data.get('ai_woocommerce_type'),
                        source_url=job.url
                    )
                    
                    db.session.add(product)
                    db.session.commit()  # Commit each product to prevent loss
                    
                except Exception as e:
                    logging.error(f"Error processing product {index}: {str(e)}")
                    continue
            
            # Final completion
            job.status = 'completed'
            job.completed_at = datetime.utcnow()
            job.current_step = 'Completed'
            job.step_detail = f'Successfully processed {job.products_ai_enhanced} products'
            db.session.commit()
            
            logging.info(f"Scraping job {job_id} completed successfully with {len(products_data)} products")
            
        except Exception as e:
            logging.error(f"Error in scraping job {job_id}: {str(e)}")
            job = ScrapingJob.query.get(job_id)
            if job:
                job.status = 'failed'
                job.error_message = str(e)
                job.completed_at = datetime.utcnow()
                job.current_step = 'Failed'
                job.step_detail = f'Error: {str(e)}'
                db.session.commit()
