"""SSRF-safe Job Description web scraper."""

import ipaddress
import logging
import re
import socket
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.core.models import JDScrapeResult

logger = logging.getLogger(__name__)

# Known cloud metadata hosts and forbidden IPs
FORBIDDEN_HOSTNAMES = {
    "metadata.google.internal",
    "metadata",
    "instance-data",
}

CLOUD_METADATA_IPS = {
    ipaddress.ip_address("169.254.169.254"),
    ipaddress.ip_address("169.254.170.2"),
}

SITE_SELECTORS = {
    "linkedin.com": "div.description__text",
    "indeed.com": "div#jobDescriptionText",
    "greenhouse.io": "div#content",
    "lever.co": "div.posting-page",
    "workday.com": "div.job-description",
}

DEFAULT_MAX_SIZE = 2 * 1024 * 1024  # 2 MB max body size
DEFAULT_TIMEOUT = 8.0  # seconds


class SSRFProtectionError(ValueError):
    """Raised when a URL attempts to access private or forbidden network targets."""

    pass


def validate_safe_url(url: str) -> None:
    """Validate that the URL is safe and does not target internal or link-local infrastructure."""
    parsed = urlparse(url)

    if parsed.scheme.lower() not in ("http", "https"):
        raise SSRFProtectionError(
            f"Disallowed scheme: '{parsed.scheme}'. Only http/https permitted."
        )

    hostname = parsed.hostname
    if not hostname:
        raise SSRFProtectionError("URL is missing a valid hostname.")

    if hostname.lower() in FORBIDDEN_HOSTNAMES:
        raise SSRFProtectionError(f"Blocked cloud metadata hostname: '{hostname}'.")

    port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)

    try:
        addr_infos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise SSRFProtectionError(f"DNS resolution failed for hostname '{hostname}': {e}") from e

    if not addr_infos:
        raise SSRFProtectionError(f"No IP addresses resolved for hostname '{hostname}'.")

    for addr_info in addr_infos:
        ip_str = addr_info[4][0]
        ip = ipaddress.ip_address(ip_str)

        if (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
            or ip in CLOUD_METADATA_IPS
        ):
            raise SSRFProtectionError(
                f"Blocked internal/restricted target IP: '{ip}' for hostname '{hostname}'."
            )


def extract_jd_from_html(html: str, domain: str) -> str:
    """Extract clean job description text using site-specific selectors or semantic fallbacks."""
    soup = BeautifulSoup(html, "html.parser")

    # Decompose irrelevant navigation and script elements
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "svg"]):
        tag.decompose()

    # Try domain-specific selectors
    for site, selector in SITE_SELECTORS.items():
        if site in domain:
            target = soup.select_one(selector)
            if target:
                text = target.get_text(separator="\n", strip=True)
                if len(text) > 100:
                    return clean_whitespace(text)

    # Heuristic fallback: largest semantic container
    candidates = []
    for tag in soup.find_all(["main", "article", "section", "div"]):
        t = tag.get_text(separator="\n", strip=True)
        if len(t) >= 150:
            candidates.append(t)

    if candidates:
        # Choose the candidate with highest textual content
        best_text = max(candidates, key=len)
        return clean_whitespace(best_text)

    # Final fallback: full body text
    body = soup.find("body")
    fallback_text = body.get_text(separator="\n", strip=True) if body else soup.get_text()
    return clean_whitespace(fallback_text)


def clean_whitespace(text: str) -> str:
    """Consolidate extra blank lines while preserving paragraph boundaries."""
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(lines).strip()


async def scrape_jd(
    url: str,
    timeout: float = DEFAULT_TIMEOUT,
    max_size_bytes: int = DEFAULT_MAX_SIZE,
) -> JDScrapeResult:
    """Safely fetch and parse job description text from external URL."""
    validate_safe_url(url)
    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()

        # Enforce content size cap
        content_bytes = response.content
        if len(content_bytes) > max_size_bytes:
            raise ValueError(
                f"Response body exceeds size cap ({len(content_bytes)} > {max_size_bytes} bytes)."
            )

        html_text = response.text

    clean_text = extract_jd_from_html(html_text, domain)
    word_count = len(clean_text.split())

    return JDScrapeResult(
        url=url,
        domain=domain,
        clean_text=clean_text,
        word_count=word_count,
    )
