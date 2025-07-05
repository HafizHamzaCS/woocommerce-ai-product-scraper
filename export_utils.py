import pandas as pd
import json
import xml.etree.ElementTree as ET
import os
from datetime import datetime
import logging

class ExportUtils:
    def __init__(self):
        self.export_dir = 'exports'
        os.makedirs(self.export_dir, exist_ok=True)
    
    def export_to_csv(self, products_data, job_identifier):
        """Export products to CSV format"""
        try:
            if not products_data:
                raise ValueError("No products data to export")
            
            # Flatten the data for CSV export
            flattened_data = []
            for product in products_data:
                flattened = self._flatten_product_data(product)
                flattened_data.append(flattened)
            
            df = pd.DataFrame(flattened_data)
            
            # Reorder columns for better readability
            desired_columns = [
                'id', 'title', 'ai_summary', 'description', 'price', 'original_price',
                'currency', 'availability', 'brand', 'ai_normalized_brand',
                'category', 'ai_normalized_category', 'sku', 'rating', 'review_count',
                'main_image_url', 'ai_woocommerce_type', 'source_url', 'scraped_at'
            ]
            
            # Add available columns in desired order
            available_columns = [col for col in desired_columns if col in df.columns]
            remaining_columns = [col for col in df.columns if col not in available_columns]
            final_columns = available_columns + remaining_columns
            
            df = df[final_columns]
            
            filename = f'products_{job_identifier}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            file_path = os.path.join(self.export_dir, filename)
            
            df.to_csv(file_path, index=False, encoding='utf-8')
            
            logging.info(f"CSV export completed: {file_path}")
            return file_path
            
        except Exception as e:
            logging.error(f"Error exporting to CSV: {str(e)}")
            raise
    
    def export_to_json(self, products_data, job_identifier):
        """Export products to JSON format"""
        try:
            if not products_data:
                raise ValueError("No products data to export")
            
            # Create WooCommerce-compatible JSON structure
            woocommerce_data = {
                'metadata': {
                    'export_date': datetime.now().isoformat(),
                    'total_products': len(products_data),
                    'format_version': '1.0'
                },
                'products': []
            }
            
            for product in products_data:
                woo_product = self._convert_to_woocommerce_format(product)
                woocommerce_data['products'].append(woo_product)
            
            filename = f'products_{job_identifier}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            file_path = os.path.join(self.export_dir, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(woocommerce_data, f, indent=2, ensure_ascii=False)
            
            logging.info(f"JSON export completed: {file_path}")
            return file_path
            
        except Exception as e:
            logging.error(f"Error exporting to JSON: {str(e)}")
            raise
    
    def export_to_xml(self, products_data, job_identifier):
        """Export products to XML format"""
        try:
            if not products_data:
                raise ValueError("No products data to export")
            
            # Create root XML element
            root = ET.Element('woocommerce_products')
            
            # Add metadata
            metadata = ET.SubElement(root, 'metadata')
            ET.SubElement(metadata, 'export_date').text = datetime.now().isoformat()
            ET.SubElement(metadata, 'total_products').text = str(len(products_data))
            ET.SubElement(metadata, 'format_version').text = '1.0'
            
            # Add products
            products_elem = ET.SubElement(root, 'products')
            
            for product in products_data:
                product_elem = ET.SubElement(products_elem, 'product')
                
                # Add product attributes
                for key, value in product.items():
                    if value is not None:
                        elem = ET.SubElement(product_elem, key)
                        if isinstance(value, (list, dict)):
                            elem.text = json.dumps(value)
                        else:
                            elem.text = str(value)
            
            # Create XML tree and save
            tree = ET.ElementTree(root)
            
            filename = f'products_{job_identifier}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xml'
            file_path = os.path.join(self.export_dir, filename)
            
            tree.write(file_path, encoding='utf-8', xml_declaration=True)
            
            logging.info(f"XML export completed: {file_path}")
            return file_path
            
        except Exception as e:
            logging.error(f"Error exporting to XML: {str(e)}")
            raise
    
    def _flatten_product_data(self, product):
        """Flatten product data for CSV export"""
        flattened = {}
        
        for key, value in product.items():
            if isinstance(value, list):
                # Convert lists to comma-separated strings
                flattened[key] = ', '.join(str(item) for item in value)
            elif isinstance(value, dict):
                # Convert dicts to JSON strings
                flattened[key] = json.dumps(value)
            else:
                flattened[key] = value
        
        return flattened
    
    def _convert_to_woocommerce_format(self, product):
        """Convert product data to WooCommerce-compatible format"""
        woo_product = {
            'name': product.get('title', ''),
            'type': product.get('ai_woocommerce_type', 'simple'),
            'description': product.get('description', ''),
            'short_description': product.get('ai_summary', ''),
            'sku': product.get('sku', ''),
            'regular_price': product.get('price', ''),
            'sale_price': product.get('original_price', ''),
            'status': 'publish',
            'catalog_visibility': 'visible',
            'featured': False,
            'categories': [
                {
                    'name': product.get('ai_normalized_category', '')
                }
            ] if product.get('ai_normalized_category') else [],
            'tags': [
                {'name': tag} for tag in product.get('ai_tags', [])
            ],
            'images': [
                {
                    'src': img_url,
                    'position': idx
                }
                for idx, img_url in enumerate(product.get('image_urls', []))
            ],
            'attributes': [
                {
                    'name': 'Brand',
                    'options': [product.get('ai_normalized_brand', '')],
                    'visible': True,
                    'variation': False
                }
            ] if product.get('ai_normalized_brand') else [],
            'meta_data': [
                {
                    'key': 'source_url',
                    'value': product.get('source_url', '')
                },
                {
                    'key': 'scraped_at',
                    'value': product.get('scraped_at', '')
                },
                {
                    'key': 'ai_enhanced',
                    'value': 'true'
                }
            ]
        }
        
        # Add rating if available
        if product.get('rating'):
            woo_product['average_rating'] = str(product['rating'])
        
        if product.get('review_count'):
            woo_product['rating_count'] = product['review_count']
        
        return woo_product
