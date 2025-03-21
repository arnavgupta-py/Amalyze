import os
import json
import logging
import pandas as pd
import streamlit as st
import time
import sys
import traceback

# Import the simple browser setup
from browser import create_browser, save_cookies, extract_product_id
from product_scraper import ProductScraper
from reviews_scraper import ReviewScraper
from analyzer import ReviewAnalyzer
from config import DATA_DIR, MAX_PAGES_PER_STAR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    st.set_page_config(page_title="Amalyze: Amazon Product Review Analyzer", layout="wide")
    
    st.title("Amalyze: Amazon Product Review Analyzer")
    st.write("Enter an Amazon.in product URL, log in to Amazon, then scrape and analyze product reviews.")
    
    # Sidebar for configuration
    st.sidebar.title("Settings")
    max_pages = st.sidebar.slider(
        "Pages per star rating (max 10):", 
        min_value=1, 
        max_value=10, 
        value=3
    )
    
    # Create data directory if it doesn't exist
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Main content
    product_url = st.text_input("Amazon Product URL:")
    
    tab1, tab2, tab3 = st.tabs(["Login", "Scrape", "Analyze"])
    
    with tab1:
        st.header("Step 1: Login to Amazon")
        st.write("You need to log in to Amazon to scrape reviews.")
        
        # Store browser in session state so it remains open
        if 'browser_open' not in st.session_state:
            st.session_state.browser_open = False
            st.session_state.driver = None
        
        st.info("""
        **Important**: 
        1. Click "Open Amazon Login Page" to launch a Chrome window
        2. Log in to your Amazon account in this window
        3. Return to this app and click "I've Logged In Successfully"
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Open Amazon Login Page"):
                if not st.session_state.browser_open:
                    with st.spinner("Opening Chrome browser... This may take a moment"):
                        driver = create_browser()
                        
                        if driver:
                            st.session_state.driver = driver
                            st.session_state.browser_open = True
                            st.success("Amazon login page opened. Please log in and then click 'I've Logged In Successfully'.")
                        else:
                            st.error("Failed to open browser. Make sure ChromeDriver is installed and in your PATH.")
                else:
                    st.warning("Browser is already open. Please log in and then click 'I've Logged In Successfully'.")
        
        with col2:
            # Only show the login confirmation button if browser is open
            if st.session_state.browser_open:
                if st.button("I've Logged In Successfully"):
                    if st.session_state.driver:
                        try:
                            # Save cookies after user confirms login
                            cookies = save_cookies(st.session_state.driver)
                            st.session_state['amazon_cookies'] = cookies
                            st.success(f"Login confirmed! {len(cookies)} cookies saved.")
                            
                            # Close the browser after getting cookies
                            st.session_state.driver.quit()
                            st.session_state.driver = None
                            st.session_state.browser_open = False
                        except Exception as e:
                            st.error(f"Error saving cookies: {str(e)}")
                            try:
                                st.session_state.driver.quit()
                            except:
                                pass
                            st.session_state.driver = None
                            st.session_state.browser_open = False
        
        # Add a way to close the browser if needed
        if st.session_state.browser_open:
            if st.button("Cancel Login / Close Browser"):
                try:
                    st.session_state.driver.quit()
                except:
                    pass
                st.session_state.driver = None
                st.session_state.browser_open = False
                st.info("Browser closed.")
        
        # Show current login status
        if 'amazon_cookies' in st.session_state:
            st.success("✅ You are logged in and ready to scrape.")
        else:
            st.warning("⚠️ Not logged in yet. Please complete the login process.")
    
    with tab2:
        st.header("Step 2: Scrape Product Reviews")
        
        if product_url:
            product_id = extract_product_id(product_url)
            if not product_id:
                st.error("Invalid product URL. Could not extract product ID.")
            else:
                st.write(f"Product ID: {product_id}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Scrape Product Info"):
                        if 'amazon_cookies' not in st.session_state:
                            st.error("Please log in to Amazon first (Step 1).")
                        else:
                            with st.spinner("Scraping product information..."):
                                driver = create_browser()
                                
                                if driver:
                                    try:
                                        # Add cookies to the browser
                                        for cookie in st.session_state['amazon_cookies']:
                                            try:
                                                cookie_dict = {k: v for k, v in cookie.items() 
                                                              if k in ['name', 'value', 'domain', 'path']}
                                                driver.add_cookie(cookie_dict)
                                            except Exception as e:
                                                logger.warning(f"Failed to add cookie: {e}")
                                        
                                        # Refresh to apply cookies
                                        driver.refresh()
                                        time.sleep(2)  # Wait for cookies to take effect
                                        
                                        # Navigate to product page
                                        driver.get(product_url)
                                        time.sleep(3)  # Wait for page to load
                                        
                                        # Scrape product info
                                        product_scraper = ProductScraper()
                                        product_info = product_scraper.selenium_scrape_product(driver, product_url)
                                        
                                        if product_info:
                                            st.session_state['product_info'] = product_info
                                            st.success("Product information scraped successfully!")
                                            
                                            # Display product info
                                            st.subheader("Product Information")
                                            for key, value in product_info.items():
                                                if key != 'about_this_item':
                                                    st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                                            
                                            if product_info.get('about_this_item'):
                                                st.write("**About This Item:**")
                                                for item in product_info['about_this_item']:
                                                    st.write(f"- {item}")
                                        else:
                                            st.error("Failed to scrape product information.")
                                    except Exception as e:
                                        st.error(f"Error during product scraping: {str(e)}")
                                        logger.error(traceback.format_exc())
                                    finally:
                                        try:
                                            driver.quit()
                                        except:
                                            pass
                                else:
                                    st.error("Failed to open browser. Make sure ChromeDriver is installed and in your PATH.")
                
                with col2:
                    if st.button("Scrape Reviews"):
                        if 'amazon_cookies' not in st.session_state:
                            st.error("Please log in to Amazon first (Step 1).")
                        else:
                            with st.spinner(f"Scraping up to {max_pages} pages per star rating..."):
                                # Create a requests session with cookies
                                import requests
                                session = requests.Session()
                                
                                # Convert cookies to requests format
                                cookies_dict = {}
                                for cookie in st.session_state['amazon_cookies']:
                                    cookies_dict[cookie.get('name')] = cookie.get('value')
                                
                                session.cookies.update(cookies_dict)
                                
                                # Add a user agent to the session
                                session.headers.update({
                                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
                                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                                    "Accept-Language": "en-US,en;q=0.9",
                                    "Connection": "keep-alive"
                                })
                                
                                # Scrape reviews
                                review_scraper = ReviewScraper(session=session)
                                reviews_df = review_scraper.scrape_reviews(product_url, max_pages_per_star=max_pages)
                                
                                if not reviews_df.empty:
                                    st.session_state['reviews_df'] = reviews_df
                                    st.success(f"Successfully scraped {len(reviews_df)} reviews!")
                                    
                                    # Display review counts by star rating
                                    st.subheader("Reviews by Star Rating")
                                    star_counts = reviews_df['star_rating'].value_counts().sort_index()
                                    for star, count in star_counts.items():
                                        st.write(f"**{star}★:** {count} reviews")
                                    
                                    # Download raw reviews
                                    reviews_csv = reviews_df.to_csv(index=False).encode('utf-8')
                                    st.download_button(
                                        "Download Raw Reviews (CSV)",
                                        reviews_csv,
                                        f"{product_id}_reviews.csv",
                                        "text/csv",
                                        key='download-csv'
                                    )
                                else:
                                    st.error("Failed to scrape reviews or no reviews found.")
    
    with tab3:
        st.header("Step 3: Analyze Reviews")
        
        if 'reviews_df' not in st.session_state:
            st.info("Please scrape reviews first (Step 2).")
        else:
            if st.button("Analyze Reviews"):
                with st.spinner("Analyzing reviews and generating visualizations..."):
                    product_info = st.session_state.get('product_info', None)
                    reviews_df = st.session_state['reviews_df']
                    
                    # Analyze reviews
                    analyzer = ReviewAnalyzer(reviews_df, product_info)
                    analyzer.prepare_data()
                    plots = analyzer.generate_all_plots()
                    excel_bytes = analyzer.export_to_excel_bytes()
                    
                    # Store analysis results for display
                    st.session_state['analysis_plots'] = plots
                    st.session_state['analysis_excel'] = excel_bytes
                    st.session_state['analyzer'] = analyzer
                
                st.success("Analysis complete!")
            
            # Display analysis results if available
            if 'analysis_plots' in st.session_state:
                st.subheader("Analysis Results")
                
                # Download Excel with full analysis
                st.download_button(
                    "Download Complete Analysis (Excel)",
                    st.session_state['analysis_excel'],
                    "amazon_review_analysis.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key='download-excel'
                )
                
                # Display summary statistics
                if 'analyzer' in st.session_state:
                    st.subheader("Summary Statistics")
                    stats_df = st.session_state['analyzer'].calculate_summary_statistics()
                    
                    # Convert to a more display-friendly format
                    stats_dict = dict(zip(stats_df['Metric'], stats_df['Value']))
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Total Reviews", f"{stats_dict['Total Reviews']:.0f}")
                        st.metric("Average Rating", f"{stats_dict['Average Rating']:.2f}★")
                        st.metric("Verified Purchases", f"{stats_dict['Verified Purchase Percentage']:.1f}%")
                    
                    with col2:
                        st.metric("Positive Reviews (VADER)", f"{stats_dict['Positive Reviews (VADER)']:.0f}")
                        st.metric("Negative Reviews (VADER)", f"{stats_dict['Negative Reviews (VADER)']:.0f}")
                        st.metric("Average Sentiment", f"{stats_dict['Average VADER Sentiment']:.2f}")
                
                # Display visualizations
                st.subheader("Visualizations")
                
                # Organize plots into tabs
                viz_tabs = st.tabs([
                    "Ratings", "Sentiment", "Word Cloud", 
                    "Verified vs Unverified", "Time Analysis"
                ])
                
                with viz_tabs[0]:  # Ratings tab
                    if "Ratings Distribution" in st.session_state['analysis_plots']:
                        st.image(
                            st.session_state['analysis_plots']["Ratings Distribution"],
                            caption="Ratings Distribution",
                            use_column_width=True
                        )
                    
                    if "Rating vs Sentiment Heatmap" in st.session_state['analysis_plots']:
                        st.image(
                            st.session_state['analysis_plots']["Rating vs Sentiment Heatmap"],
                            caption="Rating vs Sentiment Heatmap",
                            use_column_width=True
                        )
                
                with viz_tabs[1]:  # Sentiment tab
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if "TextBlob Sentiment Distribution" in st.session_state['analysis_plots']:
                            st.image(
                                st.session_state['analysis_plots']["TextBlob Sentiment Distribution"],
                                caption="TextBlob Sentiment Distribution",
                                use_column_width=True
                            )
                    
                    with col2:
                        if "VADER Sentiment Distribution" in st.session_state['analysis_plots']:
                            st.image(
                                st.session_state['analysis_plots']["VADER Sentiment Distribution"],
                                caption="VADER Sentiment Distribution",
                                use_column_width=True
                            )
                    
                    # Interactive Plotly visualization
                    if 'analyzer' in st.session_state and st.session_state['analyzer'].plotly_sentiment_comparison_html:
                        st.subheader("Interactive Sentiment Analysis")
                        st.components.v1.html(
                            st.session_state['analyzer'].plotly_sentiment_comparison_html,
                            height=550
                        )
                
                with viz_tabs[2]:  # Word Cloud tab
                    if "Word Cloud" in st.session_state['analysis_plots']:
                        st.image(
                            st.session_state['analysis_plots']["Word Cloud"],
                            caption="Word Cloud of Review Text",
                            use_column_width=True
                        )
                
                with viz_tabs[3]:  # Verified vs Unverified tab
                    if "Verified Purchase Analysis" in st.session_state['analysis_plots']:
                        st.image(
                            st.session_state['analysis_plots']["Verified Purchase Analysis"],
                            caption="Verified vs Unverified Purchases",
                            use_column_width=True
                        )
                
                with viz_tabs[4]:  # Time Analysis tab
                    if "Monthly Review Volume" in st.session_state['analysis_plots']:
                        st.image(
                            st.session_state['analysis_plots']["Monthly Review Volume"],
                            caption="Monthly Review Volume",
                            use_column_width=True
                        )
                    
                    if "Sentiment Trend" in st.session_state['analysis_plots']:
                        st.image(
                            st.session_state['analysis_plots']["Sentiment Trend"],
                            caption="Sentiment Trend Over Time",
                            use_column_width=True
                        )
                    
                    if "Rating Trend" in st.session_state['analysis_plots']:
                        st.image(
                            st.session_state['analysis_plots']["Rating Trend"],
                            caption="Rating Trend Over Time",
                            use_column_width=True
                        )

# Clean up browser before exit
def cleanup():
    if hasattr(st.session_state, 'driver') and st.session_state.driver is not None:
        try:
            st.session_state.driver.quit()
        except:
            pass
        st.session_state.driver = None
        st.session_state.browser_open = False

if __name__ == "__main__":
    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)
    
    try:
        main()
    finally:
        # Ensure browser is closed when app is exited
        cleanup()