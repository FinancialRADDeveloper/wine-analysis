"""
Selenium-based scraper for Wine Society order history and details.
"""

import os
import time
import base64
import logging
from dataclasses import dataclass, asdict
from typing import Optional, List, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("wine_soc_scraper")


@dataclass
class OrderDetail:
    order_number: Optional[str]
    order_date: Optional[str]
    order_total: Optional[str]
    url: str
    pdf_path: Optional[str]
    receipts: List[str]
    wine_notes: List[str]
    wine_links: List[str]

    def to_dict(self) -> dict:
        return asdict(self)


class WineSocietyOrderScraperSelenium:
    def __init__(self, username: str, password: str, start_url: str) -> None:
        self.username = username
        self.password = password
        self.start_url = start_url
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)

    def login(self) -> None:
        """
        Log in to the Wine Society website using Selenium, then navigate to the order
        history page.
        """
        self.driver.get(self.start_url)
        # Wait for login form
        self.wait.until(
            EC.presence_of_element_located((By.NAME, "SubmissionModel.Username"))
        )
        email_input = self.driver.find_element(By.NAME, "SubmissionModel.Username")
        password_input = self.driver.find_element(By.NAME, "SubmissionModel.Password")
        email_input.clear()
        email_input.send_keys(self.username)
        password_input.clear()
        password_input.send_keys(self.password)
        password_input.send_keys(Keys.RETURN)
        # After login, navigate directly to the order history page
        order_history_url = (
            "https://www.thewinesociety.com/my-account/order-history/?page=1&months=19"
            "&epmonths=6&isEnPrimeur=False"
        )
        self.driver.get(order_history_url)
        # Try to click the "Accept All Cookies" button if it exists
        try:
            accept_cookies_btn = self.wait.until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            accept_cookies_btn.click()
            log.info("Accepted cookies.")
        except Exception:
            log.warning("No 'Accept All Cookies' button found or could not click it.")
        # Wait for the order history page to load (look for 'View' buttons)
        self.wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//a[normalize-space(text())='View'] | "
                    "//button[normalize-space(text())='View']",
                )
            )
        )

    def get_order_view_buttons(self) -> list[Any]:
        """
        Find all 'View' buttons on the order history page.
        Returns a list of WebElement objects.
        """
        return self.driver.find_elements(
            By.XPATH, "//a[normalize-space(text())='View' and contains(@class, 'btn')]"
        )

    def save_order_page_as_pdf(self, output_path: str) -> None:
        """
        Save the current order detail page as a PDF using Chrome's print-to-PDF feature.
        Requires Chrome to be started with --headless=new and --disable-gpu for PDF output.
        """
        try:
            pdf = self.driver.execute_cdp_cmd(
                "Page.printToPDF", {"printBackground": True}
            )
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(pdf["data"]))
            log.info(f"Saved PDF to {output_path}")
        except Exception as e:
            log.error(f"Error saving PDF: {e}")

    def download_receipt_and_notes(self, download_dir: str) -> None:
        """
        Download the receipt and wine notes from the order detail page.
        Looks for links/buttons with text like 'Download receipt', 'Download wine notes', etc.
        """
        try:
            receipt_links = self.driver.find_elements(
                By.XPATH,
                "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
                "'abcdefghijklmnopqrstuvwxyz'), 'receipt')]",
            )
            for link in receipt_links:
                href = link.get_attribute("href")
                if href:
                    self.driver.execute_script(f"window.open('{href}', '_blank');")
                    log.info(f"Opened receipt link: {href}")
            notes_links = self.driver.find_elements(
                By.XPATH,
                "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
                "'abcdefghijklmnopqrstuvwxyz'), 'wine note') or "
                "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
                "'abcdefghijklmnopqrstuvwxyz'), 'tasting note')]",
            )
            for link in notes_links:
                href = link.get_attribute("href")
                if href:
                    self.driver.execute_script(f"window.open('{href}', '_blank');")
                    log.info(f"Opened wine notes link: {href}")
        except Exception as e:
            log.error(f"Error downloading receipt or notes: {e}")

    def follow_wine_links(self) -> None:
        """
        Find and follow each available wine link on the order detail page.
        Opens each wine link in a new tab and prints the URL (can be extended to scrape details).
        """
        try:
            wine_links = self.driver.find_elements(
                By.XPATH, "//a[contains(@href, '/product/')]"
            )
            for link in wine_links:
                href = link.get_attribute("href")
                if href:
                    self.driver.execute_script(f"window.open('{href}', '_blank');")
                    log.info(f"Opened wine link: {href}")
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    time.sleep(1)
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
        except Exception as e:
            log.error(f"Error following wine links: {e}")

    def handle_order_detail_page(
        self, output_dir: str = "order_details"
    ) -> Optional[OrderDetail]:
        """
        Extract order number, order date, and order total from the order detail page.
        Save the page as PDF, download receipts and wine notes, and follow wine links.
        Returns an OrderDetail dataclass instance for MongoDB storage.
        """
        # Click the "Accept All Cookies" button if it exists
        try:
            accept_btn = self.driver.find_element(By.ID, "onetrust-accept-btn-handler")
            if accept_btn.is_displayed() and accept_btn.is_enabled():
                accept_btn.click()
                time.sleep(1)
        except Exception:
            pass
        os.makedirs(output_dir, exist_ok=True)
        try:
            self.wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//*[contains(text(), 'Order No') or contains(text(), 'Order number') "
                        "or contains(text(), 'Order #') or contains(text(), 'Order no') "
                        "or contains(text(), 'OrderNo') or contains(text(), 'OrderNumber')]",
                    )
                )
            )
            # Extract order number
            try:
                order_number_elem = self.driver.find_element(
                    By.XPATH,
                    "//*[contains(text(), 'Order No') or contains(text(), 'Order number') "
                    "or contains(text(), 'Order #') or contains(text(), 'Order no') "
                    "or contains(text(), 'OrderNo') or contains(text(), 'OrderNumber')]",
                )
                order_number = order_number_elem.text
                for prefix in [
                    "Order No:",
                    "Order number:",
                    "Order #:",
                    "Order no:",
                    "OrderNo:",
                    "OrderNumber:",
                ]:
                    if order_number.startswith(prefix):
                        order_number = order_number[len(prefix) :].strip()  # noqa: E203
                        break
            except Exception:
                order_number = None
                log.error("Order Number could not be found on the order detail page.")
            # Extract order date
            try:
                order_date_h3 = self.driver.find_element(
                    By.XPATH,
                    "//h3[contains(@class, 'order-toolbar__text-column-title') "
                    "and contains(normalize-space(), 'Date placed')]",
                )
                order_date_div = order_date_h3.find_element(By.XPATH, "./parent::div")
                order_date_p = order_date_div.find_element(By.TAG_NAME, "p")
                order_date = order_date_p.text.strip()
            except Exception:
                order_date = None
                log.error("Order Date could not be found on the order detail page.")
            # Extract order total
            try:
                order_total_div = self.driver.find_element(
                    By.XPATH,
                    "//div[contains(@class, 'order-toolbar__text-column')][.//h3[contains(@class, "
                    "'order-toolbar__text-column-title') and contains(normalize-space(), 'Order total')]]",
                )
                order_total_p = order_total_div.find_element(By.TAG_NAME, "p")
                order_total = order_total_p.text.strip()
            except Exception:
                order_total = None
                log.error("Order Total could not be found on the order detail page.")
            # 1. Save the page as PDF
            pdf_path = os.path.join(
                output_dir, f"{order_number or 'unknown_order'}.pdf"
            )
            self.save_order_page_as_pdf(pdf_path)
            # 2. Download receipt and wine notes (collect links)
            receipts: List[str] = []
            wine_notes: List[str] = []
            try:
                receipt_links = self.driver.find_elements(
                    By.XPATH,
                    "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
                    "'abcdefghijklmnopqrstuvwxyz'), 'receipt')]",
                )
                for link in receipt_links:
                    href = link.get_attribute("href")
                    if href:
                        receipts.append(href)
                        self.driver.execute_script(f"window.open('{href}', '_blank');")
                        log.info(f"Opened receipt link: {href}")
                notes_links = self.driver.find_elements(
                    By.XPATH,
                    "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
                    "'abcdefghijklmnopqrstuvwxyz'), 'wine note') or "
                    "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
                    "'abcdefghijklmnopqrstuvwxyz'), 'tasting note')]",
                )
                for link in notes_links:
                    href = link.get_attribute("href")
                    if href:
                        wine_notes.append(href)
                        self.driver.execute_script(f"window.open('{href}', '_blank');")
                        log.info(f"Opened wine notes link: {href}")
            except Exception as e:
                log.error(f"Error downloading receipt or notes: {e}")
            # 3. Follow wine links (collect links)
            wine_links: List[str] = []
            try:
                wine_link_elems = self.driver.find_elements(
                    By.XPATH, "//a[contains(@href, '/product/')]"
                )
                for link in wine_link_elems:
                    href = link.get_attribute("href")
                    if href:
                        wine_links.append(href)
                        self.driver.execute_script(f"window.open('{href}', '_blank');")
                        log.info(f"Opened wine link: {href}")
                        self.driver.switch_to.window(self.driver.window_handles[-1])
                        time.sleep(1)
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
            except Exception as e:
                log.error(f"Error following wine links: {e}")
            log.info(f"Order Number: {order_number}")
            log.info(f"Order Date: {order_date}")
            log.info(f"Order Total: {order_total}")
            log.info(f"PDF Path: {pdf_path}")
            log.info(f"Receipts: {receipts}")
            log.info(f"Wine Notes: {wine_notes}")
            log.info(f"Wine Links: {wine_links}")
            return OrderDetail(
                order_number=order_number,
                order_date=order_date,
                order_total=order_total,
                url=self.driver.current_url,
                pdf_path=pdf_path,
                receipts=receipts,
                wine_notes=wine_notes,
                wine_links=wine_links,
            )
        except Exception as e:
            log.error(f"Error extracting order details: {e}")
            return None

    def scrape_all_orders(self) -> List[OrderDetail]:
        """
        Main method to scrape all orders using Selenium.
        Opens each order detail page in a new tab, scrapes, closes, and returns to main tab.
        """
        orders: List[OrderDetail] = []
        view_links = self.get_order_view_buttons()
        log.info(f"Found {len(view_links)} orders.")
        # Collect all hrefs first
        hrefs = []
        for link in view_links:
            href = link.get_attribute("href")
            if href:
                hrefs.append(href)
        main_window = self.driver.current_window_handle
        for href in hrefs:
            # Open order detail in a new tab
            self.driver.execute_script(f"window.open('{href}', '_blank');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            order_data = self.handle_order_detail_page()
            if order_data:
                orders.append(order_data)
            self.driver.switch_to.window(main_window)
        return orders

    def close(self) -> None:
        self.driver.quit()


def main() -> None:
    import os
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
    try:
        username = os.getenv("WINE_SOCIETY_EMAIL")
        password = os.getenv("WINE_SOCIETY_PASSWORD")
        if not username or not password:
            raise ValueError(
                "WINE_SOCIETY_EMAIL and/or WINE_SOCIETY_PASSWORD not set in .env file."
            )
    except Exception as e:
        log.error(f"Error loading credentials: {e}")
        raise
    start_url = (
        "https://www.thewinesociety.com/my-account/order-history/?page=1&months=19"
        "&epmonths=6&isEnPrimeur=False"
    )
    scraper = WineSocietyOrderScraperSelenium(username, password, start_url)
    try:
        scraper.login()
        orders = scraper.scrape_all_orders()
        for order in orders:
            log.info(order)
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
