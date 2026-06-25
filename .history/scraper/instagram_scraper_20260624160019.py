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
    META_ACCESS_TOKEN,
    META_API_VERSION,
    META_INSTAGRAM_ID,
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

        # Use Meta API first if token is available
        if META_ACCESS_TOKEN:
            self.logger.info(f"Using Meta API for: {url}")
            return self._scrape_meta_api(url)

        # Fallback: instaloader for Reels
        if "/reel/" in lower_url and HAS_INSTALOADER:
            self.logger.info(f"Using instaloader for Reel: {url}")
            return self._scrape_one_instaloader(url)

        # Fallback: Apify for Posts
        if APIFY_TOKEN:
            self.logger.info(f"Using Apify for: {url}")
            return self._scrape_one_apify(url)

        self.logger.warning(f"No scraper available for: {url}")
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

    def _scrape_meta_api(self, url: str) -> Dict[str, Any]:
        """Scrape Instagram post using Meta Graph API."""
        record = self._empty_record(url)

        if not META_ACCESS_TOKEN:
            self.logger.warning("META_ACCESS_TOKEN not configured; cannot use Meta API.")
            return record

        try:
            shortcode = self._extract_shortcode(url)
            self.logger.debug(f"Extracted shortcode: {shortcode}")
        except ValueError as e:
            self.logger.warning(f"Could not extract shortcode from {url}: {e}")
            return record

        # Fetch all media from account to find matching shortcode
        media_id = None
        media_item = None
        page_count = 0
        next_url = f"https://graph.instagram.com/{META_API_VERSION}/{META_INSTAGRAM_ID}/media"

        while page_count < 10 and not media_id:
            try:
                params = {
                    "fields": "id,shortcode,media_type,timestamp,caption,like_count,comments_count",
                    "limit": 50,
                    "access_token": META_ACCESS_TOKEN,
                }
                response = requests.get(next_url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                if "error" in data:
                    error_code = data["error"].get("code", 0)
                    if error_code == 190:
                        self.logger.error(
                            "Meta token expired! Re-generate at developers.facebook.com"
                        )
                    elif error_code == 100:
                        self.logger.warning(f"Post not found in Meta API: {url}")
                    else:
                        self.logger.error(f"Meta API error: {data['error']}")
                    return record

                for item in data.get("data", []):
                    if item.get("shortcode", "").lower() == shortcode.lower():
                        media_id = item.get("id")
                        media_item = item
                        break

                next_url = data.get("paging", {}).get("next")
                page_count += 1

                if not next_url:
                    break

            except requests.exceptions.RequestException as e:
                self.logger.error(f"Meta API request failed: {e}")
                self.logger.exception(e)
                return record

        if not media_id or not media_item:
            self.logger.warning(f"Shortcode {shortcode} not found in Meta API")
            return record

        # Fetch insights for the media
        insights = {}
        try:
            insights_url = f"https://graph.instagram.com/{META_API_VERSION}/{media_id}/insights"
            params = {
                "metric": "impressions,reach,saved,shares,video_views,total_interactions",
                "access_token": META_ACCESS_TOKEN,
            }
            response = requests.get(insights_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            for insight in data.get("data", []):
                name = insight.get("name")
                value = insight.get("values", [{}])[0].get("value", "N/A")
                insights[name] = value

            self.logger.debug(f"Insights for {media_id}: {insights}")

        except Exception as e:
            self.logger.warning(f"Could not fetch Meta API insights for {media_id}: {e}")

        # Detect content_type
        media_type = media_item.get("media_type", "IMAGE")
        if media_type == "VIDEO":
            content_type = "Reel"
        elif media_type == "CAROUSEL_ALBUM":
            content_type = "Carousel"
        else:
            content_type = "Post"

        # Build record
        record = {
            "url": url,
            "content_type": content_type,
            "likes_raw": media_item.get("like_count", "N/A"),
            "comments_raw": media_item.get("comments_count", "N/A"),
            "views_raw": insights.get("video_views", "N/A"),
            "saves_raw": insights.get("saved", "N/A"),
            "shares_raw": insights.get("shares", "N/A"),
            "reposts_raw": "N/A",
            "post_date_raw": media_item.get("timestamp", "N/A"),
            "caption_raw": media_item.get("caption", "N/A"),
        }

        self.logger.debug(
            "Meta API result for %s: type=%s likes=%s comments=%s views=%s saves=%s shares=%s date=%s",
            url,
            media_type,
            record["likes_raw"],
            record["comments_raw"],
            record["views_raw"],
            record["saves_raw"],
            record["shares_raw"],
            record["post_date_raw"],
        )

        return record

    def _scrape_one_apify(self, url: str) -> Dict[str, Any]:
        record = self._empty_record(url)

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
