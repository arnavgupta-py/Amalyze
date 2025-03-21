import os
import logging
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

logger = logging.getLogger(__name__)

def create_browser():
    """Create a Chrome browser using the locally installed ChromeDriver.
    
    Returns:
        WebDriver: Chrome WebDriver instance or None if failed
    """
    try:
        # Set up Chrome options with minimal settings
        chrome_options = Options()
        
        # Basic options for stability
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-extensions")
        
        # Disable automation flags
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_experimental_option("detach", True)

        # Create Chrome driver 
        driver = webdriver.Chrome(options=chrome_options)
        time.sleep(5)
        
        # Navigate to Amazon
        driver.get("https://www.amazon.in")
        
        # Add a banner with instructions
        driver.execute_script("""
        var div = document.createElement('div');
        div.style.position = 'fixed';
        div.style.top = '0';
        div.style.left = '0';
        div.style.right = '0';
        div.style.backgroundColor = '#f0c14b';
        div.style.color = 'black';
        div.style.padding = '10px';
        div.style.zIndex = '9999';
        div.style.textAlign = 'center';
        div.style.fontSize = '16px';
        div.style.fontWeight = 'bold';
        div.innerHTML = 'Please login to Amazon. After logging in, return to the Streamlit app and click "I\\'ve Logged In Successfully"';
        document.body.appendChild(div);
        """)
        
        return driver
    
    except Exception as e:
        logger.error(f"Error creating Chrome browser: {e}")
        return None

def save_cookies(driver, filename='cookies.json'):
    """Save browser cookies to a file.
    
    Args:
        driver: Selenium WebDriver instance
        filename: File to save cookies to
        
    Returns:
        list: List of cookie dictionaries
    """
    import json
    
    try:
        cookies = driver.get_cookies()
        with open(filename, 'w') as f:
            json.dump(cookies, f)
        return cookies
    except Exception as e:
        logger.error(f"Error saving cookies: {e}")
        return []

def extract_product_id(url):
    """Extract the Amazon product ID from a URL.
    
    Args:
        url: Amazon product URL
        
    Returns:
        str: Product ID or None if not found
    """
    import re
    
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