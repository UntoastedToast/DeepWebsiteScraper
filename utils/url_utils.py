from urllib.parse import urlparse, urlunparse

def normalize_url(url: str) -> str:
    """
    Normalizes the URL by adding protocol if missing and removing trailing slashes.
    """
    # Add https:// prefix if not present
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip('/')
    if not path:
        path = '/'
    normalized = urlunparse((scheme, netloc, path, '', '', ''))
    return normalized

def is_valid_url(url: str, base_domain: str, banned_extensions: set) -> bool:
    """
    Checks if a URL is valid based on domain and file extension.
    """
    parsed = urlparse(url)
    path = parsed.path.lower()
    
    # Check domain and protocol
    if parsed.netloc != base_domain or parsed.scheme not in ['http', 'https']:
        return False
        
    # Check file extension
    if any(path.endswith(ext) for ext in banned_extensions):
        return False
        
    return True
