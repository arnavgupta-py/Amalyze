# Amalyze: Amazon Product Review Analyzer

Amalyze is a powerful Streamlit-based web application that enables users to scrape, analyze, and visualize Amazon product reviews. The application provides sentiment analysis, rating distributions, word clouds, and time-based trend analysis to help understand customer feedback.

## Features

- **Amazon Login Integration**: Securely log in to access review data
- **Product Information Scraping**: Extract product details, pricing, and features
- **Review Collection**: Gather reviews filtered by star rating with pagination support
- **Sentiment Analysis**: Dual analysis using TextBlob and VADER for nuanced sentiment understanding
- **Rich Visualizations**:
  - Rating distributions
  - Sentiment analysis charts
  - Word clouds of review text
  - Verified vs. unverified purchase analysis
  - Time-based trends
  - Heatmaps correlating ratings and sentiment
- **Data Export**: Download complete analysis in Excel format

## Installation

### Prerequisites

- Python 3.8+
- Chrome browser installed
- ChromeDriver matching your Chrome version

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/arnavgupta-py/Amalyze.git
   cd Amalyze
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Start the Streamlit application:
   ```bash
   streamlit run app.py
   ```

2. The application will open in your default web browser with three main tabs:

   - **Login**: Connect to your Amazon account
   - **Scrape**: Collect product information and reviews
   - **Analyze**: Generate visualizations and insights

### Step-by-Step Guide

1. **Login Tab**:
   - Click "Open Amazon Login Page" to launch a Chrome window
   - Log in to your Amazon account
   - Return to the app and click "I've Logged In Successfully"

2. **Scrape Tab**:
   - Enter an Amazon.in product URL
   - Click "Scrape Product Info" to get basic product details
   - Click "Scrape Reviews" to collect user reviews (adjust pages per star rating in settings)

3. **Analyze Tab**:
   - Click "Analyze Reviews" to generate all visualizations
   - Explore the various charts and insights
   - Download the complete analysis as an Excel file

## Project Structure

- `app.py`: Main Streamlit application
- `analyzer.py`: Review analysis and visualization generation
- `browser.py`: Browser session management
- `config.py`: Configuration settings and constants
- `product_scraper.py`: Product information scraping
- `reviews_scraper.py`: Review collection functionality
- `utils.py`: Utility functions for scraping and browser interaction

## Anti-Detection Measures

Amalyze implements several measures to avoid triggering Amazon's anti-scraping systems:

- Random delays between requests
- User agent rotation
- Proper cookie handling
- Request throttling

## Legal Disclaimer

This tool is for educational and personal use only. Web scraping may violate Amazon's Terms of Service. Use responsibly and at your own risk. The developers are not responsible for any misuse or consequences resulting from the use of this tool.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Streamlit](https://streamlit.io/) for the web application framework
- [Selenium](https://selenium-python.readthedocs.io/) for browser automation
- [TextBlob](https://textblob.readthedocs.io/) and [VADER](https://github.com/cjhutto/vaderSentiment) for sentiment analysis
- [Matplotlib](https://matplotlib.org/), [Seaborn](https://seaborn.pydata.org/), and [Plotly](https://plotly.com/) for visualizations
