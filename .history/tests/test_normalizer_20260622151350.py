"""
Unit tests for transformer/normalizer.py
"""

import pytest
from transformer.normalizer import (
    normalize_count,
    normalize_date,
    normalize_caption,
    normalize_url,
)


class TestNormalizeCount:
    """Test cases for normalize_count function."""
    
    def test_normalize_count_with_k_suffix(self):
        assert normalize_count("1.2K") == 1200
        assert normalize_count("1.2k") == 1200
    
    def test_normalize_count_with_m_suffix(self):
        assert normalize_count("1.5M") == 1500000
        assert normalize_count("980K") == 980000
    
    def test_normalize_count_with_b_suffix(self):
        assert normalize_count("2.3B") == 2300000000
    
    def test_normalize_count_plain_integer_string(self):
        assert normalize_count("12400") == 12400
        assert normalize_count("0") == 0
    
    def test_normalize_count_with_commas(self):
        assert normalize_count("12,400") == 12400
        assert normalize_count("1,200,000") == 1200000
    
    def test_normalize_count_integer(self):
        assert normalize_count(500) == 500
    
    def test_normalize_count_none_or_empty(self):
        assert normalize_count(None) == "N/A"
        assert normalize_count("") == "N/A"
        assert normalize_count("N/A") == "N/A"
    
    def test_normalize_count_invalid(self):
        assert normalize_count("invalid") == "N/A"
        assert normalize_count("xyz") == "N/A"


class TestNormalizeDate:
    """Test cases for normalize_date function."""
    
    def test_normalize_date_iso_format(self):
        result = normalize_date("2024-01-15")
        assert "2024-01-15" in result
    
    def test_normalize_date_with_time(self):
        result = normalize_date("2024-01-15 10:30:00")
        assert "2024-01-15" in result
    
    def test_normalize_date_none(self):
        assert normalize_date(None) == "N/A"
        assert normalize_date("N/A") == "N/A"
    
    def test_normalize_date_malformed(self):
        assert normalize_date("invalid-date") == "N/A"
        assert normalize_date("32/13/2024") == "N/A"


class TestNormalizeCaption:
    """Test cases for normalize_caption function."""
    
    def test_normalize_caption_none(self):
        assert normalize_caption(None) == ""
    
    def test_normalize_caption_normal_text(self):
        result = normalize_caption("Hello World")
        assert result == "Hello World"
    
    def test_normalize_caption_with_newlines(self):
        result = normalize_caption("Hello\nWorld\nTest")
        assert "\n" not in result
        assert "Hello World Test" == result
    
    def test_normalize_caption_truncate(self):
        long_text = "a" * 150
        result = normalize_caption(long_text, max_length=100)
        assert len(result) == 103  # 100 chars + "..."
        assert result.endswith("...")
    
    def test_normalize_caption_strip_whitespace(self):
        result = normalize_caption("  Hello World  ")
        assert result == "Hello World"


class TestNormalizeUrl:
    """Test cases for normalize_url function."""
    
    def test_normalize_url_remove_query_params(self):
        url = "https://www.instagram.com/p/ABC123/?utm_source=test"
        result = normalize_url(url)
        assert "?" not in result
    
    def test_normalize_url_add_trailing_slash(self):
        url = "https://www.instagram.com/p/ABC123"
        result = normalize_url(url)
        assert result.endswith("/")
    
    def test_normalize_url_already_clean(self):
        url = "https://www.instagram.com/p/ABC123/"
        result = normalize_url(url)
        assert result == url
    
    def test_normalize_url_empty_string(self):
        assert normalize_url("") == ""
