"""
Unit tests for scraper/instagram_scraper.py
"""

import pytest
from scraper.instagram_scraper import InstagramScraper


class TestInstagramScraperInit:
    """Test cases for InstagramScraper initialization."""
    
    def test_init_with_instaloader_strategy(self):
        scraper = InstagramScraper(strategy="instaloader")
        assert scraper.strategy == "instaloader"
    
    def test_init_with_playwright_strategy(self):
        with pytest.raises(ValueError):
            InstagramScraper(strategy="playwright")
    
    def test_init_with_apify_strategy(self):
        scraper = InstagramScraper(strategy="apify")
        assert scraper.strategy == "apify"
    
    def test_init_with_invalid_strategy(self):
        with pytest.raises(ValueError):
            InstagramScraper(strategy="invalid")
    
    def test_init_case_insensitive(self):
        scraper = InstagramScraper(strategy="INSTALOADER")
        assert scraper.strategy == "instaloader"


class TestExtractShortcode:
    """Test cases for _extract_shortcode helper method."""
    
    def test_extract_shortcode_from_post_url(self):
        url = "https://www.instagram.com/p/ABC123def-_456/"
        shortcode = InstagramScraper._extract_shortcode(url)
        assert shortcode == "ABC123def-_456"
    
    def test_extract_shortcode_from_reel_url(self):
        url = "https://www.instagram.com/reel/XYZ789_ABC/"
        shortcode = InstagramScraper._extract_shortcode(url)
        assert shortcode == "XYZ789_ABC"
    
    def test_extract_shortcode_malformed_url(self):
        url = "https://www.instagram.com/profile/username/"
        with pytest.raises(ValueError):
            InstagramScraper._extract_shortcode(url)
    
    def test_extract_shortcode_with_query_params(self):
        url = "https://www.instagram.com/p/ABC123/?utm_source=test"
        shortcode = InstagramScraper._extract_shortcode(url)
        assert shortcode == "ABC123"
    
    def test_extract_shortcode_handles_underscores_dashes(self):
        url = "https://www.instagram.com/p/A-B_C-D_E-F/"
        shortcode = InstagramScraper._extract_shortcode(url)
        assert shortcode == "A-B_C-D_E-F"
