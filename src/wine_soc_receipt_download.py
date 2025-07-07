from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

import os
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("wine_soc_scraper")


def download_receipt_pdf_wine_society(
    order_number: str, download_dir: str = "wine_society_receipts"
) -> None:
    """
    Downloads a PDF receipt from The Wine Society for a given order number
    by simulating a browser download.

    This function uses Selenium to open a headless Chrome browser, constructs
    the specific download URL for The Wine Society, navigates to it, and
    triggers the download of the PDF, similar to how a user would in Chrome.
    It configures Chrome to automatically download PDFs without opening them.

    Args:
        order_number (str): The specific order number (e.g., 'TWSWEB-13480088')
                            which forms part of the download URL.
        download_dir (str): The directory where the PDF should be saved.
                            Defaults to 'wine_society_receipts' in the
                            current working directory.
    """
    base_download_url = (
        "https://www.thewinesociety.com/CustomFileDownload/DownloadInvoice"
    )
    receipt_url = f"{base_download_url}?orderNumber={order_number}"

    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
        print(f"Created download directory: {download_dir}")

    # Configure Chrome options for headless mode and PDF download
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode (no UI)
    chrome_options.add_argument(
        "--no-sandbox"
    )  # Required for some environments (e.g., Docker)
    chrome_options.add_argument(
        "--disable-dev-shm-usage"
    )  # Required for some environments
    chrome_options.add_argument("--disable-gpu")  # Recommended for headless
    # Disable popup for PDF viewing and enable automatic download
    chrome_options.add_experimental_option(
        "prefs",
        {
            "download.default_directory": os.path.abspath(download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,  # Crucial for direct PDF download
        },
    )

    # Initialize the WebDriver
    # IMPORTANT: Replace 'path/to/your/chromedriver.exe' with the actual path
    # or ensure chromedriver is in your system's PATH.
    try:
        service = Service(
            "chromedriver.exe"
        )  # Assumes chromedriver.exe is in PATH or current dir
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        log.error(
            "Error initializing WebDriver. Make sure chromedriver is installed and in your PATH, "
            "or specify its full path."
        )
        log.info(f"Details: {e}")
        return

    print(f"Attempting to download receipt for order number: {order_number}")
    print(f"Navigating to URL: {receipt_url}")

    try:
        # use Chrome settings to download the PDF to the default download directory
        # then we move this to the correct folder?
        driver.get(receipt_url)

        log.info(
            "Waiting for download to initiate and complete... (this might take a few seconds)"
        )
        time.sleep(1)  # Increased sleep slightly as a precaution. Adjust as needed.

        # Optional: You could add logic here to list files in download_dir
        # and check if a new PDF has appeared with a relevant filename.
        # This would require more sophisticated file system monitoring.

        log.info(
            f"Download triggered. Check directory: {os.path.abspath(download_dir)}"
        )

    except Exception as e:
        print(f"An error occurred during download: {e}")


# --- How to use it ---
if __name__ == "__main__":
    # Example Usage:
    # Replace 'TWSWEB-13480088' with the actual order number you want to download.
    # Be aware of authentication if you are not already logged into The Wine Society.

    # If you typically need to log in to access this, this function alone won't
    # work unless you have an existing session/cookies that Selenium can pick up
    # (which it typically won't in a fresh headless run) or if you add explicit
    # login steps before navigating to the download URL.

    my_order_number = "TWSWEB-13480088"  # Example order number from your URL
    download_directory = "my_wine_receipts"  # Custom download directory

    download_receipt_pdf_wine_society(my_order_number, download_directory)
