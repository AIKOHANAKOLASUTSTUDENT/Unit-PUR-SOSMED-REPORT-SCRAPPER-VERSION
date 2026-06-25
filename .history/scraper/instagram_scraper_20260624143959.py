"""
Instagram scraper module.
Implements Apify-based scraping for /p/ URLs and Instaloader for /reel/ posts.
"""

import re
import time
from typing import Dict, List, Any

import requests

try:
    import instaloader
    from instaloader.exceptions import (
        InstaloaderException,
        QueryReturnedNotFoundException,
        TwoFactorAuthRequiredException,
    )
    HAS_INSTALOADER = True
except Exception:
    instaloader = None
    InstaloaderException = Exception
    QueryReturnedNotFoundException = Exception
    TwoFactorAuthRequiredException = Exception
    HAS_INSTALOADER = False

from config.settings import (
    APIFY_TOKEN,
    INSTAGRAM_USERNAME,
    INSTAGRAM_PASSWORD,
    REQUEST_DELAY_SECONDS,
)
from utils.logger import get_logger


APIFY_API_URL = (
    "https://api.apify.com/v2/acts/apify~instagram-scraper/run-sync-get-dataset-items"
)
APIFY_TIMEOUT_SECONDS = 60


class InstagramScraper:
    """Instagram scraper using Apify for /p/ and Instaloader for /reel/."""

    def __init__(self, strategy: str = "instaloader"):
        self.logger = get_logger()
        self.strategy = strategy.lower()

        if self.strategy not in ["instaloader", "apify"]:
            raise ValueError(f"Unknown strategy: {strategy}")

        if self.strategy == "instaloader" and not HAS_INSTALOADER:
            self.logger.warning("Instaloader not available; /reel/ scraping will not work.")

        self.instaloader_client = None
        if HAS_INSTALOADER:
            self._init_instaloader()

        self.logger.info(f"InstagramScraper initialized with strategy: {self.strategy}")

    def _init_instaloader(self):
        if not HAS_INSTALOADER:
            return

        self.instaloader_client = instaloader.Instaloader(
            sleep=False,
            compress_json=False,
        )

        login_success = False
        if INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD:
            try:
                self.instaloader_client.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
                login_success = True
                self.logger.info(f"Logged in as {INSTAGRAM_USERNAME}")
            except TwoFactorAuthRequiredException:
                self.logger.error(
                    "Instagram login requires two-factor authentication. Continuing without login."
                )
            except Exception as e:
                self.logger.warning(f"Failed to login to Instagram: {e}")
        else:
            self.logger.info("No Instagram credentials provided. Instaloader will use public access.")

        self.logger.debug(f"Login success: {login_success}")

    def scrape(self, urls: List[str]) -> List[Dict[str, Any]]:
        reel_urls = [url for url in urls if "/reel/" in url.lower()]
        post_urls = [url for url in urls if "/p/" in url.lower()]
        other_urls = [url for url in urls if url not in reel_urls and url not in post_urls]

        self.logger.info(
            f"Scraping order: {len(reel_urls)} Reels first, then {len(post_urls)} Posts"
        )

        records: List[Dict[str, Any]] = []

        for idx, url in enumerate(reel_urls):
            try:
                records.append(self._scrape_one_instaloader(url))
                self.logger.info(f"[Reel {idx+1}/{len(reel_urls)}] Scraped: {url}")
            except Exception as e:
                self.logger.error(f"Error scraping reel {url}: {e}")
                self.logger.exception(e)
                records.append(self._empty_record(url))

            if idx < len(reel_urls) - 1:
                time.sleep(REQUEST_DELAY_SECONDS)

        for idx, url in enumerate(post_urls):
            try:
                records.append(self._scrape_one_apify(url))
                self.logger.info(f"[Post {idx+1}/{len(post_urls)}] Scraped: {url}")
            except Exception as e:
                self.logger.error(f"Error scraping post {url}: {e}")
                self.logger.exception(e)
                records.append(self._empty_record(url))

            if idx < len(post_urls) - 1:
                time.sleep(REQUEST_DELAY_SECONDS)

        for idx, url in enumerate(other_urls):
            try:
                records.append(self._scrape_one(url))
                self.logger.info(f"[Other {idx+1}/{len(other_urls)}] Scraped: {url}")
            except Exception as e:
                self.logger.error(f"Error scraping {url}: {e}")
                self.logger.exception(e)
                records.append(self._empty_record(url))

            if idx < len(other_urls) - 1:
                time.sleep(REQUEST_DELAY_SECONDS)

        self.logger.info(f"Scrape complete. Got {len(records)} records")
        return records

    def _scrape_one(self, url: str) -> Dict[str, Any]:
        lower_url = url.lower()

        if "/reel/" in lower_url:
            return self._scrape_one_instaloader(url)

        if self.strategy == "apify" or "/p/" in lower_url:
            return self._scrape_one_apify(url)

        if self.strategy == "instaloader":
            return self._scrape_one_instaloader(url)

        return self._empty_record(url)

    def _empty_record(self, url: str) -> Dict[str, Any]:
        return {
            "url": url,
            "content_type": "Post",
            "likes_raw": "N/A",
            "comments_raw": "N/A",
            "views_raw": "N/A",
            "reposts_raw": "N/A",
            "saves_raw": "N/A",
            "shares_raw": "N/A",
            "post_date_raw": "N/A",
            "caption_raw": "N/A",
        }

    def _scrape_one_apify(self, url: str) -> Dict[str, Any]:
        record = self._empty_record(url)

        if not APIFY_TOKEN:
            self.logger.warning("APIFY_TOKEN not configured; cannot use Apify for /p/ URLs.")
            return record

        endpoint = f"{APIFY_API_URL}?token={APIFY_TOKEN}"
        payload = {
            "directUrls": [url],
            "resultsType": "posts",
            "resultsLimit": 1,
        }

        try:
            response = requests.post(endpoint, json=payload, timeout=APIFY_TIMEOUT_SECONDS)
            response.raise_for_status()
            data = response.json()

            if not isinstance(data, list) or len(data) == 0:
                self.logger.warning(f"Apify returned empty response for {url}")
                return record

            item = data[0]
            self.logger.debug("Raw Apify response for %s: %s", url, item)

            record["url"] = item.get("url", url)
            record["likes_raw"] = item.get("likesCount", item.get("likes", "N/A"))
            record["comments_raw"] = item.get("commentsCount", item.get("comments", "N/A"))
            record["views_raw"] = item.get("videoViewCount", "N/A")
            record["post_date_raw"] = item.get("timestamp", item.get("createdAt", "N/A"))
            record["caption_raw"] = item.get("caption", item.get("description", "")) or ""

            item_type = item.get("type", "") or item.get("mediaType", "") or item.get("productType", "")
            if not item_type:
                if "/reel/" in url.lower():
                    item_type = "Reel"
                elif "/p/" in url.lower():
                    item_type = "Post"
                else:
                    item_type = "Post"

            if item_type in ["Video", "Reel"]:
                record["content_type"] = "Reel"
            elif item_type == "Sidecar":
                record["content_type"] = "Carousel"
            else:
                record["content_type"] = "Post"

            self.logger.debug(
                "Apify parsed result for %s: type=%s likes=%s comments=%s views=%s date=%s displayUrl=%s",
                url,
                item_type,
                record["likes_raw"],
                record["comments_raw"],
                record["views_raw"],
                record["post_date_raw"],
                item.get("displayUrl", "N/A"),
            )
            return record
        except Exception as e:
            self.logger.error(f"Apify request failed for {url}: {e}")
            self.logger.exception(e)
            return record

    def _scrape_one_instaloader(self, url: str) -> Dict[str, Any]:
        record = self._empty_record(url)

        if not HAS_INSTALOADER or self.instaloader_client is None:
            self.logger.warning(f"Instaloader not available for {url}; returning empty record")
            return record

        try:
            shortcode = self._extract_shortcode(url)
            post = instaloader.Post.from_shortcode(self.instaloader_client.context, shortcode)

            self.logger.debug(
                "Instaloader post loaded: likes=%s, comments=%s, typename=%s, is_video=%s, date_utc=%s",
                getattr(post, "likes", None),
                getattr(post, "comments", None),
                getattr(post, "typename", None),
                getattr(post, "is_video", None),
                getattr(post, "date_utc", None),
            )

            record["likes_raw"] = post.likes
            record["comments_raw"] = post.comments
            record["views_raw"] = post.video_view_count if post.is_video else "N/A"
            record["post_date_raw"] = (
                post.date_utc.strftime("%Y-%m-%dT%H:%M:%S")
                if getattr(post, "date_utc", None) is not None
                else "N/A"
            )
            record["caption_raw"] = post.caption if post.caption is not None else ""

            if "/reel/" in url.lower() or getattr(post, "is_video", False):
                record["content_type"] = "Reel"
            elif getattr(post, "typename", "") == "GraphSidecar":
                record["content_type"] = "Carousel"
            else:
                record["content_type"] = "Post"

            return record
        except (InstaloaderException, QueryReturnedNotFoundException) as e:
            self.logger.warning(f"Instaloader error for {url}: {e}")
            self.logger.exception(e)
            return record
        except Exception as e:
            self.logger.error(f"Unexpected error in instaloader for {url}: {e}")
            self.logger.exception(e)
            return record

    @staticmethod
    def _extract_shortcode(url: str) -> str:
        match = re.search(r'(?:/p/|/reel/)([A-Za-z0-9_-]+)', url)
        if not match:
            raise ValueError(f"Could not extract shortcode from URL: {url}")
        return match.group(1)
