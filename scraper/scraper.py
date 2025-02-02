import sys
import signal
import threading
import logging
import time
from queue import Queue, Empty
from urllib.parse import urljoin, urlparse
import urllib.robotparser

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils.url_utils import normalize_url, is_valid_url
from utils.html_utils import clean_html, extract_text_with_context

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)

class DeepSiteScraper:
    """
    Deep search scraper that recursively visits pages starting from a start URL and searches for a
    given search term. Only pages from the same domain are visited.
    """
    def __init__(self, base_url: str, search_term: str,
                 max_pages: int = 50, thread_count: int = 10,
                 timeout: int = 8, request_delay: float = 0.2, snippet_radius: int = 50):
        """
        Initializes the scraper with configuration parameters.
        """
        self.base_url = normalize_url(base_url)
        self.domain = urlparse(self.base_url).netloc
        self.search_term = search_term.lower()
        self.found = {}      # Mapping: URL -> List of snippets
        self.visited = set() # Set of already visited (normalized) URLs
        self.lock = threading.Lock()
        self.queue = Queue()
        self.queue.put(self.base_url)
        self.running = True

        # Configuration parameters
        self.timeout = timeout
        self.max_pages = max_pages
        self.thread_count = thread_count
        self.request_delay = request_delay
        self.snippet_radius = snippet_radius

        self.banned_extensions = {
            '.png', '.jpg', '.jpeg', '.gif', '.pdf', '.doc', '.docx',
            '.xls', '.xlsx', '.ppt', '.pptx', '.mp3', '.mp4', '.zip',
            '.tar', '.gz', '.exe', '.svg', '.css', '.js', '.ico', '.webp'
        }

        self._setup_session()
        self._setup_robots_txt()
        signal.signal(signal.SIGINT, self._exit_gracefully)

    def _setup_session(self):
        """
        Configures the requests session with retry strategy.
        """
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.1,
                       status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        self.session.headers = {'User-Agent': 'Mozilla/5.0'}

    def _setup_robots_txt(self):
        """
        Sets up and fetches robots.txt for the domain.
        """
        self.robot_parser = urllib.robotparser.RobotFileParser()
        robots_url = urljoin(self.base_url, '/robots.txt')
        try:
            self.robot_parser.set_url(robots_url)
            self.robot_parser.read()
            logging.info(f"Robots.txt fetched from {robots_url}")
        except Exception as e:
            logging.warning(f"Could not fetch robots.txt from {robots_url}: {e}")

    def _exit_gracefully(self, signum, frame):
        """
        Signal handler for clean shutdown.
        """
        logging.warning("🛑 Aborting deep scan...")
        self.running = False

    def _can_fetch(self, url: str) -> bool:
        """
        Checks if URL is allowed by robots.txt
        """
        if not self.robot_parser.can_fetch(self.session.headers['User-Agent'], url):
            logging.info(f"⏩ Skipping disallowed by robots.txt: {url}")
            return False
        return True

    def _fetch(self, url: str) -> str:
        """
        Downloads the HTML page if the content type is HTML.
        """
        try:
            time.sleep(self.request_delay)  # Rate Limiting
            response = self.session.get(url, stream=True, timeout=self.timeout)
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text/html' not in content_type:
                logging.info(f"⏩ Skipping non-HTML content: {url}")
                return ''
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logging.error(f"⚠️ Request error at {url}: {e}")
        except Exception as e:
            logging.error(f"⚠️ Error at {url}: {e}", exc_info=True)
        return ''

    def _extract_links(self, html: str, base_url: str) -> set:
        """
        Extracts all valid links from the HTML and normalizes them.
        """
        soup = BeautifulSoup(html, 'lxml')
        links = set()
        for anchor in soup.find_all('a', href=True):
            raw_url = urljoin(base_url, anchor['href']).split('#')[0]
            if is_valid_url(raw_url, self.domain, self.banned_extensions) and self._can_fetch(raw_url):
                normalized_url = normalize_url(raw_url)
                links.add(normalized_url)
        return links

    def _worker(self):
        """
        Worker thread that processes URLs, downloads content and adds new links to the queue.
        """
        while self.running:
            try:
                current_url = self.queue.get(timeout=2)
            except Empty:
                break

            if current_url is None:
                self.queue.task_done()
                break

            normalized_url = normalize_url(current_url)
            with self.lock:
                if normalized_url in self.visited or len(self.visited) >= self.max_pages:
                    self.queue.task_done()
                    continue
                self.visited.add(normalized_url)

            logging.info(f"🌐 Scanning page {len(self.visited)}/{self.max_pages}: {normalized_url}")
            html = self._fetch(normalized_url)
            if html:
                text = clean_html(html)
                if self.search_term in text.lower():
                    snippets = extract_text_with_context(text, self.search_term, self.snippet_radius)
                    with self.lock:
                        self.found[normalized_url] = snippets
                    logging.info(f"🎯 Match found on: {normalized_url}")
                    if snippets:
                        logging.info(f"    Snippet: ...{snippets[0]}...")

                if len(self.visited) < self.max_pages:
                    new_links = self._extract_links(html, normalized_url)
                    with self.lock:
                        for link in new_links:
                            if link not in self.visited:
                                self.queue.put(link)
            self.queue.task_done()

    def crawl(self):
        """
        Starts the crawl process and outputs a summary of results.
        """
        logging.info(f"\n🔍 Starting deep scan for '{self.search_term}' on {self.domain}")
        threads = []
        for _ in range(self.thread_count):
            t = threading.Thread(target=self._worker, daemon=True)
            t.start()
            threads.append(t)
        try:
            self.queue.join()
        except KeyboardInterrupt:
            self._exit_gracefully(None, None)
        finally:
            self.running = False
            for _ in range(self.thread_count):
                self.queue.put(None)
            for t in threads:
                t.join()

        self._print_results()

    def _print_results(self):
        """
        Prints the final results of the crawl.
        """
        logging.info("\n📊 Final results:")
        logging.info(f"Search term: '{self.search_term}'")
        logging.info(f"Scanned: {len(self.visited)} pages")
        if self.found:
            for url, snippets in self.found.items():
                logging.info(f"  → {url}")
                for snippet in snippets:
                    logging.info(f"     ...{snippet}...")
        else:
            logging.info("❌ No matches found.")
