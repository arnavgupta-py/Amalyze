import re
import json
import time
import logging
import random
import requests
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from config import get_random_delay, get_random_user_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def extract_product_id(url):
    """Extract the Amazon product ID from a URL."""
    patterns = [
        r'/dp/([A-Z0-9]{10})',
        r'/product/([A-Z0-9]{10})',
        r'/gp/product/([A-Z0-9]{10})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def setup_browser(headless=False, user_data_dir=None):
    """Setup a Chrome browser instance with appropriate options."""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(f"--user-agent={get_random_user_agent()}")
    
    # Add user data directory if provided for session persistence
    if user_data_dir:
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    
    # Disable automation flags to avoid detection
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    try:
        # Fixed: Use explicit driver path handling to avoid issues with webdriver-manager
        driver_path = ChromeDriverManager().install()
        
        # Check if the driver exists
        if not os.path.exists(driver_path):
            logger.error(f"ChromeDriver not found at {driver_path}")
            raise FileNotFoundError(f"ChromeDriver not found at {driver_path}")
            
        logger.info(f"Using ChromeDriver from: {driver_path}")
        service = Service(executable_path=driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Execute CDP commands to mask automation
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            """
        })
        
        return driver
    except Exception as e:
        # Fallback to direct Chrome initialization if webdriver-manager fails
        logger.warning(f"Error using webdriver-manager: {e}")
        logger.info("Attempting fallback method to initialize Chrome")
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            return driver
        except Exception as fallback_error:
            logger.error(f"Fallback initialization also failed: {fallback_error}")
            raise

def save_cookies(driver, filename='cookies.json'):
    """Save browser cookies to a file."""
    cookies = driver.get_cookies()
    with open(filename, 'w') as f:
        json.dump(cookies, f)
    return cookies

def load_cookies(filename='cookies.json'):
    """Load cookies from a file."""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def apply_cookies_to_browser(driver, cookies):
    """Apply cookies to a browser session."""
    if not cookies:
        return False
    
    driver.get("https://www.amazon.in")
    for cookie in cookies:
        try:
            # Filter out problematic cookie attributes
            c = {k: v for k, v in cookie.items() 
                 if k in ['name', 'value', 'domain', 'path', 'expiry']}
            driver.add_cookie(c)
        except Exception as e:
            logger.warning(f"Failed to add cookie: {e}")
    
    # Refresh to apply cookies
    driver.refresh()
    return True

def convert_cookies_for_requests(cookies):
    """Convert browser cookies to a format suitable for requests."""
    if not cookies:
        return {}
    
    cookies_dict = {}
    for cookie in cookies:
        cookies_dict[cookie.get('name')] = cookie.get('value')
    
    return cookies_dict

def make_request_with_backoff(url, session=None, max_retries=3):
    """Make a request with exponential backoff for retries."""
    if not session:
        session = requests.Session()
        session.headers.update({"User-Agent": get_random_user_agent()})
    
    retry = 0
    while retry < max_retries:
        try:
            # Add a random delay to mimic human behavior
            time.sleep(get_random_delay())
            
            response = session.get(url, timeout=10)
            if response.status_code == 200:
                return response
            
            logger.warning(f"Request failed with status code {response.status_code}")
        except requests.RequestException as e:
            logger.warning(f"Request failed: {e}")
        
        # Exponential backoff
        retry += 1
        wait_time = 2 ** retry + random.uniform(0, 1)
        logger.info(f"Retrying in {wait_time:.2f} seconds... (Attempt {retry}/{max_retries})")
        time.sleep(wait_time)
    
    return None

def extract_text_from_element(soup, selector, default=""):
    """Extract text from a BeautifulSoup element using a CSS selector."""
    element = soup.select_one(selector)
    if element:
        return element.get_text().strip()
    return default

def extract_attribute_from_element(soup, selector, attribute, default=""):
    """Extract an attribute from a BeautifulSoup element using a CSS selector."""
    element = soup.select_one(selector)
    if element and element.has_attr(attribute):
        return element[attribute].strip()
    return default

def is_logged_in(driver):
    """Check if the user is logged into Amazon."""
    try:
        # Look for elements that indicate logged-in state
        account_text = driver.find_element(By.ID, "nav-link-accountList-nav-line-1").text
        return "Hello, sign in" not in account_text.lower()
    except:
        return False

def wait_for_login(driver, timeout=300):
    """Wait for the user to log in manually."""
    logger.info("Please log in manually in the opened browser window.")
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: is_logged_in(d)
        )
        logger.info("Login detected successfully.")
        return True
    except TimeoutException:
        logger.error(f"Login timeout after {timeout // 60} minutes.")
        return False