"""Tests for SSRF-safe JD scraper."""

import pytest

from app.core.jd_scraper import SSRFProtectionError, extract_jd_from_html, validate_safe_url


def test_ssrf_disallowed_schemes() -> None:
    """Verify non-http/https schemes are blocked."""
    with pytest.raises(SSRFProtectionError, match="Disallowed scheme"):
        validate_safe_url("file:///etc/passwd")

    with pytest.raises(SSRFProtectionError, match="Disallowed scheme"):
        validate_safe_url("ftp://example.com/job.txt")

    with pytest.raises(SSRFProtectionError, match="Disallowed scheme"):
        validate_safe_url("gopher://example.com")


def test_ssrf_loopback_and_private_ips() -> None:
    """Verify loopback and private IP targets are blocked."""
    with pytest.raises(SSRFProtectionError, match="Blocked internal/restricted target IP"):
        validate_safe_url("http://127.0.0.1:8000/job")

    with pytest.raises(SSRFProtectionError, match="Blocked internal/restricted target IP"):
        validate_safe_url("http://10.0.0.5/job")

    with pytest.raises(SSRFProtectionError, match="Blocked internal/restricted target IP"):
        validate_safe_url("http://192.168.1.100/jd")

    with pytest.raises(SSRFProtectionError, match="Blocked internal/restricted target IP"):
        validate_safe_url("http://172.16.0.10/jd")


def test_ssrf_cloud_metadata_blocked() -> None:
    """Verify cloud metadata endpoints are strictly blocked."""
    with pytest.raises(SSRFProtectionError, match="Blocked"):
        validate_safe_url("http://169.254.169.254/latest/meta-data/")

    with pytest.raises(SSRFProtectionError, match="Blocked cloud metadata hostname"):
        validate_safe_url("http://metadata.google.internal/computeMetadata/v1/")


def test_html_extraction_with_selectors() -> None:
    """Verify HTML extractor finds content from known selectors and semantic fallback."""
    # Greenhouse selector test
    html_gh = """
    <html>
      <body>
        <div id="content">
          <h1>Staff Machine Learning Engineer</h1>
          <p>We are seeking an experienced ML Engineer with 5+ years building deep learning
          systems in PyTorch.</p>
        </div>
      </body>
    </html>
    """
    extracted_gh = extract_jd_from_html(html_gh, "greenhouse.io")
    assert "Staff Machine Learning Engineer" in extracted_gh
    assert "PyTorch" in extracted_gh

    # Generic article fallback test
    html_generic = """
    <html>
      <body>
        <nav><a href="/">Home</a></nav>
        <article>
          <h1>Senior Backend Developer</h1>
          <p>Requirements include proficiency in Python, FastAPI, and PostgreSQL.
          Must have experience with distributed microservices.</p>
        </article>
        <footer>Copyright 2026</footer>
      </body>
    </html>
    """
    extracted_gen = extract_jd_from_html(html_generic, "company.com")
    assert "Senior Backend Developer" in extracted_gen
    assert "PostgreSQL" in extracted_gen
    assert "Home" not in extracted_gen
    assert "Copyright" not in extracted_gen
