import re
import logging
import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from config import PRODUCT_URL_PATTERN, PRODUCT_SELECTORS
from utils import extract_product_id, make_request_with_backoff

logger = logging.getLogger(__name__)

class ProductScraper:
    def __init__(self, session=None):
        """Initialize the product scraper.
        
        Args:
            session: Optional requests session with cookies already set
        """
        self.session = session or requests.Session()
        self.product_info = {}
    
    def scrape_product(self, url):
        """Scrape product information from an Amazon product page.
        
        Args:
            url: The full Amazon product URL
            
        Returns:
            dict: Product information
        """
        product_id = extract_product_id(url)
        if not product_id:
            logger.error(f"Invalid product URL: {url}")
            return None
        
        product_url = PRODUCT_URL_PATTERN.format(product_id=product_id)
        response = make_request_with_backoff(product_url, self.session)
        
        if not response:
            logger.error("Failed to retrieve product page")
            return None
        
        self.product_info = self._extract_product_info(response.text, product_id)
        return self.product_info
    
    def _extract_product_info(self, html_content, product_id):
        """Extract product information from HTML content.
        
        Args:
            html_content: HTML content of the product page
            product_id: The Amazon product ID
            
        Returns:
            dict: Product information
        """
        soup = BeautifulSoup(html_content, 'lxml')
        product_info = {"product_id": product_id}
        
        # Extract title
        title_elem = soup.select_one(PRODUCT_SELECTORS["title"])
        product_info["title"] = title_elem.get_text().strip() if title_elem else "Not found"
        
        # Extract price
        price = None
        for price_selector in PRODUCT_SELECTORS["price"]:
            price_elem = soup.select_one(price_selector)
            if price_elem:
                price_text = price_elem.get_text().strip()
                # Extract numeric price from text
                price_match = re.search(r'([\d,]+(\.\d+)?)', price_text)
                if price_match:
                    price = price_match.group(1)
                    break
        
        product_info["price"] = f"₹{price}" if price else "Not found"
        
        # Extract brand
        brand = None
        for brand_selector in PRODUCT_SELECTORS["brand"]:
            brand_elem = soup.select_one(brand_selector)
            if brand_elem:
                brand_text = brand_elem.get_text().strip()
                # Clean up brand text
                if "Brand:" in brand_text:
                    brand = brand_text.replace("Brand:", "").strip()
                else:
                    brand = brand_text
                break
        
        product_info["brand"] = brand if brand else "Not found"
        
        # Extract about items
        about_items = []
        items_elements = soup.select(PRODUCT_SELECTORS["about_items"])
        about_items = [item.get_text().strip() for item in items_elements if item.get_text().strip()]
        product_info["about_this_item"] = about_items
        
        # Extract ratings info
        ratings_elem = soup.select_one(PRODUCT_SELECTORS["total_ratings"])
        if ratings_elem:
            ratings_text = ratings_elem.get_text().strip()
            ratings_match = re.search(r'([\d,]+)', ratings_text)
            product_info["total_ratings"] = ratings_match.group(1) if ratings_match else "Not found"
        else:
            product_info["total_ratings"] = "Not found"
        
        # Extract star rating
        star_rating = None
        for rating_selector in PRODUCT_SELECTORS["star_rating"]:
            star_elem = soup.select_one(rating_selector)
            if star_elem:
                star_text = star_elem.get_text()
                star_match = re.search(r'(\d+(\.\d+)?)', star_text)
                if star_match:
                    star_rating = star_match.group(1)
                    break
        
        product_info["star_rating"] = star_rating if star_rating else "Not found"
        
        return product_info
    
    def selenium_scrape_product(self, driver, url):
        """Scrape product using Selenium for dynamic content.
        
        Args:
            driver: Selenium webdriver
            url: Amazon product URL
            
        Returns:
            dict: Product information
        """
        product_id = extract_product_id(url)
        if not product_id:
            logger.error(f"Invalid product URL: {url}")
            return None
        
        driver.get(url)
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "productTitle"))
            )
        except TimeoutException:
            logger.error("Timeout waiting for product page to load")
            return None
        
        product_info = {"product_id": product_id}
        
        # Extract title
        try:
            title_element = driver.find_element(By.ID, "productTitle")
            product_info["title"] = title_element.text.strip()
        except NoSuchElementException:
            product_info["title"] = "Not found"
        
        # Extract price
        price = None
        for selector in PRODUCT_SELECTORS["price"]:
            try:
                price_element = driver.find_element(By.CSS_SELECTOR, selector)
                price_text = price_element.text.strip()
                price_match = re.search(r'([\d,]+(\.\d+)?)', price_text)
                if price_match:
                    price = price_match.group(1)
                    break
            except NoSuchElementException:
                continue
        
        product_info["price"] = f"₹{price}" if price else "Not found"
        
        # Extract brand
        brand = None
        for selector in PRODUCT_SELECTORS["brand"]:
            try:
                brand_element = driver.find_element(By.CSS_SELECTOR, selector)
                brand_text = brand_element.text.strip()
                if "Brand:" in brand_text:
                    brand = brand_text.replace("Brand:", "").strip()
                else:
                    brand = brand_text
                break
            except NoSuchElementException:
                continue
        
        product_info["brand"] = brand if brand else "Not found"
        
        # Extract about items
        try:
            about_items_elements = driver.find_elements(By.CSS_SELECTOR, PRODUCT_SELECTORS["about_items"])
            product_info["about_this_item"] = [item.text.strip() for item in about_items_elements if item.text.strip()]
        except:
            product_info["about_this_item"] = []
        
        # Extract ratings info
        try:
            ratings_element = driver.find_element(By.ID, "acrCustomerReviewText")
            ratings_text = ratings_element.text.strip()
            ratings_match = re.search(r'([\d,]+)', ratings_text)
            product_info["total_ratings"] = ratings_match.group(1) if ratings_match else "Not found"
        except:
            product_info["total_ratings"] = "Not found"
        
        # Extract star rating
        star_rating = None
        for selector in PRODUCT_SELECTORS["star_rating"]:
            try:
                star_element = driver.find_element(By.CSS_SELECTOR, selector)
                star_text = star_element.text
                star_match = re.search(r'(\d+(\.\d+)?)', star_text)
                if star_match:
                    star_rating = star_match.group(1)
                    break
            except NoSuchElementException:
                continue
        
        product_info["star_rating"] = star_rating if star_rating else "Not found"
        
        self.product_info = product_info
        return product_info