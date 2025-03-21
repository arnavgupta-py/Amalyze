import random
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
os.makedirs(DATA_DIR, exist_ok=True)

# URL patterns
BASE_URL = "https://www.amazon.in"
PRODUCT_URL_PATTERN = BASE_URL + "/dp/{product_id}"
REVIEWS_URL_PATTERN = BASE_URL + "/product-reviews/{product_id}/ref=cm_cr_arp_d_viewopt_sr?ie=UTF8&reviewerType=all_reviews&filterByStar={star_filter}&pageNumber={page}"

# Scraping settings
MAX_THREADS = 10  # Maximum number of concurrent threads
MAX_RETRIES = 3   # Maximum number of retries per request
TIMEOUT = 15      # Default timeout for requests in seconds
MAX_PAGES_PER_STAR = 10  # Maximum number of pages to scrape per star rating

# Anti-bot settings
MIN_DELAY = 1.5   # Minimum delay between requests in seconds
MAX_DELAY = 3.5   # Maximum delay between requests in seconds

def get_random_delay():
    """Generate a random delay between requests to avoid detection"""
    return random.uniform(MIN_DELAY, MAX_DELAY)

# User agent list for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36 Edg/109.0.1518.78",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
]

def get_random_user_agent():
    """Get a random user agent from the list"""
    return random.choice(USER_AGENTS)

# Star rating filters
STAR_FILTERS = {
    5: "five_star",
    4: "four_star",
    3: "three_star",
    2: "two_star",
    1: "one_star",
}

# CSS selectors for product information
PRODUCT_SELECTORS = {
    "title": "#productTitle",
    "price": ["#corePrice_feature_div .a-price-whole", ".a-price .a-offscreen", "span.a-price span[aria-hidden='true']"],
    "brand": ["#bylineInfo", "#bylineInfo_feature_div a", "a#bylineInfo"],
    "about_items": "#feature-bullets .a-list-item",
    "total_ratings": "#acrCustomerReviewText",
    "star_rating": ["span.a-icon-alt", ".a-size-medium.a-color-base"]
}

# CSS selectors for review elements
REVIEW_SELECTORS = {
    "container": "[data-hook='review']",
    "title": "[data-hook='review-title'] span",
    "text": "[data-hook='review-body'] span",
    "date": "[data-hook='review-date']",
    "verified": "[data-hook='avp-badge']",
    "author": ".a-profile-name",
    "rating": "i.review-rating"
}