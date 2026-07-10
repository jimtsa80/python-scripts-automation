import os
import requests
from bs4 import BeautifulSoup

# Create a folder to store the text files
if not os.path.exists('scraped_texts'):
    os.mkdir('scraped_texts')

# Function to fetch and parse a page
def fetch_page(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

# Function to save text to a file
def save_to_file(url, text):
    # Clean the URL to create a valid file name
    file_name = url.replace('https://www.fainareti.gr/el/', '').replace('/', '_') + '.txt'
    file_path = os.path.join('scraped_texts', file_name)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text)

# Scrape the homepage and get links
url = "https://www.fainareti.gr/el/"
soup = fetch_page(url)

if soup:
    # Extract all links from the homepage
    links = [a['href'] for a in soup.find_all('a', href=True)]
    
    # Filter out the links that are relative or internal (they don't start with 'http')
    internal_links = [link if link.startswith('http') else f'https://www.fainareti.gr{link}' for link in links]

    # Scrape each internal page and save its text
    for link in internal_links:
        page_soup = fetch_page(link)
        if page_soup:
            page_text = page_soup.get_text()
            save_to_file(link, page_text)

    print("Scraping complete. Text files saved.")
