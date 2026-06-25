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
    META_APP_ID,
    META_APP_SECRET,
)
from utils.logger import get_logger


APIFY_API_URL = (
    "https://api.apify.com/v2/acts/apify~instagram-scraper/run-sync-get-dataset-items"
)
APIFY_TIMEOUT_SECONDS = 60


class InstagramScraper:
    """Instagram scraper using Meta Graph API, Apify, or Instaloader as needed."""

    def __init__(self, strategy: str = None):
        from config.settings import SCRAPER_STRATEGY, META_ACCESS_TOKEN

        self.logger = get_logger()
        self.strategy = (strategy or SCRAPER_STRATEGY).lower()
        self.meta_token_valid = False

        if self.strategy not in ["instaloader", "apify", "meta"]:
            raise ValueError(f"Unknown strategy: {strategy}")

        if self.strategy == "meta":
            if not META_ACCESS_TOKEN:
                self.logger.warning("Meta strategy selected but META_ACCESS_TOKEN is not configured.")
                self.strategy = "instaloader"
            else:
                self.meta_token_valid = self._validate_meta_access_token()
                if not self.meta_token_valid:
                    self.logger.warning("Meta access token validation failed. Falling back to other scrapers.")
                    self.strategy = "instaloader"
                else:
                    self.logger.info("Meta API enabled for Instagram scraping.")

        self.instaloader_client = None
        if self.strategy != "meta":
            if HAS_INSTALOADER:
                self._init_instaloader()
            else:
                self.logger.warning("Instaloader not available; /reel/ scraping will not work.")

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
                records.append(self._scrape_one(url))
                self.logger.info(f"[Reel {idx+1}/{len(reel_urls)}] Scraped: {url}")
            except Exception as e:
                self.logger.error(f"Error scraping reel {url}: {e}")
                self.logger.exception(e)
                records.append(self._empty_record(url))

            if idx < len(reel_urls) - 1:
                time.sleep(REQUEST_DELAY_SECONDS)

        for idx, url in enumerate(post_urls):
            try:
                records.append(self._scrape_one(url))
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
            route_type = "Reel"
        elif "/p/" in lower_url:
            route_type = "Post"
        else:
            route_type = "Post"

        self.logger.info(f"Routing {url} as {route_type}")

        if META_ACCESS_TOKEN and self.meta_token_valid:
            self.logger.info(f"Using Meta API for: {url}")
            return self._scrape_meta_api(url, route_type=route_type)

        if self.strategy == "meta" and not self.meta_token_valid:
            self.logger.warning("Meta strategy is selected but token validation failed, falling back to alternate scraper.")

        if route_type == "Reel" and HAS_INSTALOADER:
            self.logger.info(f"Using instaloader for Reel: {url}")
            return self._scrape_one_instaloader(url)

        if route_type == "Post" and APIFY_TOKEN:
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

    def _get_meta_app_access_token(self) -> str | None:
        if META_APP_ID and META_APP_SECRET:
            return f"{META_APP_ID}|{META_APP_SECRET}"
        return None

    def _validate_meta_access_token(self) -> bool:
        if not META_ACCESS_TOKEN:
            return False

        app_access_token = self._get_meta_app_access_token()
        if app_access_token:
            validate_url = f"https://graph.facebook.com/{META_API_VERSION}/debug_token"
            params = {
                "input_token": META_ACCESS_TOKEN,
                "access_token": app_access_token,
            }
            try:
                response = requests.get(validate_url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                valid = data.get("data", {}).get("is_valid", False)
                if valid:
                    self.logger.info("Meta access token validated successfully.")
                    return True
                self.logger.warning("Meta access token validation failed: %s", data.get("data"))
                return False
            except requests.exceptions.RequestException as e:
                self.logger.warning("Meta token validation request failed: %s", e)

        self.logger.debug("Attempting fallback token validation via /me endpoint.")
        try:
            fallback_url = f"https://graph.instagram.com/me"
            params = {
                "fields": "id,username",
                "access_token": META_ACCESS_TOKEN,
            }
            response = requests.get(fallback_url, params=params, timeout=30)
            response.raise_for_status()
            self.logger.info("Meta access token validated via /me endpoint.")
            return True
        except requests.exceptions.RequestException as e:
            self.logger.warning("Meta /me validation failed: %s", e)
            return False

    def _scrape_meta_api(self, url: str, route_type: str = "Post") -> Dict[str, Any]:
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

        media_id = None
        media_item = None
        found = False

        app_access_token = self._get_meta_app_access_token()
        oembed_token = app_access_token or META_ACCESS_TOKEN

        if oembed_token:
            try:
                oembed_url = f"https://graph.facebook.com/{META_API_VERSION}/instagram_oembed"
                params = {
                    "url": url,
                    "access_token": oembed_token,
                }
                response = requests.get(oembed_url, params=params, timeout=30)
                response.raise_for_status()
                oembed_data = response.json()
                self.logger.debug("oEmbed response for %s: %s", url, oembed_data)

                media_id = oembed_data.get("id") or oembed_data.get("media_id")
                if media_id:
                    self.logger.debug("oEmbed resolved media_id=%s for %s", media_id, url)
                else:
                    self.logger.debug("oEmbed response did not include media_id for %s", url)
            except requests.exceptions.RequestException as e:
                self.logger.debug("Instagram oEmbed lookup failed for %s: %s", url, e)

        if media_id:
            try:
                media_url = f"https://graph.instagram.com/{META_API_VERSION}/{media_id}"
                params = {
                    "fields": "id,shortcode,media_type,timestamp,caption,like_count,comments_count,video_view_count,permalink",
                    "access_token": META_ACCESS_TOKEN,
                }
                response = requests.get(media_url, params=params, timeout=30)
                response.raise_for_status()
                media_item = response.json()
                if media_item.get("error"):
                    raise ValueError(media_item["error"])
                self.logger.debug("Fetched media item by media_id for %s: %s", url, media_item)
                found = True
            except Exception as e:
                self.logger.debug("Fetching media by id failed for %s: %s", url, e)
                media_id = None
                media_item = None

        if not media_item and META_INSTAGRAM_ID:
            page_url = f"https://graph.instagram.com/{META_API_VERSION}/{META_INSTAGRAM_ID}/media"
            page_count = 0
            while page_count < 3 and not media_item:
                try:
                    params = {
                        "fields": "id,shortcode,media_type,timestamp,caption,like_count,comments_count,video_view_count",
                        "limit": 100,
                        "access_token": META_ACCESS_TOKEN,
                    }
                    response = requests.get(page_url, params=params, timeout=30)
                    response.raise_for_status()
                    data = response.json()

                    if "error" in data:
                        error = data["error"]
                        self.logger.error("Meta API error while searching media: %s", error)
                        return record

                    for item in data.get("data", []):
                        if item.get("shortcode", "").lower() == shortcode.lower():
                            media_item = item
                            media_id = item.get("id")
                            found = True
                            break

                    if media_item:
                        break

                    page_url = data.get("paging", {}).get("next")
                    page_count += 1
                except requests.exceptions.RequestException as e:
                    self.logger.error("Meta API request failed while paging media: %s", e)
                    return record

        if not media_item:
            if not META_INSTAGRAM_ID:
                self.logger.warning("META_INSTAGRAM_ID is not configured; cannot search account media.")
            else:
                self.logger.warning("Unable to resolve media from Meta API for %s", url)
            return record

        media_id = media_id or media_item.get("id")

        insights = {}
        if media_id:
            try:
                insights_url = f"https://graph.instagram.com/{META_API_VERSION}/{media_id}/insights"
                params = {
                    "metric": "reach,saved,shares,plays,video_views,comments",
                    "period": "lifetime",
                    "access_token": META_ACCESS_TOKEN,
                }
                response = requests.get(insights_url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                for insight in data.get("data", []):
                    name = insight.get("name")
                    value = insight.get("values", [{}])[0].get("value", "N/A")
                    insights[name] = value

                self.logger.debug("Insights for %s: %s", media_id, insights)
            except requests.exceptions.RequestException as e:
                self.logger.warning("Could not fetch Meta API insights for %s: %s", media_id, e)

        media_type = media_item.get("media_type", "IMAGE")
        if media_type == "VIDEO":
            content_type = "Reel"
        elif media_type == "CAROUSEL_ALBUM":
            content_type = "Carousel"
        else:
            content_type = "Post"

        likes = media_item.get("like_count", "N/A")
        comments = media_item.get("comments_count", "N/A")
        if comments in [None, 0, "N/A"]:
            comments = insights.get("comments", comments)

        views = insights.get("plays") or insights.get("video_views") or media_item.get("video_view_count") or media_item.get("video_views") or media_item.get("view_count") or "N/A"
        saves = insights.get("saved", "N/A")
        shares = insights.get("shares", "N/A")
        date = media_item.get("timestamp", "N/A")

        record = {
            "url": url,
            "content_type": content_type,
            "likes_raw": likes,
            "comments_raw": comments,
            "views_raw": views,
            "saves_raw": saves,
            "shares_raw": shares,
            "reposts_raw": "N/A",
            "post_date_raw": date,
            "caption_raw": media_item.get("caption", "N/A"),
        }

        self.logger.debug(
            "Meta raw %s: type=%s likes=%s comments=%s views=%s saves=%s shares=%s",
            url,
            media_type,
            likes,
            comments,
            views,
            saves,
            shares,
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


def exchange_for_long_lived_token(short_token: str, app_id: str, app_secret: str) -> str:
    """
    Exchange a short-lived token (1 hour) for a long-lived token (60 days).
    Call this once manually after generating a new token.
    
    Usage:
        long_token = exchange_for_long_lived_token(
            short_token="your_short_token",
            app_id="905091812600525",
            app_secret="your_app_secret_from_meta_dashboard"
        )
        print(long_token)  # Save this to .env as META_ACCESS_TOKEN
    """
    url = (
        f"https://graph.instagram.com/access_token"
        f"?grant_type=ig_exchange_token"
        f"&client_secret={app_secret}"
        f"&access_token={short_token}"
    )
    response = requests.get(url)
    data = response.json()
    if "access_token" in data:
        return data["access_token"]
    raise ValueError(f"Token exchange failed: {data}")
