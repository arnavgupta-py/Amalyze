import io
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from wordcloud import WordCloud
from datetime import datetime
import logging
from config import DATA_DIR

logger = logging.getLogger(__name__)

class ReviewAnalyzer:
    def __init__(self, reviews_df, product_info=None):
        """Initialize the review analyzer.
        
        Args:
            reviews_df: DataFrame containing reviews
            product_info: Optional dictionary or DataFrame with product information
        """
        self.reviews_df = reviews_df.copy()
        
        if isinstance(product_info, dict):
            self.product_info_df = pd.DataFrame([product_info])
        elif isinstance(product_info, pd.DataFrame):
            self.product_info_df = product_info.copy()
        else:
            self.product_info_df = None
        
        self.vader = SentimentIntensityAnalyzer()
        self.plotly_sentiment_comparison_html = None
        self.plots = {}
    
    def prepare_data(self):
        """Clean and prepare review data for analysis."""
        logger.info("Preparing data for analysis")
        
        # Print columns for debugging
        logger.info(f"Available columns: {self.reviews_df.columns.tolist()}")
        
        # Ensure required columns exist with proper names
        required_columns = {
            'text': ['text', 'review_text', 'content'],
            'date': ['date', 'review_date'],
            'star_rating': ['star_rating', 'rating', 'stars'],
            'verified': ['verified', 'verified_purchase']
        }
        
        for target_col, possible_names in required_columns.items():
            if target_col not in self.reviews_df.columns:
                # Try to find the column using alternative names
                for alt_name in possible_names:
                    if alt_name in self.reviews_df.columns:
                        self.reviews_df[target_col] = self.reviews_df[alt_name]
                        break
                
                # If still not found, create default columns
                if target_col not in self.reviews_df.columns:
                    if target_col == 'text':
                        self.reviews_df[target_col] = ''
                    elif target_col == 'date':
                        self.reviews_df[target_col] = pd.NaT
                    elif target_col == 'star_rating':
                        self.reviews_df[target_col] = pd.NA
                    elif target_col == 'verified':
                        self.reviews_df[target_col] = False
        
        # Clean and convert date
        if 'date' in self.reviews_df.columns:
            self.reviews_df['date'] = self.reviews_df['date'].apply(self.clean_date)
        
        # Convert star_rating to numeric
        self.reviews_df['star_rating'] = pd.to_numeric(self.reviews_df['star_rating'], errors='coerce')
        
        # Convert verified to boolean
        self.reviews_df['verified'] = self.reviews_df['verified'].fillna(False)
        
        # Fill missing text with empty string
        self.reviews_df['text'] = self.reviews_df['text'].fillna('')
        
        # Calculate sentiments
        logger.info("Calculating sentiment scores")
        self.reviews_df['textblob_sentiment'] = self.reviews_df['text'].apply(self.get_textblob_sentiment)
        self.reviews_df['vader_sentiment'] = self.reviews_df['text'].apply(self.get_vader_sentiment)
        
        # Categorize sentiments
        self.reviews_df['textblob_category'] = self.reviews_df['textblob_sentiment'].apply(
            lambda x: 'Positive' if x > 0.1 else ('Negative' if x < -0.1 else 'Neutral'))
        self.reviews_df['vader_category'] = self.reviews_df['vader_sentiment'].apply(
            lambda x: 'Positive' if x > 0.05 else ('Negative' if x < -0.05 else 'Neutral'))
        
        logger.info("Data preparation complete")
    
    def clean_date(self, date_str):
        """Clean and convert date string to datetime object.
        
        Args:
            date_str: Date string to clean
            
        Returns:
            pandas.Timestamp: Cleaned date or NaT if invalid
        """
        try:
            if pd.isna(date_str):
                return pd.NaT
            
            # Remove common prefixes
            date_str = str(date_str).replace('Reviewed in India on ', '')
            date_str = re.sub(r'Reviewed in \w+ on ', '', date_str)
            
            # Try multiple date formats
            for fmt in ['%d %B %Y', '%B %d, %Y', '%Y-%m-%d', '%d/%m/%Y', '%d %b %Y']:
                try:
                    return pd.to_datetime(date_str, format=fmt)
                except:
                    continue
            
            return pd.to_datetime(date_str, errors='coerce')
        except:
            return pd.NaT
    
    def get_textblob_sentiment(self, text):
        """Calculate TextBlob sentiment score.
        
        Args:
            text: Review text
            
        Returns:
            float: Sentiment polarity score (-1 to 1)
        """
        try:
            return TextBlob(str(text)).sentiment.polarity
        except:
            return 0.0
    
    def get_vader_sentiment(self, text):
        """Calculate VADER sentiment score.
        
        Args:
            text: Review text
            
        Returns:
            float: Compound sentiment score (-1 to 1)
        """
        try:
            return self.vader.polarity_scores(str(text))['compound']
        except:
            return 0.0
    
    def generate_all_plots(self):
        """Generate all analysis plots."""
        logger.info("Generating analysis plots")
        
        # Only generate time-based plots if we have valid dates
        has_valid_dates = (
            'date' in self.reviews_df.columns and 
            self.reviews_df['date'].notna().any()
        )
        
        # List of plot functions to call
        plot_functions = [
            ('ratings distribution', self.add_ratings_distribution_plot),
            ('sentiment distribution', self.add_sentiment_distribution_plots),
            ('word cloud', self.add_wordcloud_plot),
            ('verified purchase analysis', self.add_verified_purchase_analysis_plot),
            ('rating sentiment heatmap', self.add_rating_sentiment_heatmap_plot)
        ]
        
        # Generate each plot with error handling
        for plot_name, plot_func in plot_functions:
            try:
                logger.info(f"Generating {plot_name} plot")
                plot_func()
            except Exception as e:
                logger.error(f"Error generating {plot_name} plot: {str(e)}")
                # Create a placeholder for failed plot
                fig, ax = plt.subplots(figsize=(6, 4))
                ax.text(0.5, 0.5, f'Error generating {plot_name} plot',
                        horizontalalignment='center',
                        verticalalignment='center',
                        transform=ax.transAxes)
                ax.axis('off')
                self.plots[plot_name.title()] = self.save_plot_to_bytes(fig)
        
        # Generate interactive Plotly plots
        try:
            self.generate_plotly_sentiment_comparison()
        except Exception as e:
            logger.error(f"Error generating plotly sentiment comparison: {str(e)}")
        
        # Generate time-based plots if dates are available
        if has_valid_dates:
            try:
                self.add_time_based_plots()
            except Exception as e:
                logger.error(f"Error generating time-based plots: {str(e)}")
        
        logger.info(f"Generated {len(self.plots)} plots")
        return self.plots
    
    def add_ratings_distribution_plot(self):
        """Generate ratings distribution pie chart."""
        fig, ax = plt.subplots(figsize=(6, 6))
        ratings_count = self.reviews_df['star_rating'].value_counts().sort_index()
        
        # Define colors from red (1-star) to green (5-star)
        colors = ['#ff4d4d', '#ff9966', '#ffcc00', '#99cc33', '#66cc66']
        
        ax.pie(ratings_count, labels=[f"{star}★" for star in ratings_count.index],
               autopct='%1.1f%%', colors=colors)
        ax.set_title('Distribution of Star Ratings')
        self.plots['Ratings Distribution'] = self.save_plot_to_bytes(fig)
    
    def add_sentiment_distribution_plots(self):
        """Generate sentiment distribution pie charts."""
        # TextBlob sentiment distribution
        fig, ax = plt.subplots(figsize=(6, 6))
        textblob_count = self.reviews_df['textblob_category'].value_counts()
        ax.pie(textblob_count, labels=textblob_count.index,
               autopct='%1.1f%%', colors=['#66cc66', '#cccccc', '#ff6666'])
        ax.set_title('TextBlob Sentiment Distribution')
        self.plots['TextBlob Sentiment Distribution'] = self.save_plot_to_bytes(fig)
        
        # VADER sentiment distribution
        fig, ax = plt.subplots(figsize=(6, 6))
        vader_count = self.reviews_df['vader_category'].value_counts()
        ax.pie(vader_count, labels=vader_count.index,
               autopct='%1.1f%%', colors=['#66cc66', '#cccccc', '#ff6666'])
        ax.set_title('VADER Sentiment Distribution')
        self.plots['VADER Sentiment Distribution'] = self.save_plot_to_bytes(fig)
    
    def add_time_based_plots(self):
        """Generate time-based analysis plots."""
        # Monthly Review Volume
        try:
            monthly_reviews = self.reviews_df.set_index('date').resample('M').size()
            if len(monthly_reviews) > 0:
                fig, ax = plt.subplots(figsize=(8, 4))
                monthly_reviews.plot(kind='bar', ax=ax)
                ax.set_title('Monthly Review Volume')
                ax.set_xlabel('Month')
                ax.set_ylabel('Number of Reviews')
                plt.xticks(rotation=45)
                self.plots['Monthly Review Volume'] = self.save_plot_to_bytes(fig)
        except Exception as e:
            logger.error(f"Error generating monthly review volume plot: {str(e)}")
        
        # Sentiment Trend
        try:
            monthly_sentiment = self.reviews_df.set_index('date').resample('M').agg({
                'textblob_sentiment': 'mean',
                'vader_sentiment': 'mean'
            })
            if len(monthly_sentiment) > 0:
                fig, ax = plt.subplots(figsize=(8, 4))
                ax.plot(monthly_sentiment.index, monthly_sentiment['textblob_sentiment'], label='TextBlob')
                ax.plot(monthly_sentiment.index, monthly_sentiment['vader_sentiment'], label='VADER')
                ax.set_title('Average Sentiment Trend Over Time')
                ax.set_xlabel('Month')
                ax.set_ylabel('Sentiment Score')
                ax.legend()
                ax.grid(True)
                self.plots['Sentiment Trend'] = self.save_plot_to_bytes(fig)
        except Exception as e:
            logger.error(f"Error generating sentiment trend plot: {str(e)}")
        
        # Monthly Star Rating
        try:
            monthly_rating = self.reviews_df.set_index('date').resample('M').agg({
                'star_rating': 'mean'
            })
            if len(monthly_rating) > 0:
                fig, ax = plt.subplots(figsize=(8, 4))
                ax.plot(monthly_rating.index, monthly_rating['star_rating'], 
                       marker='o', linestyle='-', color='orange')
                ax.set_title('Average Star Rating Over Time')
                ax.set_xlabel('Month')
                ax.set_ylabel('Average Rating')
                ax.set_ylim(1, 5)
                ax.grid(True)
                self.plots['Rating Trend'] = self.save_plot_to_bytes(fig)
        except Exception as e:
            logger.error(f"Error generating rating trend plot: {str(e)}")
    
    def save_plot_to_bytes(self, fig):
        """Save matplotlib figure to bytes.
        
        Args:
            fig: Matplotlib figure
            
        Returns:
            bytes: PNG image data
        """
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()
    
    def generate_plotly_sentiment_comparison(self):
        """Generate interactive Plotly sentiment comparison plot."""
        fig = make_subplots(rows=1, cols=2)
        
        # Add scatter plot for TextBlob sentiment vs. star rating
        fig.add_trace(
            go.Scatter(x=self.reviews_df['star_rating'], y=self.reviews_df['textblob_sentiment'],
                      mode='markers', name='TextBlob', opacity=0.6),
            row=1, col=1
        )
        
        # Add scatter plot for VADER sentiment vs. star rating
        fig.add_trace(
            go.Scatter(x=self.reviews_df['star_rating'], y=self.reviews_df['vader_sentiment'],
                      mode='markers', name='VADER', opacity=0.6),
            row=1, col=2
        )
        
        # Update layout
        fig.update_layout(
            title='Correlation between Star Ratings and Sentiment Scores',
            height=500,
            width=1000
        )
        
        fig.update_xaxes(title_text="Star Rating", row=1, col=1)
        fig.update_xaxes(title_text="Star Rating", row=1, col=2)
        fig.update_yaxes(title_text="TextBlob Sentiment", row=1, col=1)
        fig.update_yaxes(title_text="VADER Sentiment", row=1, col=2)
        
        self.plotly_sentiment_comparison_html = fig.to_html(full_html=False)
    
    def add_wordcloud_plot(self):
        """Generate word cloud from review text."""
        # Combine all review text into a single string
        text = ' '.join(self.reviews_df['text'].astype(str).fillna(''))
        
        # Basic text cleaning
        text = text.lower()
        # Remove URLs
        text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        # Remove punctuation
        text = re.sub(r'[^\w\s]', '', text)
        
        # Remove common stopwords
        stop_words = set([
            'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're",
            "you've", "you'll", "you'd", 'your', 'yours', 'yourself', 'yourselves', 'he',
            'him', 'his', 'himself', 'she', "she's", 'her', 'hers', 'herself', 'it', "it's",
            'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which',
            'who', 'whom', 'this', 'that', "that'll", 'these', 'those', 'am', 'is', 'are',
            'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do',
            'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because',
            'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against',
            'between', 'into', 'through', 'during', 'before', 'after', 'above', 'below',
            'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again',
            'further', 'then', 'once'
        ])
        
        # Split into words and remove stopwords
        words = [word for word in text.split() if word.lower() not in stop_words]
        
        # Check if we have any words to plot
        if not words:
            logger.warning("No valid words found for word cloud generation")
            # Create a simple message plot instead
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.text(0.5, 0.5, 'No words available for word cloud generation',
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=ax.transAxes)
            ax.axis('off')
            self.plots['Word Cloud'] = self.save_plot_to_bytes(fig)
            return
        
        # Join words back together
        processed_text = ' '.join(words)
        
        try:
            # Generate and plot the word cloud
            wordcloud = WordCloud(
                width=800,
                height=400,
                background_color='white',
                max_words=100,
                min_font_size=10,
                max_font_size=150,
                random_state=42,  # For reproducibility
                collocations=False  # Avoid repeating word pairs
            ).generate(processed_text)
            
            # Create the matplotlib figure
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.imshow(wordcloud, interpolation='bilinear')
            ax.axis('off')
            ax.set_title('Most Common Words in Reviews')
            
            # Save to plots dictionary
            self.plots['Word Cloud'] = self.save_plot_to_bytes(fig)
            
        except Exception as e:
            logger.error(f"Error generating word cloud: {str(e)}")
            # Create an error message plot
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.text(0.5, 0.5, 'Error generating word cloud',
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=ax.transAxes)
            ax.axis('off')
            self.plots['Word Cloud'] = self.save_plot_to_bytes(fig)
    
    def add_verified_purchase_analysis_plot(self):
        """Generate verified purchase analysis plot."""
        # Create a figure for verified vs unverified purchase distribution
        fig, ax = plt.subplots(figsize=(6, 6))
        verified_counts = self.reviews_df['verified'].value_counts()
        
        labels = []
        for value in verified_counts.index:
            if value is True or value == 1:
                labels.append('Verified')
            else:
                labels.append('Unverified')
        
        ax.pie(verified_counts, 
            labels=labels,
            autopct='%1.1f%%',
            colors=['#66cc66', '#ff6666'])
        ax.set_title('Verified vs Unverified Purchases')
        self.plots['Verified Purchase Analysis'] = self.save_plot_to_bytes(fig)
    
    def add_rating_sentiment_heatmap_plot(self):
        """Generate rating vs sentiment heatmap."""
        # Create pivot table for ratings vs sentiment categories
        pivot_textblob = pd.crosstab(self.reviews_df['star_rating'], 
                                    self.reviews_df['textblob_category'])
        
        # Create heatmap
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # TextBlob heatmap
        sns.heatmap(pivot_textblob, annot=True, cmap='YlOrRd', ax=ax1)
        ax1.set_title('Rating vs TextBlob Sentiment')
        ax1.set_xlabel('Sentiment Category')
        ax1.set_ylabel('Star Rating')
        
        # VADER heatmap
        pivot_vader = pd.crosstab(self.reviews_df['star_rating'], 
                                self.reviews_df['vader_category'])
        sns.heatmap(pivot_vader, annot=True, cmap='YlOrRd', ax=ax2)
        ax2.set_title('Rating vs VADER Sentiment')
        ax2.set_xlabel('Sentiment Category')
        ax2.set_ylabel('Star Rating')
        
        plt.tight_layout()
        self.plots['Rating vs Sentiment Heatmap'] = self.save_plot_to_bytes(fig)
    
    def calculate_summary_statistics(self):
        """Calculate summary statistics for reviews.
        
        Returns:
            pandas.DataFrame: Summary statistics
        """
        # Calculate statistics
        stats = {
            'Metric': [
                'Total Reviews',
                'Average Rating',
                'Average TextBlob Sentiment',
                'Average VADER Sentiment',
                'Verified Purchase Percentage',
                'Positive Reviews (TextBlob)',
                'Negative Reviews (TextBlob)',
                'Positive Reviews (VADER)',
                'Negative Reviews (VADER)'
            ],
            'Value': [
                len(self.reviews_df),
                self.reviews_df['star_rating'].mean(),
                self.reviews_df['textblob_sentiment'].mean(),
                self.reviews_df['vader_sentiment'].mean(),
                (self.reviews_df['verified'].sum() / len(self.reviews_df)) * 100 if len(self.reviews_df) > 0 else 0,
                (self.reviews_df['textblob_category'] == 'Positive').sum(),
                (self.reviews_df['textblob_category'] == 'Negative').sum(),
                (self.reviews_df['vader_category'] == 'Positive').sum(),
                (self.reviews_df['vader_category'] == 'Negative').sum()
            ]
        }
        
        return pd.DataFrame(stats)
    
    def export_to_excel_bytes(self):
        """Export analysis to Excel file as bytes.
        
        Returns:
            bytes: Excel file data
        """
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Write product info if available
            if self.product_info_df is not None:
                self.product_info_df.to_excel(writer, sheet_name='Product Info', index=False)
            
            # Write reviews
            self.reviews_df.to_excel(writer, sheet_name='Reviews', index=False)
            
            # Write summary statistics
            summary_stats = self.calculate_summary_statistics()
            summary_stats.to_excel(writer, sheet_name='Summary Statistics', index=False)
        
        output.seek(0)
        return output.read()
    
    def export_to_excel_file(self, filename=None):
        """Export analysis to Excel file.
        
        Args:
            filename: Output filename (default: amazon_analysis_{timestamp}.xlsx)
            
        Returns:
            str: Path to the saved Excel file
        """
        if not filename:
            product_id = None
            if self.product_info_df is not None and 'product_id' in self.product_info_df.columns:
                product_id = self.product_info_df['product_id'].iloc[0]
            
            if product_id:
                filename = DATA_DIR / f"{product_id}_analysis.xlsx"
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = DATA_DIR / f"amazon_analysis_{timestamp}.xlsx"
        
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            # Write product info if available
            if self.product_info_df is not None:
                self.product_info_df.to_excel(writer, sheet_name='Product Info', index=False)
            
            # Write reviews
            self.reviews_df.to_excel(writer, sheet_name='Reviews', index=False)
            
            # Write summary statistics
            summary_stats = self.calculate_summary_statistics()
            summary_stats.to_excel(writer, sheet_name='Summary Statistics', index=False)
        
        logger.info(f"Excel file saved to {filename}")
        return filename