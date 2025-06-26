import os
import requests
from bs4 import BeautifulSoup
import getpass
from dotenv import load_dotenv
from bs4.element import Tag

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Data', 'raw')
PDF_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Data', 'pdfs')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

LOGIN_URL = "https://www.thewinesociety.com/login"
ORDER_HISTORY_URL = "https://www.thewinesociety.com/my-account/order-history/?page=1&months=500&epmonths=300&isEnPrimeur=False"


def login(session, email, password):
    # Get login page (to get cookies and any hidden fields)
    resp = session.get(LOGIN_URL)
    soup = BeautifulSoup(resp.text, 'html.parser')
    # Find hidden fields (e.g., __RequestVerificationToken)
    login_data = {
        'Email': email,
        'Password': password,
    }
    # Add hidden fields if present
    for inp in soup.find_all('input', type='hidden'):
        if isinstance(inp, Tag):
            name = inp.attrs.get('name')
            value = inp.attrs.get('value')
            if name and value:
                login_data[str(name)] = str(value)
    # Post login
    resp = session.post(LOGIN_URL, data=login_data)
    if 'logout' not in resp.text.lower():
        print('Login failed!')
        return False
    print('Login successful!')
    return True


def fetch_order_links(session):
    resp = session.get(ORDER_HISTORY_URL)
    soup = BeautifulSoup(resp.text, 'html.parser')
    order_links = []
    for a in soup.find_all('a', href=True):
        if isinstance(a, Tag):
            href = a.get('href')
            if href and '/my-account/order-details/' in str(href):
                full_url = 'https://www.thewinesociety.com' + str(href)
                order_links.append(full_url)
    return order_links


def main():
    print('Wine Society scraper starting...')
    email = os.getenv('WINE_SOCIETY_EMAIL')
    password = os.getenv('WINE_SOCIETY_PASSWORD')
    if not email:
        email = input('Enter your Wine Society email: ')
    if not password:
        password = getpass.getpass('Enter your password: ')
    session = requests.Session()
    if not login(session, email, password):
        return
    order_links = fetch_order_links(session)
    print(f'Found {len(order_links)} order(s):')
    for link in order_links:
        print(link)

if __name__ == '__main__':
    main() 