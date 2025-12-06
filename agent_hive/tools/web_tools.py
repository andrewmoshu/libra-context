"""Web-related tools for Agent Hive drones."""

from typing import Optional, Dict, Any, List
import json
import logging
import re

logger = logging.getLogger(__name__)

# Lazy imports for optional dependencies
_httpx = None
_bs4 = None


def _get_httpx():
    """Lazy load httpx."""
    global _httpx
    if _httpx is None:
        try:
            import httpx
            _httpx = httpx
        except ImportError:
            raise ImportError("httpx is required for web tools. Install with: pip install httpx")
    return _httpx


def _get_beautifulsoup():
    """Lazy load BeautifulSoup."""
    global _bs4
    if _bs4 is None:
        try:
            from bs4 import BeautifulSoup
            _bs4 = BeautifulSoup
        except ImportError:
            raise ImportError("beautifulsoup4 is required for web tools. Install with: pip install beautifulsoup4")
    return _bs4


def web_search(
    query: str,
    num_results: int = 5,
    search_type: str = "general",
) -> Dict[str, Any]:
    """
    Search the web for information.

    This is a placeholder that integrates with Google ADK's google_search tool.
    When used with Google ADK Agent, the agent's native google_search capability
    should be preferred.

    Args:
        query: Search query string
        num_results: Number of results to return (default: 5)
        search_type: Type of search - "general", "news", "images", "scholar"

    Returns:
        Dict containing search results with titles, urls, and snippets
    """
    # Note: Actual search should use Google ADK's google_search tool
    # This function serves as a wrapper/fallback for testing
    return {
        "status": "pending",
        "query": query,
        "search_type": search_type,
        "num_results": num_results,
        "message": "Use Google ADK's google_search tool for actual searches",
        "results": [],
    }


def fetch_url(
    url: str,
    extract_text: bool = True,
    extract_links: bool = False,
    max_length: int = 10000,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """
    Fetch and parse content from a URL.

    Args:
        url: URL to fetch
        extract_text: Whether to extract main text content
        extract_links: Whether to extract links from the page
        max_length: Maximum content length to return
        timeout: Request timeout in seconds

    Returns:
        Dict containing fetched content, status, and metadata
    """
    httpx = _get_httpx()
    BeautifulSoup = _get_beautifulsoup()

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; AgentHive/1.0; +https://github.com/agent-hive)"
        }

        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        html_content = response.text

        # Parse HTML
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract metadata
        title = ""
        if soup.title:
            title = soup.title.string or ""

        description = ""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            description = meta_desc.get("content", "")

        # Extract text content if requested
        text_content = ""
        if extract_text:
            # Remove script and style elements
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()

            # Get text
            text_content = soup.get_text(separator="\n", strip=True)

            # Clean up whitespace
            text_content = re.sub(r"\n\s*\n", "\n\n", text_content)
            text_content = text_content[:max_length]

        # Extract links if requested
        links = []
        if extract_links:
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                link_text = link.get_text(strip=True)
                if href and not href.startswith("#"):
                    links.append({"url": href, "text": link_text[:100]})
            links = links[:50]  # Limit number of links

        return {
            "status": "success",
            "url": url,
            "content": text_content,
            "links": links if extract_links else None,
            "metadata": {
                "title": title,
                "description": description,
                "content_type": content_type,
                "content_length": len(text_content),
            },
        }

    except Exception as e:
        logger.error(f"Failed to fetch URL {url}: {e}")
        return {
            "status": "error",
            "url": url,
            "error": str(e),
            "content": "",
            "links": None,
            "metadata": {},
        }


def analyze_website(
    url: str,
    analysis_type: str = "overview",
) -> Dict[str, Any]:
    """
    Analyze a website for business intelligence.

    Args:
        url: Website URL to analyze
        analysis_type: Type of analysis - "overview", "competitors", "seo", "technology"

    Returns:
        Dict containing analysis results
    """
    BeautifulSoup = _get_beautifulsoup()

    # First fetch the URL
    fetch_result = fetch_url(url, extract_text=True, extract_links=True)

    if fetch_result["status"] != "success":
        return {
            "status": "error",
            "url": url,
            "analysis_type": analysis_type,
            "error": fetch_result.get("error", "Failed to fetch URL"),
            "findings": {},
            "recommendations": [],
        }

    findings = {
        "title": fetch_result["metadata"].get("title", ""),
        "description": fetch_result["metadata"].get("description", ""),
        "content_length": fetch_result["metadata"].get("content_length", 0),
    }

    recommendations = []

    if analysis_type == "overview":
        # Basic overview analysis
        content = fetch_result.get("content", "")
        findings["word_count"] = len(content.split())
        findings["has_links"] = bool(fetch_result.get("links"))
        findings["link_count"] = len(fetch_result.get("links", []))

        if not fetch_result["metadata"].get("description"):
            recommendations.append("Add a meta description for better SEO")
        if findings["word_count"] < 300:
            recommendations.append("Consider adding more content for better engagement")

    elif analysis_type == "seo":
        # SEO-focused analysis
        content = fetch_result.get("content", "").lower()
        findings["has_description"] = bool(fetch_result["metadata"].get("description"))
        findings["title_length"] = len(fetch_result["metadata"].get("title", ""))

        if findings["title_length"] > 60:
            recommendations.append("Title may be too long for search results (60 chars recommended)")
        if not findings["has_description"]:
            recommendations.append("Missing meta description - important for SEO")

    elif analysis_type == "technology":
        # Technology detection (basic)
        content = fetch_result.get("content", "").lower()
        technologies_detected = []

        tech_markers = {
            "react": ["react", "reactjs", "__NEXT_DATA__"],
            "vue": ["vue", "vuejs"],
            "angular": ["angular", "ng-"],
            "wordpress": ["wp-content", "wordpress"],
            "shopify": ["shopify", "cdn.shopify"],
        }

        for tech, markers in tech_markers.items():
            if any(marker in content for marker in markers):
                technologies_detected.append(tech)

        findings["technologies_detected"] = technologies_detected

    return {
        "status": "success",
        "url": url,
        "analysis_type": analysis_type,
        "findings": findings,
        "recommendations": recommendations,
    }


def monitor_trends(
    keywords: List[str],
    timeframe: str = "7d",
    region: str = "US",
) -> Dict[str, Any]:
    """
    Monitor trends for given keywords.

    Note: This is a placeholder for trend monitoring functionality.
    In production, this would integrate with:
    - Google Trends API
    - Social media APIs
    - News aggregation services

    Args:
        keywords: List of keywords to track
        timeframe: Time range - "24h", "7d", "30d", "90d", "12m"
        region: Geographic region code

    Returns:
        Dict containing trend data and insights
    """
    # Validate inputs
    if not keywords:
        return {
            "status": "error",
            "error": "No keywords provided",
            "keywords": [],
            "timeframe": timeframe,
            "region": region,
            "trends": {},
            "insights": [],
        }

    # This is a placeholder that would integrate with real trend APIs
    return {
        "status": "pending",
        "keywords": keywords,
        "timeframe": timeframe,
        "region": region,
        "trends": {
            keyword: {
                "status": "pending",
                "message": "Trend data requires API integration"
            }
            for keyword in keywords
        },
        "insights": [
            "Trend monitoring requires Google Trends or similar API integration",
            f"Tracking {len(keywords)} keywords for {timeframe} in {region}",
        ],
    }


def extract_contact_info(url: str) -> Dict[str, Any]:
    """
    Extract contact information from a website.

    Args:
        url: URL to extract contact info from

    Returns:
        Dict containing found contact information
    """
    fetch_result = fetch_url(url, extract_text=True)

    if fetch_result["status"] != "success":
        return {
            "status": "error",
            "url": url,
            "error": fetch_result.get("error"),
            "contacts": {},
        }

    content = fetch_result.get("content", "")

    # Extract email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = list(set(re.findall(email_pattern, content)))[:10]

    # Extract phone numbers (basic US format)
    phone_pattern = r'[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}'
    phones = list(set(re.findall(phone_pattern, content)))[:10]

    return {
        "status": "success",
        "url": url,
        "contacts": {
            "emails": emails,
            "phones": phones,
        },
        "metadata": fetch_result.get("metadata", {}),
    }


def compare_websites(
    urls: List[str],
    aspects: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Compare multiple websites.

    Args:
        urls: List of URLs to compare
        aspects: Aspects to compare (default: all)

    Returns:
        Dict containing comparison results
    """
    if not urls or len(urls) < 2:
        return {
            "status": "error",
            "error": "At least 2 URLs required for comparison",
            "urls": urls,
            "comparison": {},
        }

    aspects = aspects or ["content_length", "title", "description", "links"]

    comparison = {}
    for url in urls[:5]:  # Limit to 5 URLs
        analysis = analyze_website(url, "overview")
        if analysis["status"] == "success":
            comparison[url] = analysis["findings"]
        else:
            comparison[url] = {"error": analysis.get("error", "Failed to analyze")}

    return {
        "status": "success",
        "urls": urls,
        "aspects": aspects,
        "comparison": comparison,
        "summary": f"Compared {len(comparison)} websites",
    }
