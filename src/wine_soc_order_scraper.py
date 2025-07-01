import requests  # type: ignore[import-untyped]
from bs4 import BeautifulSoup
from typing import List
import bs4

# TODO: If login or JavaScript is required, switch to Selenium


class WineSocietyOrderScraper:
    def __init__(self, start_url: str, session: "requests.Session | None" = None):
        self.start_url = start_url
        self.session = session or requests.Session()

    def login(self, username: str, password: str) -> None:
        """
        Placeholder for login logic. If login is required, implement here.
        """
        # TODO: Implement login if needed
        pass

    def get_orders_page(self) -> BeautifulSoup:
        """
        Fetch the orders page and return a BeautifulSoup object.
        """
        resp = self.session.get(self.start_url)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")

    def find_order_links(self, soup: BeautifulSoup) -> List[str]:
        """
        Find all 'View' buttons/links for orders on the page.
        Handles both <a> and <button> elements with the text 'View'.
        If <a>, extracts href. If <button>, notes that Selenium is needed.
        """
        order_links: List[str] = []
        # Find <a> tags with text 'View'
        for a in soup.find_all("a", string="View"):
            if isinstance(a, bs4.element.Tag):
                href = a.get("href")
                if isinstance(href, str):
                    order_links.append(href)
        # Find <button> tags with text 'View' (static scraping cannot follow these)
        for btn in soup.find_all("button", string="View"):
            if isinstance(btn, bs4.element.Tag):
                # NOTE: Static scraping cannot follow button clicks; Selenium is needed for this
                order_links.append("[BUTTON: Selenium required]")
        return order_links

    def scrape_order_detail(self, order_url: str) -> dict:
        """
        Scrape data from an individual order detail page.
        Placeholder for now; update with actual scraping logic.
        """
        resp = self.session.get(order_url)
        resp.raise_for_status()
        # TODO: Extract relevant data from the order detail page
        return {"url": order_url, "data": "TODO: extract order data"}

    def scrape_all_orders(self) -> List[dict]:
        """
        Main method to scrape all orders from the orders page.
        """
        soup = self.get_orders_page()
        order_links = self.find_order_links(soup)
        print(f"Found {len(order_links)} orders.")
        orders = []
        for link in order_links:
            # If links are relative, prepend domain
            if link.startswith("/"):
                from urllib.parse import urljoin

                link = urljoin(self.start_url, link)
            order_data = self.scrape_order_detail(link)
            orders.append(order_data)
        return orders


def main() -> None:
    # Example usage
    start_url = "https://www.thewinesociety.com/my-account/orders"  # TODO: Replace with actual start link
    scraper = WineSocietyOrderScraper(start_url)
    # scraper.login('username', 'password')  # Uncomment and implement if needed
    orders = scraper.scrape_all_orders()
    for order in orders:
        print(order)


if __name__ == "__main__":
    main()
