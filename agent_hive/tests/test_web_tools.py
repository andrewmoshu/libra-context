"""Tests for web tools."""

import unittest
from unittest.mock import patch, MagicMock
from agent_hive.tools.web_tools import (
    web_search,
    fetch_url,
    analyze_website,
    monitor_trends,
    extract_contact_info,
    compare_websites,
)


class TestWebSearch(unittest.TestCase):
    """Tests for web_search function."""

    def test_web_search_returns_dict(self):
        """Test that web_search returns a dictionary."""
        result = web_search("test query")
        self.assertIsInstance(result, dict)
        self.assertEqual(result["query"], "test query")
        self.assertEqual(result["status"], "pending")

    def test_web_search_with_params(self):
        """Test web_search with custom parameters."""
        result = web_search("test", num_results=10, search_type="news")
        self.assertEqual(result["num_results"], 10)
        self.assertEqual(result["search_type"], "news")


class TestFetchUrl(unittest.TestCase):
    """Tests for fetch_url function."""

    @patch('agent_hive.tools.web_tools._get_httpx')
    @patch('agent_hive.tools.web_tools._get_beautifulsoup')
    def test_fetch_url_success(self, mock_bs4, mock_httpx):
        """Test successful URL fetch."""
        # Setup mocks
        mock_response = MagicMock()
        mock_response.text = "<html><head><title>Test Page</title></head><body>Test content</body></html>"
        mock_response.headers = {"content-type": "text/html"}

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)
        mock_client.get.return_value = mock_response

        mock_httpx_module = MagicMock()
        mock_httpx_module.Client.return_value = mock_client
        mock_httpx.return_value = mock_httpx_module

        # Use real BeautifulSoup
        from bs4 import BeautifulSoup
        mock_bs4.return_value = BeautifulSoup

        result = fetch_url("https://example.com")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["url"], "https://example.com")
        self.assertIn("metadata", result)

    def test_fetch_url_error_handling(self):
        """Test that fetch_url handles errors gracefully."""
        # Use an invalid URL that will fail
        with patch('agent_hive.tools.web_tools._get_httpx') as mock_httpx:
            mock_httpx.side_effect = ImportError("httpx not installed")

            with self.assertRaises(ImportError):
                fetch_url("https://example.com")


class TestAnalyzeWebsite(unittest.TestCase):
    """Tests for analyze_website function."""

    @patch('agent_hive.tools.web_tools.fetch_url')
    def test_analyze_website_overview(self, mock_fetch):
        """Test website overview analysis."""
        mock_fetch.return_value = {
            "status": "success",
            "content": "This is test content " * 100,
            "links": [{"url": "http://example.com", "text": "link"}],
            "metadata": {
                "title": "Test Site",
                "description": "A test description",
                "content_length": 1000,
            },
        }

        result = analyze_website("https://example.com", "overview")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["analysis_type"], "overview")
        self.assertIn("findings", result)
        self.assertIn("word_count", result["findings"])

    @patch('agent_hive.tools.web_tools.fetch_url')
    def test_analyze_website_error(self, mock_fetch):
        """Test website analysis when fetch fails."""
        mock_fetch.return_value = {
            "status": "error",
            "error": "Connection failed",
        }

        result = analyze_website("https://example.com")

        self.assertEqual(result["status"], "error")
        self.assertIn("error", result)


class TestMonitorTrends(unittest.TestCase):
    """Tests for monitor_trends function."""

    def test_monitor_trends_with_keywords(self):
        """Test trend monitoring with valid keywords."""
        result = monitor_trends(["ai", "machine learning"], "7d", "US")

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["keywords"], ["ai", "machine learning"])
        self.assertEqual(result["timeframe"], "7d")
        self.assertEqual(result["region"], "US")

    def test_monitor_trends_empty_keywords(self):
        """Test trend monitoring with empty keywords."""
        result = monitor_trends([])

        self.assertEqual(result["status"], "error")
        self.assertIn("error", result)


class TestExtractContactInfo(unittest.TestCase):
    """Tests for extract_contact_info function."""

    @patch('agent_hive.tools.web_tools.fetch_url')
    def test_extract_emails(self, mock_fetch):
        """Test email extraction from page content."""
        mock_fetch.return_value = {
            "status": "success",
            "content": "Contact us at test@example.com or sales@example.com",
            "metadata": {"title": "Contact"},
        }

        result = extract_contact_info("https://example.com/contact")

        self.assertEqual(result["status"], "success")
        self.assertIn("emails", result["contacts"])
        self.assertIn("test@example.com", result["contacts"]["emails"])

    @patch('agent_hive.tools.web_tools.fetch_url')
    def test_extract_phones(self, mock_fetch):
        """Test phone number extraction."""
        mock_fetch.return_value = {
            "status": "success",
            "content": "Call us at 555-123-4567 or 1-800-555-0123",
            "metadata": {"title": "Contact"},
        }

        result = extract_contact_info("https://example.com/contact")

        self.assertEqual(result["status"], "success")
        self.assertIn("phones", result["contacts"])


class TestCompareWebsites(unittest.TestCase):
    """Tests for compare_websites function."""

    def test_compare_websites_minimum_urls(self):
        """Test that compare requires at least 2 URLs."""
        result = compare_websites(["https://example.com"])

        self.assertEqual(result["status"], "error")
        self.assertIn("At least 2 URLs", result["error"])

    @patch('agent_hive.tools.web_tools.analyze_website')
    def test_compare_websites_success(self, mock_analyze):
        """Test successful website comparison."""
        mock_analyze.return_value = {
            "status": "success",
            "findings": {
                "title": "Test",
                "content_length": 1000,
            },
        }

        result = compare_websites([
            "https://example1.com",
            "https://example2.com",
        ])

        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["comparison"]), 2)


if __name__ == "__main__":
    unittest.main()
