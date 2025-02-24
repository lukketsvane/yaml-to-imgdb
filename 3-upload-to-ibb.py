import os
import re
import yaml
import base64
import concurrent.futures
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from colorama import Fore, Style
from dotenv import load_dotenv

load_dotenv()

# Directories and API key.
DATA_DIR = Path("data-store")
PROCESSED_DIR = Path("data-store-processed")
IBB_API_KEY = os.getenv("IBB_API_KEY")

# Ensure the processed folder exists.
PROCESSED_DIR.mkdir(exist_ok=True)

def sanitize_name(name: str) -> str:
    """
    Standard dash-based naming.
    """
    name = name.lower()
    name = re.sub(r'[^a-z0-9]+', '-', name)
    return name.strip('-')

# Global session with retry logic.
SESSION = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
SESSION.mount("http://", adapter)
SESSION.mount("https://", adapter)

def unify_details(details):
    """
    Convert details into a dict with at least a 'year' key.
    The original YAML may list a product as:
      - an int (e.g. 1949)
      - a str (e.g. "1949")
      - or a dict (e.g. { 'year': 1949, 'image': '...' }).
    """
    if isinstance(details, dict):
        return details
    elif isinstance(details, int):
        return {"year": details}
    elif isinstance(details, str):
        return {"year": details}
    else:
        return {"year": ""}

def fix_yaml_structure(content):
    """
    Some YAML files (e.g. for Jasper Morrison) have a design house key with a null value
    and then separate top-level keys for products starting with "__".
    This function re-organizes such content so that products with keys starting with "__"
    are attached to the most recent design house key.
    It also cleans product names by stripping leading underscores and replacing underscores with spaces.
    """
    new_content = {}
    current_design_house = None
    for key, value in content.items():
        if not key.startswith("__"):
            # Treat this as a design house key.
            current_design_house = key
            # If value is already a dict, use it; otherwise initialize an empty dict.
            new_content[current_design_house] = value if isinstance(value, dict) else {}
        else:
            # Key starts with "__": assume it belongs to the current design house.
            if current_design_house is None:
                current_design_house = "unknown"
                new_content.setdefault(current_design_house, {})
            # Clean product name: remove leading underscores and replace remaining underscores with spaces.
            clean_product = key.lstrip("_").replace("_", " ")
            new_content[current_design_house][clean_product] = value
    return new_content

def upload_entry(design_house, product, details):
    """
    1) Convert details to a dict.
    2) If an imgbb link already exists, skip upload.
    3) Otherwise, locate the corresponding PNG file in PROCESSED_DIR and
       upload it to imgbb (using Base64 encoding).
    4) Update the details with the returned direct URL.
    Returns the updated details and a flag indicating if a change was made.
    """
    if not IBB_API_KEY:
        print(f"{Fore.RED}IBB_API_KEY not set{Style.RESET_ALL}")
        return details, False

    details = unify_details(details)
    if "image" in details and "ibb.co" in details["image"]:
        return details, False  # Already updated

    dh_sanitized = sanitize_name(design_house)
    product_sanitized = sanitize_name(product)
    year = details.get("year", "")

    # Look for the PNG file in a subfolder (named after the design house) in PROCESSED_DIR.
    png_path = PROCESSED_DIR / dh_sanitized / f"{product_sanitized}-{year}.png"
    if not png_path.exists():
        return details, False  # No processed image available

    try:
        # Read the image and encode it in Base64.
        with open(png_path, "rb") as f:
            image_bytes = f.read()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        response = SESSION.post(
            "https://api.imgbb.com/1/upload",
            data={"key": IBB_API_KEY, "image": image_base64}
        )
        response.raise_for_status()
        data = response.json().get("data", {})
        details["image"] = data.get("url", "")
        print(f"{Fore.GREEN}Uploaded {product}{Style.RESET_ALL}")
        return details, True
    except Exception as e:
        print(f"{Fore.RED}Upload failed for {product}: {e}{Style.RESET_ALL}")
        return details, False

def process_yaml_file(yaml_file: Path):
    """
    Reads a YAML file from DATA_DIR, fixes its structure if needed,
    processes each product entry (uploading images if available) and writes the updated YAML
    file to PROCESSED_DIR (using the same filename).
    """
    try:
        content = yaml.safe_load(yaml_file.read_text()) or {}
    except Exception as e:
        print(f"{Fore.RED}Error reading {yaml_file.name}: {e}{Style.RESET_ALL}")
        return

    # Fix structure if needed.
    content = fix_yaml_structure(content)

    changed_any = False
    for design_house, products in content.items():
        # Ensure that products is a dict.
        if not isinstance(products, dict):
            continue

        updated_products = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_map = {
                executor.submit(upload_entry, design_house, product, details): product
                for product, details in products.items()
            }
            for future in concurrent.futures.as_completed(future_map):
                prod = future_map[future]
                new_details, changed = future.result()
                if changed:
                    changed_any = True
                updated_products[prod] = new_details

        content[design_house] = updated_products

    output_path = PROCESSED_DIR / yaml_file.name
    yaml.dump(content, stream=open(output_path, "w"), sort_keys=False)
    if changed_any:
        print(f"{Fore.GREEN}Updated {output_path}{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}No changes for {yaml_file.name}{Style.RESET_ALL}")

def create_datatable():
    """
    Combines all updated YAML files in PROCESSED_DIR into a single datatable YAML file.
    """
    datatable = {}
    for yf in PROCESSED_DIR.glob("*.yaml"):
        try:
            content = yaml.safe_load(yf.read_text()) or {}
        except Exception as e:
            print(f"{Fore.RED}Error reading {yf.name}: {e}{Style.RESET_ALL}")
            continue

        for design_house, products in content.items():
            if not isinstance(products, dict):
                continue
            if design_house not in datatable:
                datatable[design_house] = {}
            for product, details in products.items():
                datatable[design_house][product] = details

    output_path = PROCESSED_DIR / "datatable.yaml"
    output_path.write_text(yaml.dump(datatable, sort_keys=False))
    print(f"{Fore.GREEN}Created datatable at {output_path}{Style.RESET_ALL}")

def main():
    # Process each YAML file from DATA_DIR and write updated versions to PROCESSED_DIR.
    for yf in DATA_DIR.glob("*.yaml"):
        process_yaml_file(yf)
    # Create a consolidated datatable from the updated YAML files.
    create_datatable()

if __name__ == "__main__":
    main()
