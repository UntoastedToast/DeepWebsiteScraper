import sys
import signal
import threading
import logging
from queue import Queue, Empty
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Logging configuration
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

    def __init__(self, base_url: str, search_term: str):
        """
        Initializes the scraper with start URL and search term.
        """
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.search_term = search_term.lower()
        self.found = set()   # Pages where the search term was found
        self.visited = set()  # Already visited pages
        self.lock = threading.Lock()
        self.queue = Queue()
        self.queue.put(base_url)
        self.running = True

        # Configuration
        self.timeout = 8
        self.max_pages = 500
        self.thread_count = 20
        self.banned_extensions = {
            '.png', '.jpg', '.jpeg', '.gif', '.pdf', '.doc', '.docx',
            '.xls', '.xlsx', '.ppt', '.pptx', '.mp3', '.mp4', '.zip',
            '.tar', '.gz', '.exe', '.svg', '.css', '.js', '.ico', '.webp'
        }

        # Configure Requests session with retry strategy
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.1,
                        status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)
        self.session.headers = {'User-Agent': 'Mozilla/5.0'}

        # Enable aborting via CTRL+C
        signal.signal(signal.SIGINT, self._exit_gracefully)

    def _exit_gracefully(self, signum, frame):
        """
        Signal handler that cleanly terminates the scraper when aborted (e.g., CTRL+C).
        """
        logging.warning("🛑 Deep scan is being aborted...")
        self.running = False
        sys.exit(0)

    def _is_valid_url(self, url: str) -> bool:
        """
        Checks if the URL is in the same domain, has no unwanted file type,
        and has an HTTP/HTTPS scheme.
        """
        parsed = urlparse(url)
        path = parsed.path.lower()
        return (
            parsed.netloc == self.domain and
            parsed.scheme in ['http', 'https'] and
            not any(path.endswith(ext) for ext in self.banned_extensions)
        )

    def _fetch(self, url: str) -> str:
        """
        Downloads the HTML page from the given URL.
        Skips pages that are not delivered as 'text/html'.
        """
        try:
            with self.session.get(url, stream=True, timeout=self.timeout) as response:
                content_type = response.headers.get('Content-Type', '').lower()
                if 'text/html' not in content_type:
                    logging.info(f"⏩ Skipping non-HTML: {url}")
                    return ''
                response.raise_for_status()
                return response.text
        except Exception as e:
            logging.error(f"⚠️ Error at {url}: {e}")
            return ''

    def _check_content(self, html: str) -> bool:
        """
        Checks if the search term is present in the HTML text (after removing scripts, styles, etc.).
        """
        soup = BeautifulSoup(html, 'lxml')
        # Remove elements that typically don't belong to the main content
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'meta', 'link']):
            element.decompose()
        text = soup.get_text(separator=' ', strip=True).lower()
        return self.search_term in text

    def _extract_links(self, html: str, base_url: str) -> set:
        """
        Extracts all valid links from the HTML and converts relative URLs to absolute ones.
        """
        soup = BeautifulSoup(html, 'lxml')
        links = set()
        for link in soup.find_all('a', href=True):
            absolute_url = urljoin(base_url, link['href']).split('#')[0]
            if self._is_valid_url(absolute_url):
                links.add(absolute_url)
        return links

    def _worker(self):
        """
        Worker thread: Gets URLs from the queue, processes them (download, content check)
        and adds newly found links back to the queue.
        """
        while self.running:
            try:
                current_url = self.queue.get(timeout=2)
            except Empty:
                # No task in queue - terminate
                break

            # Ensure task_done() is always called
            try:
                if current_url is None:
                    break

                with self.lock:
                    if current_url in self.visited or len(self.visited) >= self.max_pages:
                        continue
                    self.visited.add(current_url)

                logging.info(f"🌐 Scanning page {len(self.visited)}/{self.max_pages}: {current_url}")

                html = self._fetch(current_url)
                if html:
                    if self._check_content(html):
                        with self.lock:
                            self.found.add(current_url)
                        logging.info(f"🎯 Match found on: {current_url}")

                    # If max count not reached yet, extract and add links
                    if len(self.visited) < self.max_pages:
                        new_links = self._extract_links(html, current_url)
                        with self.lock:
                            for link in new_links:
                                if link not in self.visited:
                                    self.queue.put(link)
            except Exception as e:
                logging.error(f"⚠️ Unexpected error: {e}", exc_info=True)
            finally:
                self.queue.task_done()

    def crawl(self):
        """
        Starts the crawler: Creates worker threads, waits for the queue to be processed and
        then outputs a summary of the results.
        """
        logging.info(f"\n🔍 Starting deep scan for '{self.search_term}' on {self.domain}")

        threads = []
        for _ in range(self.thread_count):
            t = threading.Thread(target=self._worker)
            t.start()
            threads.append(t)

        try:
            self.queue.join()
        except KeyboardInterrupt:
            self._exit_gracefully(None, None)
        finally:
            self.running = False
            # Send stop indicator (None) for each worker
            for _ in range(self.thread_count):
                self.queue.put(None)
            for t in threads:
                t.join()

        # Output final results
        logging.info("\n📊 Final results:")
        logging.info(f"Search term: '{self.search_term}'")
        logging.info(f"Scanned: {len(self.visited)} pages")
        logging.info(f"Limit: {'Reached' if len(self.visited) >= self.max_pages else 'Not reached'}")

        if self.found:
            logging.info("\n✅ Matches found on the following pages:")
            for result in self.found:
                logging.info(f"  → {result}")
        else:
            logging.info("\n❌ No matches found")


if __name__ == "__main__":
    logging.info("🕸️ Deep Website Scraper")
    logging.info("Press CTRL+C to abort\n")

    try:
        url = input("🌍 Start URL: ").strip()
        term = input("🔎 Search term: ").strip()

        scraper = DeepSiteScraper(url, term)
        scraper.crawl()

    except Exception as e:
        logging.critical(f"❌ Critical error: {e}", exc_info=True)
