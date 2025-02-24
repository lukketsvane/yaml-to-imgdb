import os
import re
import yaml
import concurrent.futures
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from serpapi import GoogleSearch
from colorama import Fore, Style
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path("data-store")

def sanitize_name(name: str) -> str:
    """
    Convert a string to lowercase, replace all non-alphanumeric
    characters with dashes, and strip leading/trailing dashes.
    """
    name = name.lower()
    name = re.sub(r'[^a-z0-9]+', '-', name)
    return name.strip('-')

# Global Session with retry logic
SESSION = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
SESSION.mount("http://", adapter)
SESSION.mount("https://", adapter)

def load_products():
    """
    Loads all YAML from data-store/*.yaml, merging into a dict:
    {
      "DesignHouse": {
         "ProductA": 1985,
         "ProductB": 1990,
      },
      ...
    }
    """
    products = {}
    for yaml_file in DATA_DIR.glob("*.yaml"):
        try:
            content = yaml.safe_load(yaml_file.read_text()) or {}
            for design_house, items in content.items():
                if design_house not in products:
                    products[design_house] = {}
                if isinstance(items, dict):
                    products[design_house].update(items)
        except Exception as e:
            print(f"{Fore.RED}Error loading {yaml_file.name}: {e}{Style.RESET_ALL}")
    return products

def download_image(design_house, product, year):
    """
    Use SerpAPI to find a large image with a white background,
    searching for: <design_house> "<product>" large photo with white background.
    Saves to data-store/<dh_sanitized>/<product_sanitized>-<year>.jpg if not present.
    """
    dh_sanitized = sanitize_name(design_house)
    product_sanitized = sanitize_name(product)
    save_dir = DATA_DIR / dh_sanitized
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / f"{product_sanitized}-{year}.jpg"

    if save_path.exists():
        return  # Already downloaded

    try:
        # Product in quotes, "large photo with white background", tbs=isz:l
        search = GoogleSearch({
            "engine": "google_images",
            "q": f"{design_house} \"{product}\" large photo with white background",
            "api_key": os.getenv("SERP_API_KEY"),
            "num": 1,
            "tbs": "isz:l"
        })
        result = search.get_dict()
        img_url = result.get("images_results", [{}])[0].get("original")
        if not img_url:
            return

        resp = SESSION.get(img_url, timeout=5)
        save_path.write_bytes(resp.content)
        print(f"{Fore.GREEN}Downloaded {design_house}/{product}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Failed {design_house}/{product}: {e}{Style.RESET_ALL}")

def main():
    products_dict = load_products()
    tasks = []
    for dh, items in products_dict.items():
        for product, year in items.items():
            tasks.append((dh, product, year))

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(lambda t: download_image(*t), tasks)

if __name__ == "__main__":
    main()
