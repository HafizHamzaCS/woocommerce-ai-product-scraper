import requests
from bs4 import BeautifulSoup
import json
import re
import logging
from urllib.parse import urljoin, urlparse
import time

class ProductScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def scrape_products(self, url):
        """Main method to scrape products from a given URL with pagination support"""
        try:
            logging.info(f"Scraping products from: {url}")
            all_products = []
            current_page = 1
            max_pages = 10  # Reasonable limit to prevent infinite loops
            
            while current_page <= max_pages:
                # Build URL for current page
                page_url = self._build_page_url(url, current_page)
                logging.info(f"Scraping page {current_page}: {page_url}")
                
                # Get the page content
                response = self.session.get(page_url, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Try different scraping strategies
                page_products = []
                
                # Strategy 1: Look for JSON-LD structured data
                json_ld_products = self._extract_json_ld_products(soup)
                if json_ld_products:
                    page_products.extend(json_ld_products)
                
                # Strategy 2: Look for common product containers
                if not page_products:
                    container_products = self._extract_container_products(soup, page_url)
                    page_products.extend(container_products)
                
                # Strategy 3: Single product page (only for first page)
                if not page_products and current_page == 1:
                    single_product = self._extract_single_product(soup, page_url)
                    if single_product:
                        page_products.append(single_product)
                
                # If no products found on this page, we've reached the end
                if not page_products:
                    logging.info(f"No products found on page {current_page}, stopping pagination")
                    break
                
                all_products.extend(page_products)
                logging.info(f"Found {len(page_products)} products on page {current_page}")
                
                # Check if there's a next page
                if not self._has_next_page(soup, page_url):
                    logging.info(f"No next page found, stopping at page {current_page}")
                    break
                
                current_page += 1
                time.sleep(1)  # Be respectful to the server
            
            logging.info(f"Total products found across {current_page} pages: {len(all_products)}")
            return all_products
            
        except Exception as e:
            logging.error(f"Error scraping products: {str(e)}")
            raise
    
    def _extract_json_ld_products(self, soup):
        """Extract products from JSON-LD structured data"""
        products = []
        
        try:
            json_scripts = soup.find_all('script', type='application/ld+json')
            
            for script in json_scripts:
                try:
                    data = json.loads(script.string)
                    
                    # Handle different JSON-LD structures
                    if isinstance(data, list):
                        for item in data:
                            product = self._parse_json_ld_product(item)
                            if product:
                                products.append(product)
                    else:
                        product = self._parse_json_ld_product(data)
                        if product:
                            products.append(product)
                            
                except json.JSONDecodeError:
                    continue
        
        except Exception as e:
            logging.warning(f"Error extracting JSON-LD products: {str(e)}")
        
        return products
    
    def _parse_json_ld_product(self, data):
        """Parse a single product from JSON-LD data"""
        try:
            if data.get('@type') == 'Product':
                product = {
                    'title': data.get('name', ''),
                    'description': data.get('description', ''),
                    'brand': data.get('brand', {}).get('name', '') if isinstance(data.get('brand'), dict) else str(data.get('brand', '')),
                    'sku': data.get('sku', ''),
                    'image_urls': []
                }
                
                # Extract price information
                offers = data.get('offers', {})
                if offers:
                    if isinstance(offers, list):
                        offers = offers[0]
                    
                    product['price'] = offers.get('price', '')
                    product['currency'] = offers.get('priceCurrency', '')
                    product['availability'] = offers.get('availability', '')
                
                # Extract images
                if 'image' in data:
                    images = data['image']
                    if isinstance(images, str):
                        product['image_urls'] = [images]
                        product['main_image_url'] = images
                    elif isinstance(images, list):
                        product['image_urls'] = images
                        product['main_image_url'] = images[0] if images else ''
                
                # Extract rating
                rating_data = data.get('aggregateRating', {})
                if rating_data:
                    product['rating'] = rating_data.get('ratingValue')
                    product['review_count'] = rating_data.get('reviewCount')
                
                return product
                
        except Exception as e:
            logging.warning(f"Error parsing JSON-LD product: {str(e)}")
        
        return None
    
    def _extract_container_products(self, soup, base_url):
        """Extract products from common HTML containers"""
        products = []
        
        # Common product container selectors
        product_selectors = [
            '.product-item',
            '.product',
            '.product-card',
            '.woocommerce-product',
            '.shop-item',
            '.product-box',
            '[data-product-id]',
            '.product-tile',
            '.item-product'
        ]
        
        for selector in product_selectors:
            containers = soup.select(selector)
            if containers:
                for container in containers[:20]:  # Limit to first 20 products
                    product = self._extract_product_from_container(container, base_url)
                    if product:
                        products.append(product)
                break  # Use first successful selector
        
        return products
    
    def _extract_product_from_container(self, container, base_url):
        """Extract product data from a single container element"""
        try:
            product = {
                'title': '',
                'description': '',
                'price': '',
                'original_price': '',
                'brand': '',
                'category': '',
                'image_urls': [],
                'main_image_url': '',
                'rating': None,
                'review_count': None
            }
            
            # Extract title
            title_selectors = [
                '.product-title', '.product-name', 'h2', 'h3', 'h4',
                '.title', '.name', '[data-product-title]'
            ]
            for selector in title_selectors:
                title_elem = container.select_one(selector)
                if title_elem:
                    product['title'] = title_elem.get_text(strip=True)
                    break
            
            # Extract price
            price_selectors = [
                '.price', '.product-price', '.cost', '.amount',
                '[data-price]', '.price-current', '.sale-price'
            ]
            for selector in price_selectors:
                price_elem = container.select_one(selector)
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    product['price'] = self._clean_price(price_text)
                    break
            
            # Extract original price (for sales)
            original_price_selectors = [
                '.original-price', '.regular-price', '.was-price',
                '.price-old', '.strike-through'
            ]
            for selector in original_price_selectors:
                orig_price_elem = container.select_one(selector)
                if orig_price_elem:
                    product['original_price'] = self._clean_price(orig_price_elem.get_text(strip=True))
                    break
            
            # Extract main image
            img_elem = container.select_one('img')
            if img_elem:
                img_src = img_elem.get('src') or img_elem.get('data-src')
                if img_src:
                    product['main_image_url'] = urljoin(base_url, img_src)
                    product['image_urls'] = [product['main_image_url']]
            
            # Extract rating
            rating_elem = container.select_one('.rating, .stars, [data-rating]')
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                rating_match = re.search(r'(\d+(?:\.\d+)?)', rating_text)
                if rating_match:
                    product['rating'] = float(rating_match.group(1))
            
            return product if product['title'] else None
            
        except Exception as e:
            logging.warning(f"Error extracting product from container: {str(e)}")
            return None
    
    def _extract_single_product(self, soup, url):
        """Extract single product data from a product detail page"""
        try:
            product = {
                'title': '',
                'description': '',
                'price': '',
                'original_price': '',
                'brand': '',
                'category': '',
                'sku': '',
                'image_urls': [],
                'main_image_url': '',
                'rating': None,
                'review_count': None
            }
            
            # Extract title
            title_selectors = [
                'h1.product-title', 'h1.entry-title', 'h1.product_title',
                'h1', '.product-name h1', '.product-title'
            ]
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    product['title'] = title_elem.get_text(strip=True)
                    break
            
            # Extract description
            desc_selectors = [
                '.product-description', '.product-details', '.entry-content',
                '.product-summary', '.short-description', '#tab-description'
            ]
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    product['description'] = desc_elem.get_text(strip=True)[:1000]  # Limit length
                    break
            
            # Extract price
            price_selectors = [
                '.price .amount', '.product-price', '.price-current',
                '.sale-price', '.woocommerce-Price-amount'
            ]
            for selector in price_selectors:
                price_elem = soup.select_one(selector)
                if price_elem:
                    product['price'] = self._clean_price(price_elem.get_text(strip=True))
                    break
            
            # Extract images
            img_selectors = [
                '.product-images img', '.product-gallery img',
                '.woocommerce-product-gallery img'
            ]
            for selector in img_selectors:
                img_elements = soup.select(selector)
                if img_elements:
                    for img in img_elements[:5]:  # Limit to 5 images
                        img_src = img.get('src') or img.get('data-src')
                        if img_src:
                            full_url = urljoin(url, img_src)
                            product['image_urls'].append(full_url)
                    
                    if product['image_urls']:
                        product['main_image_url'] = product['image_urls'][0]
                    break
            
            # Extract SKU
            sku_elem = soup.select_one('.sku, [data-sku]')
            if sku_elem:
                product['sku'] = sku_elem.get_text(strip=True)
            
            return product if product['title'] else None
            
        except Exception as e:
            logging.warning(f"Error extracting single product: {str(e)}")
            return None
    
    def _clean_price(self, price_text):
        """Clean and normalize price text"""
        if not price_text:
            return ''
        
        # Remove common currency symbols and extract numeric value
        price_text = re.sub(r'[^\d.,]', '', price_text)
        return price_text.strip()
    
    def _build_page_url(self, base_url, page_number):
        """Build URL for a specific page number"""
        if page_number == 1:
            return base_url
        
        # Try common pagination patterns
        patterns = [
            f"{base_url}/page/{page_number}",
            f"{base_url}?page={page_number}",
            f"{base_url}&page={page_number}",
            f"{base_url}/page/{page_number}/",
            f"{base_url}?paged={page_number}",
            f"{base_url}&paged={page_number}"
        ]
        
        # Check if URL already has query parameters
        if '?' in base_url:
            return f"{base_url}&page={page_number}"
        else:
            # Try WordPress/WooCommerce style first (most common)
            if base_url.endswith('/'):
                return f"{base_url}page/{page_number}/"
            else:
                return f"{base_url}/page/{page_number}/"
    
    def _has_next_page(self, soup, current_url):
        """Check if there's a next page available"""
        # Look for common next page indicators
        next_indicators = [
            'a[rel="next"]',
            'a.next',
            'a.next-page',
            '.pagination a.next',
            '.wp-pagenavi a.nextpostslink',
            '.woocommerce-pagination a.next',
            '.page-numbers.next',
            'a[aria-label*="Next"]',
            'a[title*="Next"]'
        ]
        
        for indicator in next_indicators:
            if soup.select_one(indicator):
                return True
        
        # Look for pagination with higher page numbers
        page_links = soup.select('.pagination a, .page-numbers a, .wp-pagenavi a')
        current_page_num = self._extract_page_number_from_url(current_url)
        
        for link in page_links:
            href = link.get('href', '')
            if href:
                page_num = self._extract_page_number_from_url(href)
                if page_num and page_num > current_page_num:
                    return True
        
        return False
    
    def _extract_page_number_from_url(self, url):
        """Extract page number from URL"""
        # Try to find page number in URL
        patterns = [
            r'/page/(\d+)',
            r'[?&]page=(\d+)',
            r'[?&]paged=(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return int(match.group(1))
        
        return 1  # Default to page 1
    
    def scrape_products_with_progress(self, url, job_id):
        """Enhanced scrape method with progress tracking for job monitoring"""
        from app import db
        from models import ScrapingJob
        
        try:
            logging.info(f"Scraping products from: {url}")
            all_products = []
            current_page = 1
            max_pages = 10  # Reasonable limit to prevent infinite loops
            
            while current_page <= max_pages:
                # Check if job was cancelled/paused before each page
                job = ScrapingJob.query.get(job_id)
                if job and job.status in ['cancelled', 'paused']:
                    return all_products
                
                # Update progress for current page - IMMEDIATE UPDATE
                if job:
                    job.current_page = current_page
                    job.step_detail = f'Scraping page {current_page} of website...'
                    try:
                        db.session.commit()
                        logging.info(f"Started scraping page {current_page}")
                    except Exception as e:
                        logging.error(f"Error updating page progress: {e}")
                        db.session.rollback()
                
                # Build URL for current page
                page_url = self._build_page_url(url, current_page)
                logging.info(f"Scraping page {current_page}: {page_url}")
                
                # Get the page content
                response = self.session.get(page_url, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Try different scraping strategies
                page_products = []
                
                # Strategy 1: Look for JSON-LD structured data
                json_ld_products = self._extract_json_ld_products(soup)
                if json_ld_products:
                    page_products.extend(json_ld_products)
                
                # Strategy 2: Look for common product containers
                if not page_products:
                    container_products = self._extract_container_products(soup, page_url)
                    page_products.extend(container_products)
                
                # Strategy 3: Single product page (only for first page)
                if not page_products and current_page == 1:
                    single_product = self._extract_single_product(soup, page_url)
                    if single_product:
                        page_products.append(single_product)
                
                # If no products found on this page, we've reached the end
                if not page_products:
                    logging.info(f"No products found on page {current_page}, stopping pagination")
                    break
                
                all_products.extend(page_products)
                logging.info(f"Found {len(page_products)} products on page {current_page}")
                
                # Update progress with total found so far - IMMEDIATE UPDATE
                if job:
                    job.total_products_found = len(all_products)
                    job.step_detail = f'Found {len(all_products)} products so far (page {current_page})'
                    try:
                        db.session.commit()
                        logging.info(f"Progress updated: {len(all_products)} products found on page {current_page}")
                    except Exception as e:
                        logging.error(f"Error updating progress: {e}")
                        db.session.rollback()
                
                # Check if there's a next page
                if not self._has_next_page(soup, page_url):
                    logging.info(f"No next page found, stopping at page {current_page}")
                    if job:
                        job.total_pages = current_page
                        db.session.commit()
                    break
                
                current_page += 1
                time.sleep(1)  # Be respectful to the server
            
            # Final update
            if job:
                job.total_pages = current_page
                job.total_products_found = len(all_products)
                job.step_detail = f'Scraping complete: {len(all_products)} products found across {current_page} pages'
                db.session.commit()
            
            logging.info(f"Total products found across {current_page} pages: {len(all_products)}")
            return all_products
            
        except Exception as e:
            logging.error(f"Error scraping products: {str(e)}")
            raise
