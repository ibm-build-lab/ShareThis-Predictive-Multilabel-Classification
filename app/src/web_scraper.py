#!/usr/bin/env python3
"""
Web Scraper Module for FastAPI Application
==========================================

A comprehensive web scraping tool that fetches, cleans, and extracts metadata from web pages.

Features:
- Fetches HTML content with proper headers and error handling
- Extracts and cleans main text content
- Extracts comprehensive metadata (title, description, author, dates, Open Graph tags, etc.)
- Handles different encodings and content types
- Returns structured output with cleaned text and metadata

Author: Bob
Date: 2026-04-24
"""

import re
import json
import logging
from typing import Dict, Optional, List, Any
from urllib.parse import urlparse, urljoin
from datetime import datetime

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError as e:
    print(f"Error: Missing required library. Please install: pip install requests beautifulsoup4 lxml")
    raise e

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WebScraper:
    """
    A comprehensive web scraper for extracting and cleaning content from web pages.
    
    Attributes:
        timeout (int): Request timeout in seconds
        max_retries (int): Maximum number of retry attempts
        headers (dict): HTTP headers for requests
    """
    
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        """
        Initialize the WebScraper.
        
        Args:
            timeout (int): Request timeout in seconds (default: 30)
            max_retries (int): Maximum retry attempts (default: 3)
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    def validate_url(self, url: str) -> bool:
        """
        Validate if the URL is properly formatted.
        
        Args:
            url (str): URL to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception as e:
            logger.error(f"URL validation error: {e}")
            return False
    
    def fetch_html(self, url: str) -> Optional[requests.Response]:
        """
        Fetch HTML content from URL with retry logic.
        
        Args:
            url (str): URL to fetch
            
        Returns:
            Optional[requests.Response]: Response object or None if failed
        """
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Fetching URL (attempt {attempt + 1}/{self.max_retries}): {url}")
                response = requests.get(
                    url,
                    headers=self.headers,
                    timeout=self.timeout,
                    allow_redirects=True
                )
                response.raise_for_status()
                return response
            
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    logger.error(f"Failed to fetch URL after {self.max_retries} attempts: Timeout")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    logger.error(f"Failed to fetch URL after {self.max_retries} attempts")
        
        return None
    
    def extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """
        Extract comprehensive metadata from HTML.
        
        Args:
            soup (BeautifulSoup): Parsed HTML
            url (str): Original URL
            
        Returns:
            Dict[str, Any]: Dictionary containing all extracted metadata
        """
        metadata = {
            'url': url,
            'domain': urlparse(url).netloc,
            'scraped_at': datetime.utcnow().isoformat(),
        }
        
        # Extract title
        title_tag = soup.find('title')
        metadata['title'] = title_tag.get_text().strip() if title_tag else None
        
        # Extract meta tags
        meta_tags = soup.find_all('meta')
        
        for tag in meta_tags:
            # Standard meta tags
            if tag.get('name'):
                name = tag.get('name').lower()
                content = tag.get('content', '').strip()
                
                if name in ['description', 'keywords', 'author', 'robots', 'language']:
                    metadata[name] = content
                elif name == 'article:published_time' or name == 'publish_date':
                    metadata['published_date'] = content
                elif name == 'article:modified_time' or name == 'modified_date':
                    metadata['modified_date'] = content
            
            # Open Graph tags
            if tag.get('property'):
                prop = tag.get('property').lower()
                content = tag.get('content', '').strip()
                
                if prop.startswith('og:'):
                    key = prop.replace('og:', 'og_')
                    metadata[key] = content
                elif prop.startswith('article:'):
                    key = prop.replace('article:', 'article_')
                    metadata[key] = content
            
            # Charset
            if tag.get('charset'):
                metadata['charset'] = tag.get('charset')
        
        # Extract canonical URL
        canonical = soup.find('link', {'rel': 'canonical'})
        if canonical and canonical.get('href'):
            metadata['canonical_url'] = canonical.get('href')
        
        # Extract language from html tag
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            metadata['html_lang'] = html_tag.get('lang')
        
        return metadata
    
    def remove_unwanted_elements(self, soup: BeautifulSoup) -> BeautifulSoup:
        """
        Remove unwanted HTML elements (scripts, styles, nav, footer, etc.).
        
        Args:
            soup (BeautifulSoup): Parsed HTML
            
        Returns:
            BeautifulSoup: Cleaned HTML
        """
        # Elements to remove
        unwanted_tags = [
            'script', 'style', 'noscript', 'iframe', 'embed',
            'nav', 'header', 'footer', 'aside', 'form',
            'button', 'input', 'select', 'textarea'
        ]
        
        for tag in unwanted_tags:
            for element in soup.find_all(tag):
                element.decompose()
        
        # Remove elements with common ad/navigation classes
        unwanted_classes = [
            'advertisement', 'ad-', 'ads-', 'sidebar', 'menu',
            'navigation', 'nav-', 'footer', 'header', 'cookie',
            'popup', 'modal', 'social-share', 'related-posts'
        ]
        
        for element in soup.find_all(class_=True):
            classes = ' '.join(element.get('class', [])).lower()
            if any(unwanted in classes for unwanted in unwanted_classes):
                element.decompose()
        
        return soup
    
    def extract_main_content(self, soup: BeautifulSoup) -> str:
        """
        Extract main content from HTML, prioritizing article/main tags.
        
        Args:
            soup (BeautifulSoup): Parsed HTML
            
        Returns:
            str: Extracted text content
        """
        # Try to find main content containers
        main_content = None
        
        # Priority order for content extraction
        content_selectors = [
            ('article', {}),
            ('main', {}),
            ('div', {'role': 'main'}),
            ('div', {'class': re.compile(r'(content|article|post|entry)', re.I)}),
            ('body', {})
        ]
        
        for tag, attrs in content_selectors:
            main_content = soup.find(tag, attrs)
            if main_content:
                logger.info(f"Found main content in <{tag}> tag")
                break
        
        if not main_content:
            main_content = soup
        
        # Extract text
        text = main_content.get_text(separator=' ', strip=True)
        return text
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text.
        
        Args:
            text (str): Raw text to clean
            
        Returns:
            str: Cleaned text
        """
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove multiple newlines
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Remove special characters (keep basic punctuation)
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\[\]\{\}\"\'\/\@\#\$\%\&\*\+\=\<\>\~\`\|\\]', '', text)
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        
        # Remove extra spaces around punctuation
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)
        
        # Trim
        text = text.strip()
        
        return text
    
    def scrape(self, url: str) -> Dict[str, Any]:
        """
        Main scraping method that orchestrates the entire process.
        
        Args:
            url (str): URL to scrape
            
        Returns:
            Dict[str, Any]: Dictionary containing:
                - url: Original URL
                - status: 'success' or 'error'
                - cleaned_text: Cleaned main content
                - metadata: Extracted metadata
                - error: Error message (if status is 'error')
        """
        result = {
            'url': url,
            'status': 'error',
            'cleaned_text': None,
            'metadata': {},
            'error': None
        }
        
        # Validate URL
        if not self.validate_url(url):
            result['error'] = "Invalid URL format"
            logger.error(f"Invalid URL: {url}")
            return result
        
        # Fetch HTML
        response = self.fetch_html(url)
        if not response:
            result['error'] = "Failed to fetch URL"
            return result
        
        try:
            # Parse HTML
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Extract metadata
            metadata = self.extract_metadata(soup, url)
            result['metadata'] = metadata
            
            # Extract main content (before removing unwanted elements for raw text)
            raw_text = self.extract_main_content(soup)
            result['raw_text'] = raw_text
            
            # Remove unwanted elements
            soup = self.remove_unwanted_elements(soup)
            
            # Extract main content again after cleaning
            main_text = self.extract_main_content(soup)
            
            # Clean text
            cleaned_text = self.clean_text(main_text)
            result['cleaned_text'] = cleaned_text
            
            # Add text statistics to metadata
            result['metadata']['text_length'] = len(cleaned_text)
            result['metadata']['word_count'] = len(cleaned_text.split())
            
            result['status'] = 'success'
            logger.info(f"Successfully scraped: {url}")
            
        except Exception as e:
            result['error'] = f"Parsing error: {str(e)}"
            logger.error(f"Error parsing HTML: {e}")
        
        return result

# Made with Bob
