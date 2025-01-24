# Deep Website Scraper 🕸️

A powerful, multi-threaded Python web scraper that performs deep scanning of websites to find specific search terms.

## Features ✨

- 🚀 Multi-threaded scanning for high performance
- 🔍 Deep recursive scanning of websites
- 🛡️ Built-in protection against common errors
- ⚡ Automatic retry mechanism for failed requests
- 🎯 Smart filtering of non-HTML content
- 🔒 Domain-restricted scanning
- ⏱️ Configurable timeout settings
- 📊 Detailed progress reporting
- 🛑 Graceful exit with CTRL+C

## Requirements 📋

- Python 3.6+
- Required packages:
  - requests
  - beautifulsoup4
  - lxml

## Installation 🔧

1. Clone this repository:
```bash
git clone https://github.com/UntoastedToast/DeepWebsiteScraper.git
cd DeepWebsiteScraper
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

All dependencies with their correct versions will be installed automatically.

## Usage 💻

1. Run the script:
```bash
python DeepWebsiteScraper.py
```

2. Enter the required information:
   - Start URL (e.g., https://example.com)
   - Search term to find

3. The scraper will begin scanning and show real-time progress:
   - 🌐 Currently scanning page
   - 🎯 Found matches
   - ⚠️ Errors (if any)
   - 📊 Final results

## Configuration ⚙️

The following parameters can be adjusted in the `DeepSiteScraper` class:

- `timeout`: Request timeout in seconds (default: 8)
- `max_pages`: Maximum pages to scan (default: 500)
- `thread_count`: Number of concurrent threads (default: 20)
- `banned_extensions`: File types to skip

## Features in Detail 🔎

- **Smart Content Filtering**: Automatically skips non-HTML content and irrelevant file types
- **Domain Restriction**: Only scans pages within the specified domain
- **Error Handling**: Implements retry mechanism for failed requests
- **Resource Management**: Efficient queue-based multi-threading
- **Progress Tracking**: Real-time scanning status and results
- **Memory Efficient**: Tracks visited URLs to avoid duplicate scanning

## Error Handling 🛡️

The scraper includes comprehensive error handling:
- Automatic retries for server errors (500, 502, 503, 504)
- Timeout protection
- Invalid URL detection
- Non-HTML content filtering
- Graceful exit handling

## License 📄

This project is open source and available under the MIT License.

## Contributing 🤝

Contributions, issues, and feature requests are welcome!

## Notes 📝

- Use responsibly and respect website robots.txt
- Configure thread count based on your system capabilities
- Adjust timeout settings based on target website response times
