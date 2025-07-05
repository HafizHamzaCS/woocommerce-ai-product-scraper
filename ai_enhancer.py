import os
import json
import logging
from openai import OpenAI

class AIEnhancer:
    def __init__(self):
        self.openai_client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY")
        )
    
    def enhance_product(self, product_data):
        """Enhance product data using AI"""
        try:
            enhanced_data = product_data.copy()
            
            # Generate AI summary
            if product_data.get('description'):
                enhanced_data['ai_summary'] = self._generate_summary(product_data['description'])
            
            # Normalize brand and category
            enhanced_data['ai_normalized_brand'] = self._normalize_brand(product_data.get('brand', ''))
            enhanced_data['ai_normalized_category'] = self._normalize_category(product_data.get('category', ''), product_data.get('title', ''))
            
            # Generate SEO tags
            enhanced_data['ai_tags'] = self._generate_seo_tags(product_data)
            enhanced_data['ai_tags_json'] = json.dumps(enhanced_data['ai_tags'])
            
            # Determine WooCommerce product type
            enhanced_data['ai_woocommerce_type'] = self._determine_woocommerce_type(product_data)
            
            # Format image URLs as JSON
            if product_data.get('image_urls'):
                enhanced_data['image_urls_json'] = json.dumps(product_data['image_urls'])
            else:
                enhanced_data['image_urls_json'] = json.dumps([])
            
            return enhanced_data
            
        except Exception as e:
            logging.error(f"Error enhancing product data: {str(e)}")
            # Return original data if AI enhancement fails
            product_data['ai_summary'] = ''
            product_data['ai_tags'] = []
            product_data['ai_tags_json'] = '[]'
            product_data['ai_normalized_brand'] = product_data.get('brand', '')
            product_data['ai_normalized_category'] = product_data.get('category', '')
            product_data['ai_woocommerce_type'] = 'simple'
            product_data['image_urls_json'] = json.dumps(product_data.get('image_urls', []))
            return product_data
    
    def _generate_summary(self, description):
        """Generate a concise product summary"""
        try:
            if not description or len(description.strip()) < 50:
                return description
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a product copywriter. Generate a concise, compelling 2-3 sentence summary of the product description that highlights key features and benefits. Keep it under 200 characters."
                    },
                    {
                        "role": "user",
                        "content": f"Summarize this product description: {description[:1000]}"
                    }
                ],
                max_tokens=100,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logging.error(f"Error generating AI summary: {str(e)}")
            return description[:200] + "..." if len(description) > 200 else description
    
    def _normalize_brand(self, brand):
        """Normalize brand name using AI"""
        try:
            if not brand or len(brand.strip()) < 2:
                return brand
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a brand normalization expert. Normalize brand names to their standard format. Return only the normalized brand name, nothing else. If the input is not a real brand, return it as-is."
                    },
                    {
                        "role": "user",
                        "content": f"Normalize this brand name: {brand}"
                    }
                ],
                max_tokens=50,
                temperature=0.1
            )
            
            normalized = response.choices[0].message.content.strip()
            return normalized if normalized else brand
            
        except Exception as e:
            logging.error(f"Error normalizing brand: {str(e)}")
            return brand
    
    def _normalize_category(self, category, title):
        """Normalize product category using AI"""
        try:
            context = f"Category: {category}, Title: {title}" if category else f"Title: {title}"
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a product categorization expert. Based on the product information, return a single, standardized category name that would work well in an e-commerce store. Use common category names like 'Electronics', 'Clothing', 'Home & Garden', 'Sports', etc. Return only the category name."
                    },
                    {
                        "role": "user",
                        "content": context
                    }
                ],
                max_tokens=30,
                temperature=0.1
            )
            
            normalized = response.choices[0].message.content.strip()
            return normalized if normalized else category
            
        except Exception as e:
            logging.error(f"Error normalizing category: {str(e)}")
            return category
    
    def _generate_seo_tags(self, product_data):
        """Generate SEO-friendly tags for the product"""
        try:
            product_info = {
                'title': product_data.get('title', ''),
                'description': product_data.get('description', '')[:500],  # Limit description length
                'brand': product_data.get('brand', ''),
                'category': product_data.get('category', '')
            }
            
            context = f"Product: {product_info['title']}\nBrand: {product_info['brand']}\nCategory: {product_info['category']}\nDescription: {product_info['description']}"
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an SEO expert. Generate 5-8 relevant, SEO-friendly tags for this product. Tags should be specific, searchable keywords that customers might use. Return the response as a JSON array of strings."
                    },
                    {
                        "role": "user",
                        "content": context
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=150,
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            tags = result.get('tags', [])
            
            # Ensure we have a list of strings
            if isinstance(tags, list) and all(isinstance(tag, str) for tag in tags):
                return tags[:8]  # Limit to 8 tags
            else:
                return []
                
        except Exception as e:
            logging.error(f"Error generating SEO tags: {str(e)}")
            return []
    
    def _determine_woocommerce_type(self, product_data):
        """Determine appropriate WooCommerce product type"""
        try:
            title = product_data.get('title', '').lower()
            description = product_data.get('description', '').lower()
            
            # Simple heuristics for product type determination
            variable_keywords = ['size', 'color', 'variant', 'option', 'select']
            grouped_keywords = ['bundle', 'set', 'pack', 'collection', 'kit']
            
            text_to_check = f"{title} {description}"
            
            if any(keyword in text_to_check for keyword in grouped_keywords):
                return 'grouped'
            elif any(keyword in text_to_check for keyword in variable_keywords):
                return 'variable'
            else:
                return 'simple'
                
        except Exception as e:
            logging.error(f"Error determining WooCommerce type: {str(e)}")
            return 'simple'
