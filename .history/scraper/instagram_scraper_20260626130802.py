"""
Instagram scraper module.
Implements Apify-based scraping for /p/ URLs and Instaloader for /reel/ posts.
"""

import re
import time
from datetime import datetime, timezone
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
        from config.settings import SCRAPER_STRATEGY

        self.logger = get_logger()
        self.strategy = (strategy or SCRAPER_STRATEGY).lower()
        self.meta_token_valid = False

        if self.strategy not in ["instaloader", "apify", "meta", "hybrid"]:
            raise ValueError(f"Unknown strategy: {strategy}")

        if META_ACCESS_TOKEN:
            self.meta_token_valid = self._validate_meta_access_token()
            if self.meta_token_valid:
                self.logger.info("Meta API enabled for Instagram scraping.")
            else:
                self.logger.warning("Meta access token validation failed. Meta API requests may not work.")

        self.instaloader_client = None
        self.cbp_followers_raw = "N/A"
        self.cbp_followers_cache = {}
        if HAS_INSTALOADER:
            self._init_instaloader()
        else:
            self.logger.warning("Instaloader not available; /reel/ scraping will not work.")

        self._load_cbp_followers()
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

    def _load_cbp_followers(self):
        if not INSTAGRAM_USERNAME:
            self.logger.warning("INSTAGRAM_USERNAME not configured; cannot fetch CBP followers count.")
            return

        # Prefer Instaloader for the CBP account follower count
        if HAS_INSTALOADER and self.instaloader_client is not None:
            try:
                profile = instaloader.Profile.from_username(self.instaloader_client.context, INSTAGRAM_USERNAME)
                self.cbp_followers_raw = profile.followers
                self.logger.info(
                    "Loaded CBP account followers (%s): %s",
                    INSTAGRAM_USERNAME,
                    self.cbp_followers_raw,
                )
                return
            except Exception as e:
                self.logger.warning("Failed to load CBP profile followers via Instaloader: %s", e)

        if META_ACCESS_TOKEN and META_INSTAGRAM_ID:
            try:
                profile_url = f"https://graph.facebook.com/{META_API_VERSION}/{META_INSTAGRAM_ID}"
                params = {
                    "fields": "followers_count",
                    "access_token": META_ACCESS_TOKEN,
                }
                response = requests.get(profile_url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                self.cbp_followers_raw = data.get("followers_count", "N/A")
                self.logger.info("Loaded CBP account followers from Meta API: %s", self.cbp_followers_raw)
            except Exception as e:
                self.logger.warning("Failed to load CBP followers via Meta API: %s", e)

    def _parse_datetime_for_insights(self, date_str: str) -> datetime | None:
        if not date_str or date_str == "N/A":
            return None

        iso_date = date_str.strip()
        if iso_date.endswith("Z"):
            iso_date = iso_date[:-1] + "+00:00"
        if re.search(r"[+-]\d{4}$", iso_date):
            iso_date = iso_date[:-5] + iso_date[-5:-2] + ":" + iso_date[-2:]

        try:
            return datetime.fromisoformat(iso_date)
        except ValueError:
            try:
                return datetime.strptime(iso_date, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                return None

    def _fetch_cbp_followers_by_date(self, date_str: str) -> Any:
        if not date_str or date_str == "N/A":
            return self.cbp_followers_raw

        if date_str in self.cbp_followers_cache:
            return self.cbp_followers_cache[date_str]

        parsed_date = self._parse_datetime_for_insights(date_str)
        if parsed_date is None:
            self.cbp_followers_cache[date_str] = self.cbp_followers_raw
            return self.cbp_followers_raw

        if META_ACCESS_TOKEN and META_INSTAGRAM_ID:
            try:
                since = int(parsed_date.replace(tzinfo=timezone.utc).timestamp())
                until = since + 86400
                insights_url = f"https://graph.facebook.com/{META_API_VERSION}/{META_INSTAGRAM_ID}/insights"
                params = {
                    "metric": "follower_count",
                    "period": "day",
                    "since": since,
                    "until": until,
                    "access_token": META_ACCESS_TOKEN,
                }
                response = requests.get(insights_url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                values = data.get("data", [])[0].get("values", []) if data.get("data") else []
                if values:
                    followers_on_date = values[-1].get("value", self.cbp_followers_raw)
                    self.cbp_followers_cache[date_str] = followers_on_date
                    return followers_on_date
                self.logger.info("No follower_count insight found for %s; using current CBP follower count.", date_str)
            except Exception as e:
                self.logger.warning("Failed to fetch CBP follower count for %s via Meta Insights: %s", date_str, e)

        self.cbp_followers_cache[date_str] = self.cbp_followers_raw
        return self.cbp_followers_raw

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

        if "/reel/" in lower_url or "/p/" in lower_url:
            self.logger.info(f"Routing as Instagram post/reel → instaloader: {url}")
            if HAS_INSTALOADER:
                try:
                    return self._scrape_instaloader(url)
                except Exception as e:
                    error_message = str(e)
                    self.logger.warning(f"Instaloader failed for {url}: {error_message}")
                    self.logger.debug("Instaloader exception details:", exc_info=e)
                    if "Fetching Post metadata failed" in error_message and META_ACCESS_TOKEN:
                        self.logger.info("Falling back to Meta API for %s due to instaloader metadata failure.", url)
                        return self._scrape_meta_api(url)

                    if "/p/" in lower_url:
                        if META_ACCESS_TOKEN:
                            return self._scrape_meta_api(url)
                        if APIFY_TOKEN:
                            return self._scrape_apify(url)

                    return self._empty_record(url)

            self.logger.warning("Instaloader not available, trying fallback scraper for %s", url)
            if "/p/" in lower_url:
                if META_ACCESS_TOKEN:
                    return self._scrape_meta_api(url)
                if APIFY_TOKEN:
                    return self._scrape_apify(url)
            return self._empty_record(url)

        else:
            self.logger.warning(f"Unknown URL format: {url}")
            return self._empty_record(url)

    def _empty_record(self, url: str) -> Dict[str, Any]:
        return {
            "url": url,
            "content_type": "Post",
            "likes_raw": "N/A",
            "comments_raw": "N/A",
            "views_raw": "N/A",
            "reach_raw": "N/A",
            "reposts_raw": "N/A",
            "saves_raw": "N/A",
            "shares_raw": "N/A",
            "followers_raw": self.cbp_followers_raw,
            "username_raw": "N/A",
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

        media_id = None
        next_url = f"https://graph.instagram.com/{META_API_VERSION}/me/media"
        params = {
            "fields": "id,shortcode",
            "limit": 100,
            "access_token": META_ACCESS_TOKEN,
        }

        for page_index in range(2):
            try:
                response = requests.get(next_url, params=params if page_index == 0 else None, timeout=30)
                response.raise_for_status()
                data = response.json()
            except requests.exceptions.RequestException as e:
                self.logger.error("Meta API /me/media request failed for %s on page %s: %s", url, page_index + 1, e)
                return record

            items = data.get("data", [])
            shortcodes = [item.get("shortcode", "") for item in items]
            if page_index == 0:
                self.logger.debug("Meta /me/media page 1 shortcodes: %s", shortcodes)

            for item in items:
                if item.get("shortcode", "").lower() == shortcode.lower():
                    media_id = item.get("id")
                    break

            if media_id:
                break

            next_url = data.get("paging", {}).get("next")
            if not next_url:
                break
            params = None

        if not media_id:
            self.logger.warning("Shortcode %s not found in first 2 pages of /me/media; returning empty record", shortcode)
            return record

        media_url = f"https://graph.instagram.com/{META_API_VERSION}/{media_id}"
        media_params = {
            "fields": "id,shortcode,media_type,timestamp,caption,like_count,comments_count",
            "access_token": META_ACCESS_TOKEN,
        }

        try:
            response = requests.get(media_url, params=media_params, timeout=30)
            response.raise_for_status()
            media_item = response.json()
            if media_item.get("error"):
                self.logger.error("Meta API media fetch error for %s: %s", url, media_item["error"])
                return record
            self.logger.debug("Meta API media response for %s: %s", url, media_item)
        except requests.exceptions.RequestException as e:
            self.logger.error("Meta API media request failed for %s: %s", url, e)
            return record

        insights = {}
        insights_url = f"https://graph.instagram.com/{META_API_VERSION}/{media_id}/insights"
        media_type = media_item.get("media_type", "IMAGE")

        if media_type == "VIDEO":
            metrics = "plays,saved,shares,reach,impressions"
        else:
            metrics = "saved,shares,reach,impressions"

        insights_params = {
            "metric": metrics,
            "period": "lifetime",
            "access_token": META_ACCESS_TOKEN,
        }

        try:
            response = requests.get(insights_url, params=insights_params, timeout=30)
            response.raise_for_status()
            data = response.json()
            if data.get("error"):
                self.logger.warning("Meta API insights error for %s: %s", url, data["error"])
            else:
                for insight in data.get("data", []):
                    name = insight.get("name")
                    value = insight.get("values", [{}])[0].get("value", "N/A")
                    insights[name] = value
                self.logger.debug("Meta API insights response for %s: %s", url, insights)
        except requests.exceptions.RequestException as e:
            self.logger.warning("Meta API insights request failed for %s: %s", url, e)

        if media_type == "VIDEO":
            content_type = "Reel"
        elif media_type == "CAROUSEL_ALBUM":
            content_type = "Carousel"
        else:
            content_type = "Post"

        post_date = media_item.get("timestamp", "N/A")
        result = {
            "url": url,
            "content_type": content_type,
            "likes_raw": media_item.get("like_count", "N/A"),
            "comments_raw": media_item.get("comments_count", "N/A"),
            "views_raw": insights.get("plays", "N/A"),
            "reach_raw": insights.get("reach", "N/A"),
            "saves_raw": insights.get("saved", "N/A"),
            "shares_raw": insights.get("shares", "N/A"),
            "reposts_raw": "N/A",
            "followers_raw": self._fetch_cbp_followers_by_date(post_date),
            "username_raw": media_item.get("username", "N/A"),
            "post_date_raw": post_date,
            "caption_raw": media_item.get("caption", "N/A"),
        }

        self.logger.debug(f"Meta API result for {url}: {result}")
        return result

    def _scrape_apify(self, url: str) -> Dict[str, Any]:
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
            record["reach_raw"] = item.get("reach", "N/A")
            record["post_date_raw"] = item.get("timestamp", item.get("createdAt", "N/A"))
            record["followers_raw"] = self._fetch_cbp_followers_by_date(record["post_date_raw"])
            record["username_raw"] = item.get("username", item.get("ownerUsername", "N/A"))
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

    def _scrape_instaloader(self, url: str) -> Dict[str, Any]:
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
            record["views_raw"] = getattr(post, "video_view_count", "N/A") if getattr(post, "is_video", False) else "N/A"
            record["reach_raw"] = "N/A"
            record["post_date_raw"] = (
                post.date_utc.strftime("%Y-%m-%dT%H:%M:%S")
                if getattr(post, "date_utc", None) is not None
                else "N/A"
            )
            record["followers_raw"] = self._fetch_cbp_followers_by_date(record["post_date_raw"])
            owner_profile = getattr(post, "owner_profile", None)
            record["username_raw"] = getattr(owner_profile, "username", "N/A") if owner_profile is not None else "N/A"
            record["caption_raw"] = post.caption if post.caption is not None else ""

            if getattr(post, "is_video", False):
                record["content_type"] = "Reel"
            elif getattr(post, "typename", "") == "GraphSidecar":
                record["content_type"] = "Carousel"
            else:
                record["content_type"] = "Post"

            return record
        except (InstaloaderException, QueryReturnedNotFoundException) as e:
            self.logger.warning(f"Instaloader error for {url}: {e}")
            self.logger.exception(e)
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in instaloader for {url}: {e}")
            self.logger.exception(e)
            raise

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
