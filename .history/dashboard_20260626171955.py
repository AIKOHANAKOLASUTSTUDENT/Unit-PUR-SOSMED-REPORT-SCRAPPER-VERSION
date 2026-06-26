"""
Streamlit web dashboard for Instagram Engagement Scraper.
Provides a user-friendly interface for scraping Instagram URLs without coding.
"""
import streamlit as st
import pandas as pd
import re
from typing import List
from config.settings import SCRAPER_STRATEGY, GOOGLE_SHEET_ID, META_ACCESS_TOKEN
from scraper.instagram_scraper import InstagramScraper
from transformer.processor import process_record
from transformer.validator import validate_record
from utils.logger import get_logger

# Lazy import SpreadsheetService so missing Google packages do not crash dashboard startup
try:
    from services.spreadsheet_service import SpreadsheetService
    HAS_SPREADSHEET_SERVICE = True
except Exception as e:
    SpreadsheetService = None
    HAS_SPREADSHEET_SERVICE = False
    spreadsheet_import_error = e

logger = get_logger()

# Check optional scraping dependencies via scraper module flags (non-fatal)
try:
    import scraper.instagram_scraper as _insta_mod
    HAS_INSTALOADER = getattr(_insta_mod, "HAS_INSTALOADER", False)
    HAS_PLAYWRIGHT = getattr(_insta_mod, "HAS_PLAYWRIGHT", False)
    HAS_BS4 = getattr(_insta_mod, "HAS_BS4", False)
except Exception:
    HAS_INSTALOADER = False
    HAS_PLAYWRIGHT = False
    HAS_BS4 = False

# Show friendly warnings for missing optional deps (do not crash app)
missing = []
if not HAS_INSTALOADER:
    missing.append("instaloader")
if not HAS_PLAYWRIGHT:
    missing.append("playwright")
if not HAS_BS4:
    missing.append("beautifulsoup4")

if missing:
    msg = (
        "Beberapa modul optional tidak ditemukan: " + ", ".join(missing) +
        ".\nScraping akan mencoba fallback, tetapi untuk fungsionalitas penuh, install modul-modul ini."
    )
    logger.warning(msg)
    st.warning(msg)

if not HAS_SPREADSHEET_SERVICE:
    spreadsheet_msg = (
        "Google Sheets upload tidak tersedia karena modul Sheets tidak terinstal atau konfigurasi gagal. "
        "Pastikan 'gspread' dan 'google-auth' terinstal dan .env dikonfigurasi dengan benar."
    )
    logger.warning(spreadsheet_msg)
    st.warning(spreadsheet_msg)


def parse_urls(input_text: str) -> List[str]:
    """
    Parse and validate Instagram URLs from input text.
    Splits by comma, newline, and whitespace.
    Deduplicates while preserving order.
    """
    if not input_text.strip():
        return []
    
    # Split by comma, newline, and multiple whitespace
    urls = re.split(r'[,\n\s]+', input_text.strip())
    
    # Filter valid Instagram URLs and deduplicate
    valid_urls = []
    seen = set()
    for url in urls:
        url = url.strip()
        if url.startswith("https://www.instagram.com/") and url not in seen:
            valid_urls.append(url)
            seen.add(url)
    
    return valid_urls


def calculate_metrics(results: List[dict]) -> dict:
    """Calculate summary metrics from results."""
    total_likes = sum([r.get("likes", 0) if isinstance(r.get("likes"), int) else 0 for r in results])
    total_comments = sum([r.get("comments", 0) if isinstance(r.get("comments"), int) else 0 for r in results])
    total_views = sum([r.get("views", 0) if isinstance(r.get("views"), int) else 0 for r in results])
    
    return {
        "total_urls": len(results),
        "total_likes": total_likes,
        "total_comments": total_comments,
        "total_views": total_views,
    }


# ============================================================================
# MAIN APP
# ============================================================================

# Page title
st.title("📊 Instagram Engagement Report")
st.info("🎬 Reel: instaloader | 🖼️ Post: Meta API")

# ============================================================================
# SECTION 1: URL INPUT AREA
# ============================================================================

st.header("📥 Input URL Instagram")

url_input = st.text_area(
    "Masukkan URL Instagram (pisahkan dengan koma, spasi, atau baris baru)",
    height=160,
    placeholder="https://www.instagram.com/p/ABC123/\nhttps://www.instagram.com/reel/XYZ789/"
)

# Parse URLs
parsed_urls = parse_urls(url_input)
st.caption(f"✅ {len(parsed_urls)} URL valid ditemukan")

# Input buttons
col1, col2 = st.columns([2, 1])

with col1:
    scrape_clicked = st.button("🚀 Mulai Scraping", use_container_width=True, type="primary")

with col2:
    reset_clicked = st.button("🗑️ Reset", use_container_width=True)

# Reset button logic
if reset_clicked:
    for key in ["has_results", "results", "invalid", "appended_count"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

# ============================================================================
# SECTION 2: PROGRESS & STATUS (shown only while scraping)
# ============================================================================

if scrape_clicked and len(parsed_urls) > 0:
    try:
        st.info("⏳ Memulai proses scraping...")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        scraper = InstagramScraper(strategy=SCRAPER_STRATEGY)
        raw_records = []

        reel_urls = [url for url in parsed_urls if "/reel/" in url.lower()]
        post_urls = [url for url in parsed_urls if "/p/" in url.lower()]
        total_urls = len(reel_urls) + len(post_urls)

        has_meta = bool(META_ACCESS_TOKEN)

        status_text.info("🎬 Scraping Reels with instaloader...")
        for idx, url in enumerate(reel_urls):
            record = scraper._scrape_one(url)
            raw_records.append(record)
            progress_bar.progress((idx + 1) / max(1, total_urls))

        status_text.info("🖼️ Scraping Posts with Meta API...")
        for idx, url in enumerate(post_urls):
            record = scraper._scrape_one(url)
            raw_records.append(record)
            progress_bar.progress((len(reel_urls) + idx + 1) / max(1, total_urls))

        processed = [process_record(r) for r in raw_records]
        
        valid_records = []
        invalid_records = []
        for record in processed:
            ok, reason = validate_record(record)
            if ok:
                valid_records.append(record)
            else:
                invalid_records.append({"url": record.get("url"), "reason": reason})
        
        # Do not upload to Google Sheets automatically. Wait for user confirmation first.
        st.session_state["results"] = valid_records
        st.session_state["invalid"] = invalid_records
        st.session_state["appended_count"] = 0
        st.session_state["has_results"] = True
        
        st.success(f"✅ Scraping selesai! {len(valid_records)} data berhasil diproses.")
    except ImportError as e:
        logger.exception(e)
        st.error("❌ Modul scraper tidak ditemukan. Pastikan semua file project ada.")
        st.exception(e)
    except Exception as e:
        logger.exception(e)
        st.error(f"❌ Error: {str(e)}")
        st.exception(e)

# ============================================================================
# SECTION 3: RESULTS TABLE (shown only if has results)
# ============================================================================

if st.session_state["has_results"] and len(st.session_state["results"]) > 0:
    st.divider()
    st.header("📊 Hasil Engagement")
    
    results = st.session_state["results"]
    metrics = calculate_metrics(results)
    
    # Show metrics in 5 columns
    metric_cols = st.columns(5)
    
    with metric_cols[0]:
        st.metric("Total URL Diproses", metrics["total_urls"])
    
    with metric_cols[1]:
        st.metric("Total Likes", f"{metrics['total_likes']:,}")
    
    with metric_cols[2]:
        st.metric("Total Comments", f"{metrics['total_comments']:,}")
    
    with metric_cols[3]:
        st.metric("Total Views", f"{metrics['total_views']:,}")
    
    with metric_cols[4]:
        st.metric("Baris Baru di Sheets", st.session_state["appended_count"])
    
    # Display results table
    df = pd.DataFrame(results)
    # Defensive logging to help debug missing columns (helps reproduce KeyError)
    logger.info("Result DataFrame columns (initial): %s", df.columns.tolist())
    try:
        st.caption(f"Columns found: {df.columns.tolist()}")
    except Exception:
        # In case Streamlit can't render caption in some environments, continue silently
        logger.debug("Unable to render columns caption in Streamlit UI.")
    # Sort results oldest -> newest by post_date (if available)
    if "post_date" in df.columns:
        try:
            df["_post_dt"] = pd.to_datetime(df["post_date"], errors="coerce")
            df = df.sort_values(by="_post_dt", ascending=True).reset_index(drop=True)
            df.drop(columns=["_post_dt"], inplace=True)
        except Exception:
            pass
    df["content_type"] = df["content_type"].map(
        {
            "Reel": "🎬 Reel",
            "Post": "🖼️ Post",
            "Carousel": "🎠 Carousel",
        }
    ).fillna(df["content_type"])

    df = df.rename(columns={
        "url": "Link IG",
        "post_date": "Tanggal yang post date",
        "caption": "Judul Konten",
        "content_type": "Content Type",
        "username": "Username",
        "collab_status": "Collab Status",
        "views": "Views",
        "likes": "Likes",
        "comments": "Comment",
        "shares": "Share",
        "reposts": "Repost",
        "saves": "Save",
        "reach_display": "Reach",
    })
    # Ensure Reach column exists — fallback to other names or create placeholder
    if "Reach" not in df.columns:
        if "reach_display" in df.columns:
            df = df.rename(columns={"reach_display": "Reach"})
            logger.info("Renamed 'reach_display' -> 'Reach'")
        elif "reach" in df.columns:
            df = df.rename(columns={"reach": "Reach"})
            logger.info("Renamed 'reach' -> 'Reach'")
        else:
            df["Reach"] = "N/A"
            logger.info("Added placeholder 'Reach' column with 'N/A' values")

    if "Collab Status" not in df.columns:
        df["Collab Status"] = "belum collab"

    # Defensive: ensure all expected columns exist before attempting selection
    expected_columns = [
        "No", "Bulan", "Tanggal yang post date", "Judul Konten", "Content Type",
        "Username", "Link IG", "Reach", "Views", "Likes", "Comment", "Share",
        "Repost", "Save", "Collab Status"
    ]
    for col in expected_columns:
        if col not in df.columns:
            df[col] = "" if col in ["No", "Bulan"] else "N/A"
    logger.info("Result DataFrame columns (final): %s", df.columns.tolist())

    def _extract_month(date_value: str) -> str:
        if not date_value or date_value == "N/A":
            return ""
        try:
            parsed = pd.to_datetime(date_value, errors="coerce")
            if pd.isna(parsed):
                return ""
            month_name = parsed.strftime("%m")
            return {
                "01": "Januari",
                "02": "Februari",
                "03": "Maret",
                "04": "April",
                "05": "Mei",
                "06": "Juni",
                "07": "Juli",
                "08": "Agustus",
                "09": "September",
                "10": "Oktober",
                "11": "November",
                "12": "Desember",
            }.get(month_name, "")
        except Exception:
            return ""

    df["Bulan"] = df["Tanggal yang post date"].apply(_extract_month)
    df.insert(0, "No", range(1, len(df) + 1))
    df = df[[
        "No", "Bulan", "Tanggal yang post date", "Judul Konten", "Content Type", "Username", "Link IG",
        "Reach", "Views", "Likes", "Comment", "Share", "Repost", "Save", "Collab Status"
    ]]

    # Display an informational banner for result types
    if META_ACCESS_TOKEN:
        st.success("✅ Meta API aktif — Likes, Comments, Views, Saves, Shares tersedia!")
    else:
        st.info("ℹ️ Meta API tidak aktif. Data diambil dari fallback scraper jika tersedia.")

    # Display dataframe with column config
    st.dataframe(
        df,
        use_container_width=True,
        height=400,
        column_config={
            "Link IG": st.column_config.LinkColumn("Link IG", display_text="🔗 Buka"),
            "Views": st.column_config.NumberColumn("Views", format="%d"),
            "Likes": st.column_config.NumberColumn("Likes", format="%d"),
            "Comment": st.column_config.NumberColumn("Comment", format="%d"),
            "Share": st.column_config.NumberColumn("Share", format="%d"),
            "Repost": st.column_config.NumberColumn("Repost", format="%d"),
            "Save": st.column_config.NumberColumn("Save", format="%d"),
            "Reach": st.column_config.TextColumn("Reach"),
        }
    )

    if HAS_SPREADSHEET_SERVICE:
        st.info("Tekan tombol di bawah untuk mengonfirmasi penyalinan hasil scraping ke Google Sheets.")
        if st.button("✅ Konfirmasi Salin ke Google Sheets", type="primary"):
            try:
                service = SpreadsheetService()
                service.ensure_header()
                # Ensure rows are appended in oldest->newest order
                try:
                    sorted_records = sorted(
                        st.session_state["results"],
                        key=lambda r: pd.to_datetime(r.get("post_date"), errors="coerce")
                    )
                except Exception:
                    sorted_records = st.session_state["results"]
                appended = service.append_rows(sorted_records)
                st.session_state["appended_count"] = appended
                if appended > 0:
                    st.success(f"✅ Berhasil menambahkan {appended} baris ke Google Sheets.")
                else:
                    st.info("Tidak ada baris baru untuk ditambahkan ke Google Sheets.")
            except Exception as e:
                logger.exception(e)
                st.warning(
                    "⚠️ Upload ke Google Sheets gagal. Data tetap ditampilkan, tetapi tidak disimpan ke Sheets. "
                    "Periksa konfigurasi kredensial atau akses sheet."
                )
                st.error(f"Google Sheets error: {str(e)}")
    else:
        st.warning("Google Sheets upload tidak tersedia karena SpreadsheetService tidak dapat diinisialisasi.")

    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        # Download CSV button
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download Hasil (CSV)",
            data=csv,
            file_name="engagement_report.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # Open Google Sheets button
        if GOOGLE_SHEET_ID.startswith("https://"):
            sheets_url = GOOGLE_SHEET_ID
        else:
            sheets_url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}"
        
        st.link_button(
            "📄 Lihat Google Sheets",
            url=sheets_url,
            use_container_width=True
        )
    
    # ========================================================================
    # SECTION 5: INVALID RECORDS (shown if any failed)
    # ========================================================================
    
    if st.session_state["invalid"] and len(st.session_state["invalid"]) > 0:
        st.divider()
        with st.expander(f"⚠️ URL yang gagal diproses ({len(st.session_state['invalid'])} URL)"):
            invalid_df = pd.DataFrame(st.session_state["invalid"])
            st.dataframe(invalid_df, use_container_width=True)

# ============================================================================
# SECTION 6: FOOTER
# ============================================================================

st.divider()
st.markdown(
    "<p style='text-align: center; color: gray; font-size: 0.9em;'>"
    "Instagram Engagement Scraper • Built with Streamlit"
    "</p>",
    unsafe_allow_html=True
)
