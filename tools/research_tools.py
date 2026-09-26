import ipaddress
import socket
from urllib.parse import urlparse

from ddgs import DDGS


MAX_WEB_RESULTS = 8
MAX_WEB_CONTENT = 15_000


def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the public web for information.

    Args:
        query: Search query.
        max_results: Number of results to return, from 1 to 8.

    Returns:
        Search results containing titles, URLs, and snippets.
    """

    if not query.strip():
        return "Error: Search query cannot be empty."

    max_results = max(1, min(int(max_results), MAX_WEB_RESULTS))

    try:
        results = DDGS().text(
            query=query,
            region="uk-en",
            safesearch="moderate",
            max_results=max_results,
        )
    except Exception as error:
        return f"Error performing web search: {error}"

    if not results:
        return "No web results found."

    output = []

    for index, result in enumerate(results, start=1):
        title = result.get("title", "Untitled")
        url = result.get("href", "")
        body = result.get("body", "")

        output.append(
            f"[{index}] {title}\n"
            f"URL: {url}\n"
            f"Snippet: {body}"
        )

    return "\n\n".join(output)


def _safe_public_url(url: str) -> bool:
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        return False

    hostname = parsed.hostname

    if not hostname:
        return False

    if hostname.lower() == "localhost":
        return False

    try:
        addresses = socket.getaddrinfo(hostname, None)

        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])

            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
            ):
                return False

    except (socket.gaierror, ValueError):
        return False

    return True


def fetch_webpage(url: str) -> str:
    """
    Fetch and extract readable content from a public webpage.

    Args:
        url: Public HTTP or HTTPS URL.

    Returns:
        Extracted webpage content.
    """

    if not _safe_public_url(url):
        return "Error: URL is not an allowed public HTTP/HTTPS address."

    try:
        result = DDGS().extract(
            url,
            fmt="text_markdown",
        )
    except Exception as error:
        return f"Error fetching webpage: {error}"

    content = str(result.get("content", ""))

    if not content:
        return "Error: No readable webpage content was returned."

    if len(content) > MAX_WEB_CONTENT:
        content = (
            content[:MAX_WEB_CONTENT]
            + "\n\n[Content truncated]"
        )

    return (
        f"Source URL: {url}\n\n"
        f"{content}"
    )