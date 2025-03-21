import re
import time
import json
import logging
import concurrent.futures
import pandas as pd
from bs4 import BeautifulSoup
from threading import Semaphore
from datetime import datetime
from queue import Queue, Empty

from config import (
    REVIEWS_URL_PATTERN, 
    STAR_FILTERS, 
    MAX_THREADS,
    MAX_PAGES_PER_STAR,
    REVIEW_SELECTORS,
    DATA_DIR,
    get_random_delay
)
from utils import make_request_with_backoff, extract_product_id

logger = logging.getLogger(__name__)

class ReviewScraper:
    def __init__(self, session=None, max_threads=MAX_THREADS):
        """Initialize the review scraper.
        
        Args:
            session: Optional requests session with cookies already set
            max_threads: Maximum number of concurrent threads
        """
        self.session = session
        self.max_threads = max_threads
        self.semaphore = Semaphore(max_threads)
        self.reviews_queue = Queue()
        self.total_reviews = 0
        self.successful_requests = 0
        self.failed_requests = 0
    
    def scrape_reviews(self, product_url, max_pages_per_star=MAX_PAGES_PER_STAR):
        """Scrape reviews for a product using multiple threads.
        
        Args:
            product_url: The Amazon product URL
            max_pages_per_star: Maximum number of pages to scrape per star rating
            
        Returns:
            pandas.DataFrame: DataFrame containing all scraped reviews
        """
        product_id = extract_product_id(product_url)
        if not product_id:
            logger.error(f"Invalid product URL: {product_url}")
            return pd.DataFrame()
        
        logger.info(f"Starting review scraping for product ID: {product_id}")
        
        # Check if cookies are properly set
        if self.session is None:
            logger.error("No session provided. Login cookies may be missing.")
            return pd.DataFrame()
            
        # Test if we can access Amazon with the current session
        test_url = f"https://www.amazon.in/product-reviews/{product_id}"
        test_response = make_request_with_backoff(test_url, self.session)
        if test_response is None:
            logger.error("Failed to access Amazon reviews. Login cookies may have expired or be invalid.")
            return pd.DataFrame()
        
        # Check if we're hitting a captcha or login wall
        if "Sign in to continue" in test_response.text or "Type the characters you see in this image" in test_response.text:
            logger.error("Amazon is requiring login or showing a captcha. Review scraping cannot proceed.")
            return pd.DataFrame()
        
        logger.info("Initial access test passed. Proceeding with review scraping.")
        
        # List of (star_rating, page_number) pairs to scrape
        scrape_tasks = []
        for star_rating in range(5, 0, -1):
            for page_number in range(1, max_pages_per_star + 1):
                scrape_tasks.append((star_rating, page_number))
        
        # Use thread pool to scrape in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            future_to_task = {
                executor.submit(
                    self._scrape_single_page, 
                    product_id, 
                    star_rating, 
                    page_number
                ): (star_rating, page_number) 
                for star_rating, page_number in scrape_tasks
            }
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_task):
                star_rating, page_number = future_to_task[future]
                try:
                    reviews_count = future.result()
                    logger.info(f"Completed {star_rating}★, page {page_number}: {reviews_count} reviews")
                except Exception as e:
                    logger.error(f"Error scraping {star_rating}★, page {page_number}: {str(e)}")
        
        # Drain the queue to create a DataFrame
        reviews = []
        while not self.reviews_queue.empty():
            try:
                reviews.append(self.reviews_queue.get(block=False))
            except Empty:
                break
        
        logger.info(f"Completed scraping: {len(reviews)} reviews collected")
        logger.info(f"Successful requests: {self.successful_requests}, Failed requests: {self.failed_requests}")
        
        # Save reviews to CSV file
        df = pd.DataFrame(reviews)
        if not df.empty:
            # Save intermediate results as a precaution
            csv_path = DATA_DIR / f"{product_id}_reviews.csv"
            df.to_csv(csv_path, index=False)
            logger.info(f"Reviews saved to {csv_path}")
        else:
            logger.warning("No reviews were collected. The dataframe is empty.")
        
        return df
    
    def _scrape_single_page(self, product_id, star_rating, page_number):
        """Scrape a single page of reviews.
        
        Args:
            product_id: The Amazon product ID
            star_rating: Star rating filter (1-5)
            page_number: Page number to scrape
            
        Returns:
            int: Number of reviews scraped from this page
        """
        with self.semaphore:
            url = REVIEWS_URL_PATTERN.format(
                product_id=product_id,
                star_filter=STAR_FILTERS[star_rating],
                page=page_number
            )
            
            # Longer delay for the first few pages to avoid being detected
            if page_number <= 2:
                time.sleep(2.0 + get_random_delay())  # Additional delay for first pages
            
            response = make_request_with_backoff(url, self.session)
            if not response:
                self.failed_requests += 1
                logger.warning(f"Failed to get response for {star_rating}★, page {page_number}")
                return 0
            
            # Check for captcha or login walls
            if "Sign in to continue" in response.text or "Type the characters you see in this image" in response.text:
                logger.error(f"Hit login wall or captcha for {star_rating}★, page {page_number}")
                self.failed_requests += 1
                return 0
            
            self.successful_requests += 1
            return self._extract_reviews_from_page(response.text, star_rating)
    
    def _extract_reviews_from_page(self, html_content, star_rating):
        """Extract reviews from a page of HTML content.
        
        Args:
            html_content: HTML content of the reviews page
            star_rating: Star rating filter used for this page
            
        Returns:
            int: Number of reviews extracted
        """
        soup = BeautifulSoup(html_content, 'lxml')
        review_elements = soup.select(REVIEW_SELECTORS["container"])
        
        if not review_elements:
            logger.warning("No review elements found on page")
            return 0
        
        count = 0
        for element in review_elements:
            try:
                # Extract review title
                title_elem = element.select_one(REVIEW_SELECTORS["title"])
                if not title_elem:
                    title_elem = element.select_one("[data-hook='review-title']")
                title = title_elem.get_text().strip() if title_elem else ""
                
                # Extract review text
                text_elem = element.select_one(REVIEW_SELECTORS["text"])
                if not text_elem:
                    text_elem = element.select_one("[data-hook='review-body']")
                text = text_elem.get_text().strip() if text_elem else ""
                
                # Extract review date
                date_elem = element.select_one(REVIEW_SELECTORS["date"])
                date_text = date_elem.get_text().strip() if date_elem else ""
                
                # Extract verified purchase status
                verified = element.select_one(REVIEW_SELECTORS["verified"]) is not None
                
                # Extract author name
                author_elem = element.select_one(REVIEW_SELECTORS["author"])
                author = author_elem.get_text().strip() if author_elem else ""
                
                # Extract rating (if available in the page)
                rating_elem = element.select_one(REVIEW_SELECTORS["rating"])
                if rating_elem:
                    rating_text = rating_elem.get_text().strip()
                    rating_match = re.search(r'(\d+(\.\d+)?)', rating_text)
                    extracted_rating = float(rating_match.group(1)) if rating_match else star_rating
                else:
                    extracted_rating = star_rating
                
                review_data = {
                    "star_rating": extracted_rating,
                    "title": title,
                    "text": text,
                    "date": date_text,
                    "verified": verified,
                    "author": author,
                    "extracted_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                self.reviews_queue.put(review_data)
                count += 1
                
            except Exception as e:
                logger.error(f"Error parsing review: {str(e)}")
                continue
        
        return count
    
    def get_reviews_count(self, df):
        """Get review count statistics.
        
        Args:
            df: DataFrame of reviews
            
        Returns:
            dict: Review count statistics
        """
        stats = {}
        if df.empty:
            return {"total": 0}
        
        # Total reviews
        stats["total"] = len(df)
        
        # Reviews by star rating
        for star in range(1, 6):
            count = len(df[df["star_rating"] == star])
            stats[f"{star}_star"] = count
        
        # Verified purchase reviews
        if "verified" in df.columns:
            stats["verified"] = df["verified"].sum()
            stats["verified_percent"] = (stats["verified"] / stats["total"]) * 100
        
        return stats
    
    def export_to_excel(self, df, product_info=None, filename=None):
        """Export reviews to Excel.
        
        Args:
            df: DataFrame of reviews
            product_info: Optional product information dictionary
            filename: Output Excel filename (default: {product_id}_analysis.xlsx)
            
        Returns:
            str: Path to the saved Excel file
        """
        if df.empty:
            logger.warning("No reviews to export")
            return None
        
        product_id = None
        if product_info and "product_id" in product_info:
            product_id = product_info["product_id"]
        
        if not filename:
            if product_id:
                filename = DATA_DIR / f"{product_id}_analysis.xlsx"
            else:
                filename = DATA_DIR / f"amazon_reviews_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            # Write product info if available
            if product_info:
                # Convert to DataFrame
                if isinstance(product_info, dict):
                    product_df = pd.DataFrame([product_info])
                else:
                    product_df = product_info
                
                product_df.to_excel(writer, sheet_name='Product Info', index=False)
            
            # Write reviews
            df.to_excel(writer, sheet_name='Reviews', index=False)
            
            # Write review count statistics
            stats = self.get_reviews_count(df)
            stats_df = pd.DataFrame({
                'Metric': list(stats.keys()),
                'Value': list(stats.values())
            })
            stats_df.to_excel(writer, sheet_name='Statistics', index=False)
        
        logger.info(f"Excel file saved to {filename}")
        return filename