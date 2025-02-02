import re
from bs4 import BeautifulSoup

def clean_html(html: str) -> str:
    """
    Removes script, style, and other unnecessary tags from HTML content.
    Returns cleaned text content.
    """
    soup = BeautifulSoup(html, 'lxml')
    # Remove unnecessary tags
    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'meta', 'link']):
        tag.decompose()
    return soup.get_text(separator=' ', strip=True)

def extract_text_with_context(text: str, search_term: str, radius: int = 50) -> list:
    """
    Extracts snippets of text containing the search term with surrounding context.
    Returns a list of highlighted snippets.
    """
    snippets = []
    text_lower = text.lower()
    highlight = "\033[93m"  # ANSI yellow
    reset = "\033[0m"      # ANSI reset
    
    for match in re.finditer(re.escape(search_term.lower()), text_lower):
        start = max(match.start() - radius, 0)
        end = min(match.end() + radius, len(text))
        snippet = text[start:end]
        # Highlight the search term
        snippet_highlighted = re.sub(
            f"({re.escape(search_term)})",
            highlight + r"\1" + reset,
            snippet,
            flags=re.IGNORECASE
        )
        snippets.append(snippet_highlighted)
    return snippets
