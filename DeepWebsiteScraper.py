import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from queue import Queue, Empty
import threading
import signal
import sys
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class DeepSiteScraper:
    def __init__(self, base_url: str, search_term: str):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.search_term = search_term.lower()
        self.found = set()
        self.visited = set()
        self.lock = threading.Lock()
        self.queue = Queue()
        self.queue.put(base_url)
        self.running = True
        self.timeout = 8
        self.max_pages = 500
        self.thread_count = 20
        self.banned_extensions = {
            '.png', '.jpg', '.jpeg', '.gif', '.pdf', '.doc', '.docx',
            '.xls', '.xlsx', '.ppt', '.pptx', '.mp3', '.mp4', '.zip',
            '.tar', '.gz', '.exe', '.svg', '.css', '.js', '.ico', '.webp'
        }

        # Session mit Retries konfigurieren
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.1,
                        status_forcelist=[500, 502, 503, 504])
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.headers = {'User-Agent': 'Mozilla/5.0'}

        signal.signal(signal.SIGINT, self._exit_gracefully)

    def _exit_gracefully(self, signum, frame):
        print("\n🛑 Tiefenscan wird abgebrochen...")
        self.running = False
        sys.exit(0)

    def _is_valid_url(self, url: str) -> bool:
        parsed = urlparse(url)
        path = parsed.path.lower()
        return (
            parsed.netloc == self.domain and
            not any(path.endswith(ext) for ext in self.banned_extensions) and
            parsed.scheme in ['http', 'https']
        )

    def _fetch(self, url: str) -> str:
        try:
            with self.session.get(url, stream=True, timeout=self.timeout) as response:
                content_type = response.headers.get('Content-Type', '').lower()
                if 'text/html' not in content_type:
                    print(f"⏩ Überspringe Nicht-HTML: {url}")
                    return ''
                response.raise_for_status()
                return response.text
        except Exception as e:
            print(f"⚠️ Fehler bei {url}: {str(e)}")
            return ''

    def _check_content(self, html: str) -> bool:
        soup = BeautifulSoup(html, 'lxml')
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'meta', 'link']):
            element.decompose()
        text = soup.get_text(separator=' ', strip=True).lower()
        return self.search_term in text

    def _extract_links(self, html: str, base_url: str) -> set:
        soup = BeautifulSoup(html, 'lxml')
        links = set()
        for link in soup.find_all('a', href=True):
            absolute_url = urljoin(base_url, link['href']).split('#')[0]
            if self._is_valid_url(absolute_url):
                links.add(absolute_url)
        return links

    def _worker(self):
        while self.running:
            try:
                current_url = self.queue.get(timeout=2)
                if current_url is None:
                    break

                # Check if already visited before processing
                with self.lock:
                    if current_url in self.visited or len(self.visited) >= self.max_pages:
                        self.queue.task_done()
                        continue
                    self.visited.add(current_url)

                print(f"🌐 Scanne Seite {len(self.visited)}/{self.max_pages}: {current_url}")

                html = self._fetch(current_url)
                if html:
                    if self._check_content(html):
                        with self.lock:
                            self.found.add(current_url)
                            print(f"🎯 Treffer auf: {current_url}")

                    if len(self.visited) < self.max_pages:
                        new_links = self._extract_links(html, current_url)
                        for link in new_links:
                            with self.lock:
                                if link not in self.visited:
                                    self.queue.put(link)

                self.queue.task_done()

            except Empty:
                break
            except Exception as e:
                print(f"⚠️ Unerwarteter Fehler: {str(e)}")
                if not self.queue.empty():
                    self.queue.task_done()

    def crawl(self):
        print(f"\n🔍 Starte Tiefenscan nach '{self.search_term}' auf {self.domain}")
        
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
            for _ in range(self.thread_count):
                self.queue.put(None)
            for t in threads:
                t.join()

        print("\n📊 Endergebnis:")
        print(f"Suchbegriff: '{self.search_term}'")
        print(f"Gescannte Seiten: {len(self.visited)}")
        print(f"Maximales Limit: {'Erreicht' if len(self.visited) >= self.max_pages else 'Nicht erreicht'}")
        
        if self.found:
            print("\n✅ Treffer auf folgenden Seiten:")
            for result in self.found:
                print(f"  → {result}")
        else:
            print("\n❌ Keine Treffer gefunden")

if __name__ == "__main__":
    print("🕸️  Vollständiger Website-Scanner (Multi-Thread)")
    print("Drücke STRG+C zum Abbrechen\n")
    
    try:
        url = input("🌍 Start-URL: ").strip()
        term = input("🔎 Suchbegriff: ").strip()
        
        scraper = DeepSiteScraper(url, term)
        scraper.crawl()
            
    except Exception as e:
        print(f"❌ Kritischer Fehler: {str(e)}")
