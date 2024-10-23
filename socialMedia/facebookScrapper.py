from facebook_scraper import get_posts, _scraper
import json

with open('./mbasicHeaders.json', 'r') as file:
    _scraper.mbasic_headers = json.load(file)

for post in get_posts('NintendoAmerica', base_url="https://mbasic.facebook.com", start_url="https://mbasic.facebook.com/NintendoAmerica?v=timeline", pages=1):
    print(post['text'][:50])