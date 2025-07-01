from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from dataclasses import dataclass, asdict
import os

@dataclass
class OrderDetail:
    order_number: str | None
    order_date: str | None
    order_total: str | None
    url: str
    pdf_path: str | None
    receipts: list[str]
    wine_notes: list[str]
    wine_links: list[str]

    def to_dict(self):
        return asdict(self)

class WineSocietyOrderScraperSelenium:
    def __init__(self, username: str, password: str, start_url: str):
        self.username = username
        self.password = password
        self.start_url = start_url
        chrome_options = Options()
        chrome_options.add_argument('--start-maximized')
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)

    def login(self):
        """
        Log in to the Wine Society website using Selenium, then navigate to the order history page.
        """
        self.driver.get(self.start_url)
        # Wait for login form
        self.wait.until(EC.presence_of_element_located((By.NAME, 'SubmissionModel.Username')))
        email_input = self.driver.find_element(By.NAME, 'SubmissionModel.Username')
        password_input = self.driver.find_element(By.NAME, 'SubmissionModel.Password')
        email_input.clear()
        email_input.send_keys(self.username)
        password_input.clear()
        password_input.send_keys(self.password)
        password_input.send_keys(Keys.RETURN)
        # After login, navigate directly to the order history page
        order_history_url = 'https://www.thewinesociety.com/my-account/order-history/?page=1&months=19&epmonths=6&isEnPrimeur=False'
        self.driver.get(order_history_url)
        # Wait for the order history page to load (look for 'View' buttons)
        # Wait for either <a> or <button> elements with text 'View' to be present
        self.wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//a[normalize-space(text())='View'] | //button[normalize-space(text())='View']"
                )
            )
        )

        # Find all <a> elements with text 'View'
        view_links = self.driver.find_elements(By.XPATH, "//a[normalize-space(text())='View']")
        for link in view_links:
            href = link.get_attribute("href")
            if href:
                # Open each order detail in a new tab
                self.driver.execute_script(f"window.open('{href}', '_blank');")
                self.driver.switch_to.window(self.driver.window_handles[-1])
                self.handle_order_detail_page()
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])

    def get_order_view_buttons(self):
        """
        Find all 'View' buttons on the order history page.
        Returns a list of WebElement objects.
        """
        return self.driver.find_elements(By.XPATH, "//button[text()='View']")

    def scrape_order_detail(self):
        """
        Placeholder for scraping order detail data from the current page.
        """
        # TODO: Implement actual scraping logic here
        time.sleep(1)  # Simulate wait for page load
        return {'url': self.driver.current_url, 'data': 'TODO: extract order data'}

    def scrape_all_orders(self):
        """
        Main method to scrape all orders using Selenium.
        """
        orders = []
        view_buttons = self.get_order_view_buttons()
        print(f"Found {len(view_buttons)} orders.")
        for _, btn in enumerate(view_buttons):
            # Open order detail in a new tab
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            # Click the button in the original tab to get the order detail URL
            self.driver.switch_to.window(self.driver.window_handles[0])
            self.driver.execute_script("arguments[0].click();", btn)
            time.sleep(2)  # Wait for navigation
            # Switch to the new tab and scrape
            self.driver.switch_to.window(self.driver.window_handles[-1])
            order_data = self.scrape_order_detail()
            orders.append(order_data)
            # Close the detail tab and return to the main tab
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
        return orders

    def close(self):
        self.driver.quit()

    def handle_order_detail_page(self, output_dir: str = "order_details") -> OrderDetail | None:
        """
        Extract order number, order date, and order total from the order detail page.
        Save the page as PDF, download receipts and wine notes, and follow wine links.
        Returns an OrderDetail dataclass instance for MongoDB storage.
        """
        os.makedirs(output_dir, exist_ok=True)
        try:
            # Wait for the order detail page to load (adjust selector as needed)
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Order No') or contains(text(), 'Order number') or contains(text(), 'Order #') or contains(text(), 'Order no') or contains(text(), 'OrderNo') or contains(text(), 'OrderNumber')]")))

            # Extract order number
            try:
                order_number_elem = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Order No') or contains(text(), 'Order number') or contains(text(), 'Order #') or contains(text(), 'Order no') or contains(text(), 'OrderNo') or contains(text(), 'OrderNumber')]")
                order_number = order_number_elem.text
            except Exception:
                order_number = None

            # Extract order date (look for 'Date:' or similar)
            try:
                order_date_elem = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Date:')]")
                order_date = order_date_elem.text
            except Exception:
                order_date = None

            # Extract order total (look for 'Order total:' or similar)
            try:
                order_total_elem = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Order total:')]")
                order_total = order_total_elem.text
            except Exception:
                order_total = None

            # 1. Save the page as PDF
            pdf_path = os.path.join(output_dir, f"{order_number or 'unknown_order'}.pdf")
            self.save_order_page_as_pdf(pdf_path)

            # 2. Download receipt and wine notes (collect links)
            receipts = []
            wine_notes = []
            try:
                # Receipts
                receipt_links = self.driver.find_elements(By.XPATH, "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'receipt')]")
                for link in receipt_links:
                    href = link.get_attribute("href")
                    if href:
                        receipts.append(href)
                        self.driver.execute_script(f"window.open('{href}', '_blank');")
                # Wine notes
                notes_links = self.driver.find_elements(
                    By.XPATH,
                    "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'wine note') or "
                    "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'tasting note')]"
                )
                for link in notes_links:
                    href = link.get_attribute("href")
                    if href:
                        wine_notes.append(href)
                        self.driver.execute_script(f"window.open('{href}', '_blank');")
            except Exception as e:
                print(f"Error downloading receipt or notes: {e}")

            # 3. Follow wine links (collect links)
            wine_links = []
            try:
                wine_link_elems = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/product/')]")
                for link in wine_link_elems:
                    href = link.get_attribute("href")
                    if href:
                        wine_links.append(href)
                        self.driver.execute_script(f"window.open('{href}', '_blank');")
                        print(f"Opened wine link: {href}")
                        self.driver.switch_to.window(self.driver.window_handles[-1])
                        time.sleep(1)  # Simulate scraping
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
            except Exception as e:
                print(f"Error following wine links: {e}")

            print(f"Order Number: {order_number}")
            print(f"Order Date: {order_date}")
            print(f"Order Total: {order_total}")
            print(f"PDF Path: {pdf_path}")
            print(f"Receipts: {receipts}")
            print(f"Wine Notes: {wine_notes}")
            print(f"Wine Links: {wine_links}")

            return OrderDetail(
                order_number=order_number,
                order_date=order_date,
                order_total=order_total,
                url=self.driver.current_url,
                pdf_path=pdf_path,
                receipts=receipts,
                wine_notes=wine_notes,
                wine_links=wine_links
            )
        except Exception as e:
            print(f"Error extracting order details: {e}")
            return None

    def save_order_page_as_pdf(self, output_path: str):
        """
        Save the current order detail page as a PDF using Chrome's print-to-PDF feature.
        Requires Chrome to be started with --headless=new and --disable-gpu for PDF output.
        """
        # This requires the DevTools Protocol; Selenium 4+ supports it
        try:
            pdf = self.driver.execute_cdp_cmd("Page.printToPDF", {"printBackground": True})
            with open(output_path, "wb") as f:
                f.write(bytes.fromhex(pdf["data"]))
            print(f"Saved PDF to {output_path}")
        except Exception as e:
            print(f"Error saving PDF: {e}")

    def download_receipt_and_notes(self, download_dir: str):
        """
        Download the receipt and wine notes from the order detail page.
        Looks for links/buttons with text like 'Download receipt', 'Download wine notes', etc.
        """
        try:
            # Find and click/download receipt
            receipt_links = self.driver.find_elements(By.XPATH, "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'receipt')]")
            for link in receipt_links:
                href = link.get_attribute("href")
                if href:
                    self.driver.execute_script(f"window.open('{href}', '_blank');")
                    print(f"Opened receipt link: {href}")
            # Find and click/download wine notes
            # The alphabet is used in the XPath to make the text search case-insensitive.
            # However, Selenium 4+ and modern browsers support the 'translate' function, but for clarity, let's simplify:
            # We'll use 'translate' to lowercase the text, but let's explain it:
            # This XPath finds <a> elements whose text contains 'wine note' or 'tasting note', case-insensitive.
            notes_links = self.driver.find_elements(
                By.XPATH,
                "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'wine note') or "
                "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'tasting note')]"
            )
            for link in notes_links:
                href = link.get_attribute("href")
                if href:
                    self.driver.execute_script(f"window.open('{href}', '_blank');")
                    print(f"Opened wine notes link: {href}")
        except Exception as e:
            print(f"Error downloading receipt or notes: {e}")

    def follow_wine_links(self):
        """
        Find and follow each available wine link on the order detail page.
        Opens each wine link in a new tab and prints the URL (can be extended to scrape details).
        """
        try:
            wine_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/product/')]")
            for link in wine_links:
                href = link.get_attribute("href")
                if href:
                    self.driver.execute_script(f"window.open('{href}', '_blank');")
                    print(f"Opened wine link: {href}")
                    # Optionally, switch to new tab and scrape, then close
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    time.sleep(1)  # Simulate scraping
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
        except Exception as e:
            print(f"Error following wine links: {e}")

def main():
    import os
    from dotenv import load_dotenv

    # Load environment variables from .env file in the parent directory
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

    try:
        username = os.getenv('WINE_SOCIETY_EMAIL')
        password = os.getenv('WINE_SOCIETY_PASSWORD')
        if not username or not password:
            raise ValueError("WINE_SOCIETY_EMAIL and/or WINE_SOCIETY_PASSWORD not set in .env file.")
    except Exception as e:
        print(f"Error loading credentials: {e}")
        raise
    
    start_url = 'https://www.thewinesociety.com/my-account/order-history/?page=1&months=19&epmonths=6&isEnPrimeur=False'
    scraper = WineSocietyOrderScraperSelenium(username, password, start_url)
    try:
        scraper.login()
        orders = scraper.scrape_all_orders()
        for order in orders:
            print(order)
    finally:
        scraper.close()

if __name__ == '__main__':
    main() 