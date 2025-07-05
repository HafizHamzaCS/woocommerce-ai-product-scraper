# AI Product Scraper for WooCommerce

## Overview

This is a Flask-based web application that scrapes product data from e-commerce websites and enhances it using AI. The system extracts product information like titles, descriptions, prices, and images, then uses OpenAI's API to generate summaries, normalize categories/brands, and create SEO tags optimized for WooCommerce integration.

## System Architecture

### Backend Architecture
- **Framework**: Flask web framework with SQLAlchemy ORM
- **Database**: PostgreSQL for production-ready data storage
- **AI Integration**: OpenAI API for product data enhancement
- **Background Processing**: Python threading for asynchronous scraping jobs
- **Web Scraping**: BeautifulSoup and requests for HTML parsing and data extraction

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Flask
- **CSS Framework**: Bootstrap 5 for responsive design
- **JavaScript**: Vanilla JS with axios for AJAX requests
- **Real-time Updates**: Polling-based status updates for scraping jobs

## Key Components

### Core Modules

1. **App Module (`app.py`)**
   - Flask application factory pattern
   - SQLAlchemy database configuration
   - ProxyFix middleware for deployment readiness

2. **Models (`models.py`)**
   - `ScrapingJob`: Tracks scraping sessions with status management
   - `Product`: Stores extracted and AI-enhanced product data
   - Foreign key relationship between jobs and products

3. **Scraper (`scraper.py`)**
   - Multi-strategy product extraction (JSON-LD, container-based, single product)
   - Robust error handling and fallback mechanisms
   - Configurable user-agent and session management

4. **AI Enhancer (`ai_enhancer.py`)**
   - OpenAI integration for product data enhancement
   - Generates AI summaries, normalized categories/brands
   - Creates SEO tags and determines WooCommerce product types
   - Graceful fallback when AI services are unavailable

5. **Export Utilities (`export_utils.py`)**
   - Multi-format export support (CSV, planned XML/JSON)
   - Data flattening for tabular exports
   - Timestamped file generation

6. **Routes (`routes.py`)**
   - RESTful API endpoints for scraping operations
   - Real-time job status monitoring
   - File download and export functionality

### Database Schema

**ScrapingJob Table**:
- Tracks scraping sessions with status (pending, running, completed, failed)
- Stores source URL and timestamps
- One-to-many relationship with Product table

**Product Table**:
- Comprehensive product data storage
- AI-enhanced fields for WooCommerce integration
- JSON fields for structured data (tags, image arrays)

## Data Flow

1. **Job Initiation**: User submits URL → Creates ScrapingJob record → Starts background thread
2. **Data Extraction**: Scraper analyzes HTML → Extracts product information using multiple strategies
3. **AI Enhancement**: Raw data → OpenAI API → Enhanced with summaries, normalized data, SEO tags
4. **Storage**: Enhanced data → Database with job association
5. **Export**: Processed data → Multiple export formats for WooCommerce import

## External Dependencies

### Core Dependencies
- **Flask Ecosystem**: Flask, SQLAlchemy, Jinja2 for web framework
- **Web Scraping**: BeautifulSoup4, requests for HTML parsing
- **AI Services**: OpenAI API for product enhancement
- **Data Processing**: Pandas for export functionality

### Frontend Dependencies
- **Bootstrap 5**: UI framework and responsive design
- **Font Awesome**: Icon library
- **Axios**: HTTP client for API requests

## Deployment Strategy

### Development Setup
- PostgreSQL database for development and production
- Flask development server with debug mode
- Environment variables for API keys and configuration

### Production Considerations
- **Database**: PostgreSQL configured for production use
- **WSGI**: ProxyFix middleware configured for reverse proxy deployment
- **Scaling**: Background job processing ready for Celery integration
- **Security**: Session management and environment-based secrets

### Environment Variables
- `OPENAI_API_KEY`: Required for AI enhancement features
- `SESSION_SECRET`: Flask session security (defaults provided for development)

## Changelog
- July 05, 2025. Enhanced Progress Tracking and Control System
  - Implemented detailed real-time progress tracking with step-by-step status updates
  - Added comprehensive progress statistics (products found, processed, AI enhanced, pages scraped)
  - Created intuitive control buttons (Pause, Resume, Cancel) for job management
  - Enhanced pagination support with intelligent multi-page detection
  - Background processing persists when navigating between pages
  - Real-time updates every second with detailed current activity display
  - Added database fields for tracking: total_products_found, products_processed, products_ai_enhanced, current_page, total_pages, current_step, step_detail
  - Created enhanced progress modal with statistics dashboard and control interface

- July 04, 2025. Initial setup and successful testing
  - Successfully tested scraper with WooCommerce Storefront demo store
  - Scraped 16 products including camera equipment and electronics
  - Confirmed AI enhancement working (summaries, category normalization, SEO tags)
  - Verified multi-format export functionality (CSV, JSON, XML)
  - OpenAI API integration functioning properly
  - Upgraded database from SQLite to PostgreSQL for production readiness
  - Verified PostgreSQL integration with successful data persistence

## User Preferences

Preferred communication style: Simple, everyday language.