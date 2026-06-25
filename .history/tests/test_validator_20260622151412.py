"""
Unit tests for transformer/validator.py
"""

import pytest
from transformer.validator import validate_record


class TestValidateRecord:
    """Test cases for validate_record function."""
    
    def test_validate_record_fully_valid(self):
        record = {
            "url": "https://www.instagram.com/p/ABC123/",
            "content_type": "Post",
            "post_date": "2024-01-15 10:30:00",
            "likes": 100,
            "comments": 50,
            "views": 1000,
            "reposts": 10,
            "saves": 20,
            "shares": 5,
            "caption": "Test caption",
            "ingestion_timestamp": "2024-01-15 10:30:00",
        }
        ok, reason = validate_record(record)
        assert ok is True
        assert reason == ""
    
    def test_validate_record_missing_url(self):
        record = {
            "content_type": "Post",
            "post_date": "2024-01-15 10:30:00",
            "likes": 100,
            "ingestion_timestamp": "2024-01-15 10:30:00",
        }
        ok, reason = validate_record(record)
        assert ok is False
        assert "URL" in reason
    
    def test_validate_record_invalid_url_format(self):
        record = {
            "url": "https://twitter.com/user/status/123",
            "content_type": "Post",
            "post_date": "2024-01-15 10:30:00",
            "likes": 100,
            "ingestion_timestamp": "2024-01-15 10:30:00",
        }
        ok, reason = validate_record(record)
        assert ok is False
        assert "Invalid URL" in reason
    
    def test_validate_record_invalid_content_type(self):
        record = {
            "url": "https://www.instagram.com/p/ABC123/",
            "content_type": "Story",  # Invalid
            "post_date": "2024-01-15 10:30:00",
            "likes": 100,
            "ingestion_timestamp": "2024-01-15 10:30:00",
        }
        ok, reason = validate_record(record)
        assert ok is False
        assert "content_type" in reason
    
    def test_validate_record_missing_post_date(self):
        record = {
            "url": "https://www.instagram.com/p/ABC123/",
            "content_type": "Post",
            "likes": 100,
            "ingestion_timestamp": "2024-01-15 10:30:00",
        }
        ok, reason = validate_record(record)
        assert ok is False
        assert "post_date" in reason
    
    def test_validate_record_post_date_is_na(self):
        record = {
            "url": "https://www.instagram.com/p/ABC123/",
            "content_type": "Post",
            "post_date": "N/A",
            "likes": 100,
            "ingestion_timestamp": "2024-01-15 10:30:00",
        }
        ok, reason = validate_record(record)
        assert ok is False
        assert "N/A" in reason
    
    def test_validate_record_invalid_likes_none(self):
        record = {
            "url": "https://www.instagram.com/p/ABC123/",
            "content_type": "Post",
            "post_date": "2024-01-15 10:30:00",
            "likes": None,
            "ingestion_timestamp": "2024-01-15 10:30:00",
        }
        ok, reason = validate_record(record)
        assert ok is False
        assert "likes" in reason
    
    def test_validate_record_invalid_likes_empty_string(self):
        record = {
            "url": "https://www.instagram.com/p/ABC123/",
            "content_type": "Post",
            "post_date": "2024-01-15 10:30:00",
            "likes": "",
            "ingestion_timestamp": "2024-01-15 10:30:00",
        }
        ok, reason = validate_record(record)
        assert ok is False
        assert "likes" in reason
    
    def test_validate_record_likes_na_valid(self):
        record = {
            "url": "https://www.instagram.com/p/ABC123/",
            "content_type": "Post",
            "post_date": "2024-01-15 10:30:00",
            "likes": "N/A",
            "ingestion_timestamp": "2024-01-15 10:30:00",
        }
        ok, reason = validate_record(record)
        assert ok is True
    
    def test_validate_record_missing_ingestion_timestamp(self):
        record = {
            "url": "https://www.instagram.com/p/ABC123/",
            "content_type": "Post",
            "post_date": "2024-01-15 10:30:00",
            "likes": 100,
        }
        ok, reason = validate_record(record)
        assert ok is False
        assert "ingestion_timestamp" in reason
    
    def test_validate_record_valid_reel(self):
        record = {
            "url": "https://www.instagram.com/reel/ABC123/",
            "content_type": "Reel",
            "post_date": "2024-01-15 10:30:00",
            "likes": 500,
            "comments": 50,
            "views": 5000,
            "reposts": 100,
            "saves": 200,
            "shares": 50,
            "caption": "Test reel",
            "ingestion_timestamp": "2024-01-15 10:30:00",
        }
        ok, reason = validate_record(record)
        assert ok is True
