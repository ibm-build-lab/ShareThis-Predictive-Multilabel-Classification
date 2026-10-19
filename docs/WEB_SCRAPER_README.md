# Web Scraper Documentation

## Overview

A comprehensive Python web scraping tool that fetches, cleans, and extracts metadata from web pages. The scraper handles static HTML content and provides structured output with cleaned text and comprehensive metadata.

## Features

✅ **URL Fetching**
- HTTP requests with proper headers and User-Agent
- Automatic retry logic (configurable)
- Timeout handling
- Support for redirects

✅ **Text Extraction & Cleaning**
- Removes HTML tags, scripts, styles, and navigation elements
- Cleans extra whitespace and special characters
- Extracts main content (prioritizes article/main tags)
- Removes ads, sidebars, and unwanted elements

✅ **Metadata Extraction**
- Basic: title, description, keywords, author
- Open Graph tags (og:title, og:description, og:image, etc.)
- Twitter Card tags
- Publication and modification dates
- Canonical URLs
- Language detection
- Structured data (JSON-LD)
- Character encoding

✅ **Output Format**
- Structured dictionary with cleaned text and metadata
- Success/error status
- Word count and text statistics
- JSON-serializable output

## Installation

### 1. Install Dependencies

```bash
cd Notebook
pip install -r scraper_requirements.txt
```

Or install manually:

```bash
pip install requests beautifulsoup4 lxml
```

### 2. Verify Installation

```bash
python -c "import requests, bs4; print('✓ All dependencies installed')"
```

## Usage

### Basic Usage

```python
from web_scraper import WebScraper

# Initialize scraper
scraper = WebScraper()

# Scrape a single URL
result = scraper.scrape("https://example.com/article")

# Check status
if result['status'] == 'success':
    print(f"Title: {result['metadata']['title']}")
    print(f"Text: {result['cleaned_text'][:200]}...")
else:
    print(f"Error: {result['error']}")
```

### Advanced Usage

```python
from web_scraper import WebScraper

# Initialize with custom settings
scraper = WebScraper(
    timeout=60,        # 60 seconds timeout
    max_retries=5      # 5 retry attempts
)

# Scrape single URL
result = scraper.scrape("https://example.com")

# Access metadata
metadata = result['metadata']
print(f"Title: {metadata.get('title')}")
print(f"Description: {metadata.get('description')}")
print(f"Author: {metadata.get('author')}")
print(f"Published: {metadata.get('published_date')}")
print(f"Word Count: {metadata.get('word_count')}")

# Access cleaned text
text = result['cleaned_text']
print(f"Content length: {len(text)} characters")
```

### Scraping Multiple URLs

```python
from web_scraper import WebScraper

scraper = WebScraper()

urls = [
    "https://example.com/article1",
    "https://example.com/article2",
    "https://example.com/article3"
]

# Scrape all URLs
results = scraper.scrape_multiple(urls)

# Process results
for result in results:
    if result['status'] == 'success':
        print(f"✓ {result['url']}")
        print(f"  Title: {result['metadata']['title']}")
        print(f"  Words: {result['metadata']['word_count']}")
    else:
        print(f"✗ {result['url']}: {result['error']}")
```

### Saving Results to JSON

```python
import json
from web_scraper import WebScraper

scraper = WebScraper()
result = scraper.scrape("https://example.com")

# Save to JSON file
with open('scraping_result.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print("✓ Results saved to scraping_result.json")
```

### Batch Processing with CSV

```python
import pandas as pd
from web_scraper import WebScraper

# Read URLs from CSV
df = pd.read_csv('urls.csv')  # CSV with 'url' column

scraper = WebScraper()
results = []

for url in df['url']:
    result = scraper.scrape(url)
    results.append({
        'url': url,
        'title': result['metadata'].get('title'),
        'text': result['cleaned_text'],
        'word_count': result['metadata'].get('word_count'),
        'status': result['status']
    })

# Save results to CSV
output_df = pd.DataFrame(results)
output_df.to_csv('scraping_results.csv', index=False)
print(f"✓ Scraped {len(results)} URLs")
```

## Running the Example Script

The script includes a built-in example that demonstrates all features:

```bash
cd Notebook
python web_scraper.py
```

This will:
1. Scrape example URLs (Wikipedia, Python.org, etc.)
2. Display extracted metadata and cleaned text
3. Save results to `scraping_result.json`

## Output Structure

### Success Response

```json
{
  "url": "https://example.com/article",
  "status": "success",
  "cleaned_text": "This is the cleaned main content...",
  "metadata": {
    "url": "https://example.com/article",
    "domain": "example.com",
    "scraped_at": "2026-04-24T05:10:00.000Z",
    "title": "Article Title",
    "description": "Article description",
    "keywords": "keyword1, keyword2",
    "author": "John Doe",
    "published_date": "2026-04-20",
    "og_title": "Open Graph Title",
    "og_description": "Open Graph Description",
    "og_image": "https://example.com/image.jpg",
    "canonical_url": "https://example.com/article",
    "html_lang": "en",
    "charset": "utf-8",
    "text_length": 5432,
    "word_count": 876
  },
  "error": null
}
```

### Error Response

```json
{
  "url": "https://invalid-url.com",
  "status": "error",
  "cleaned_text": null,
  "metadata": {},
  "error": "Failed to fetch URL"
}
```

## Metadata Fields

| Field | Description | Example |
|-------|-------------|---------|
| `url` | Original URL | `https://example.com` |
| `domain` | Domain name | `example.com` |
| `scraped_at` | Timestamp (UTC) | `2026-04-24T05:10:00.000Z` |
| `title` | Page title | `"Article Title"` |
| `description` | Meta description | `"Article description"` |
| `keywords` | Meta keywords | `"keyword1, keyword2"` |
| `author` | Author name | `"John Doe"` |
| `published_date` | Publication date | `"2026-04-20"` |
| `modified_date` | Last modified date | `"2026-04-22"` |
| `og_*` | Open Graph tags | `og_title`, `og_image`, etc. |
| `twitter_*` | Twitter Card tags | `twitter_title`, etc. |
| `canonical_url` | Canonical URL | `https://example.com/article` |
| `html_lang` | HTML language | `"en"` |
| `charset` | Character encoding | `"utf-8"` |
| `text_length` | Character count | `5432` |
| `word_count` | Word count | `876` |
| `structured_data` | JSON-LD data | `[{...}]` |

## Configuration Options

### WebScraper Parameters

```python
scraper = WebScraper(
    timeout=30,        # Request timeout in seconds (default: 30)
    max_retries=3      # Maximum retry attempts (default: 3)
)
```

### Custom Headers

The scraper uses realistic browser headers by default. You can modify them:

```python
scraper = WebScraper()
scraper.headers['User-Agent'] = 'Your Custom User Agent'
```

## Error Handling

The scraper handles various error scenarios:

- **Invalid URL**: Returns error status with "Invalid URL format"
- **Network errors**: Retries up to `max_retries` times
- **Timeout**: Returns error after timeout period
- **Parsing errors**: Returns error with details
- **HTTP errors**: Returns error with status code

Example error handling:

```python
result = scraper.scrape(url)

if result['status'] == 'error':
    print(f"Failed to scrape {url}")
    print(f"Error: {result['error']}")
else:
    # Process successful result
    process_data(result)
```

## Best Practices

### 1. Respect Robots.txt

Always check the website's `robots.txt` file before scraping:

```python
import requests

def check_robots_txt(url):
    domain = urlparse(url).netloc
    robots_url = f"https://{domain}/robots.txt"
    response = requests.get(robots_url)
    print(response.text)
```

### 2. Add Delays Between Requests

Avoid overwhelming servers:

```python
import time

for url in urls:
    result = scraper.scrape(url)
    time.sleep(2)  # 2 second delay
```

### 3. Handle Errors Gracefully

```python
results = []
for url in urls:
    try:
        result = scraper.scrape(url)
        results.append(result)
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        continue
```

### 4. Use Appropriate Timeout

Set timeout based on expected page load time:

```python
# For fast sites
scraper = WebScraper(timeout=10)

# For slow sites
scraper = WebScraper(timeout=60)
```

## Limitations

❌ **Does not handle:**
- JavaScript-rendered content (use Selenium/Playwright for this)
- Authentication or login-required pages
- CAPTCHA challenges
- Rate limiting or IP blocking
- Binary files (PDF, DOCX) - only HTML
- Dynamic content loaded via AJAX

✅ **Best for:**
- Static HTML pages
- News articles
- Blog posts
- Documentation sites
- Product pages (static)

## Troubleshooting

### Issue: "Failed to fetch URL"

**Possible causes:**
- Network connectivity issues
- Invalid URL
- Server is down
- Blocked by firewall/proxy

**Solution:**
- Check internet connection
- Verify URL is correct
- Try increasing timeout
- Check if site is accessible in browser

### Issue: Empty or minimal text extracted

**Possible causes:**
- JavaScript-rendered content
- Content behind authentication
- Unusual HTML structure

**Solution:**
- Check if page requires JavaScript (view source in browser)
- Use Selenium/Playwright for JS-rendered content
- Inspect HTML structure and adjust selectors

### Issue: Missing metadata

**Possible causes:**
- Website doesn't include meta tags
- Non-standard meta tag format

**Solution:**
- Check page source for available meta tags
- Some sites may not include all metadata
- Extract from structured data if available

## Examples

### Example 1: News Article Scraper

```python
from web_scraper import WebScraper
import pandas as pd

scraper = WebScraper(timeout=30)

news_urls = [
    "https://example-news.com/article1",
    "https://example-news.com/article2"
]

articles = []
for url in news_urls:
    result = scraper.scrape(url)
    if result['status'] == 'success':
        articles.append({
            'title': result['metadata'].get('title'),
            'author': result['metadata'].get('author'),
            'date': result['metadata'].get('published_date'),
            'content': result['cleaned_text'],
            'url': url
        })

df = pd.DataFrame(articles)
df.to_csv('news_articles.csv', index=False)
```

### Example 2: Blog Post Scraper

```python
from web_scraper import WebScraper
import json

scraper = WebScraper()

blog_url = "https://example-blog.com/post"
result = scraper.scrape(blog_url)

if result['status'] == 'success':
    blog_post = {
        'title': result['metadata'].get('title'),
        'description': result['metadata'].get('description'),
        'content': result['cleaned_text'],
        'word_count': result['metadata'].get('word_count'),
        'image': result['metadata'].get('og_image')
    }
    
    with open('blog_post.json', 'w') as f:
        json.dump(blog_post, f, indent=2)
```

## Support

For issues or questions:
1. Check this documentation
2. Review the script comments
3. Test with example URLs first
4. Check website's robots.txt

## License

This script is provided as-is for educational and research purposes. Always respect website terms of service and robots.txt when scraping.