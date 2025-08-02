**Target Store Locator Scraper**

A Python-based web scraper that automatically extracts all Target store names, grouped by city, from Target’s Store Locator. Built using Playwright, this scraper bypasses bot protection and handles dynamic content effectively.

**Features**
✅ Scrapes Target stores organized by City
✅ Handles JavaScript-rendered pages using Playwright
✅ Bypasses bot detection with human-like behavior
✅ Includes retry logic, timeouts, and dynamic delays
✅ Saves data in both CSV and JSON formats
✅ Fully asynchronous for improved speed
✅ Easily configurable and modular codebase

**Sample Output**
State	City	Stores
California	Los Angeles	Target Hollywood, Target DTLA
Texas	Austin	Target North Austin, Target Southpark Meadows

Tech Stack
Python 3.8+
Playwright
pandas for CSV/JSON export
asyncio
logging, random, and standard libraries

Installation
# Clone the repo
git clone https://github.com/your-username/target-store-scraper.git
cd target-store-scraper

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install
Usage
python main.py
Your output will be saved as:

target_stores_by_city.csv
target_stores_by_city.json
Configuration
The scraper is configurable via the CONFIG dictionary in main.py:

CONFIG = {
    "timeout": 180000,
    "retry_attempts": 5,
    "headless": True,
    "sleep_min": 5.0,
    "sleep_max": 8.0,
    ...
}
You can tweak settings like timeout, headless mode, delay intervals, and more.

**Use Cases**
Data analysis and visualization
Mapping store coverage
Testing scraping frameworks
Educational/demo projects for web scraping
Disclaimer
This project is for educational purposes only. Scraping websites without permission may violate their Terms of Service. Use responsibly.

Contributing
Pull requests are welcome! Feel free to fork this project and suggest improvements.
