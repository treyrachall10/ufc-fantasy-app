from bs4 import BeautifulSoup
from backend.shared.utils import normalize_name

def parse_html(soup):
    """
    Parses the HTML content of a page and extracts the fighter names and image URLs.
    Returns a list of objects: {normalized_name: ..., img_url: ...}
    """
    # Parse HTML content with BeautifulSoup
    cards = soup.find_all('div', class_='c-listing-athlete-flipcard__front')

    fighter_objs = []
    
    # Loop through each div and extract fighter name and image URL
    for card in cards:

        name_tag = card.find('span', class_='c-listing-athlete__name') # Gets fighter name
        img_tag = card.find('img') if card.find('img') else None # gets image tag

        # Add to list if both name and image tag exist
        if name_tag and img_tag:

            name = name_tag.text.strip() # Extract name from name tag
            img_url = img_tag['src'] # Extract image URL from img tag
            normalized_name = normalize_name(name)# Normalize name
            
            # Add to fighter list
            fighter_objs.append({
                'normalized_name': normalized_name,
                'img_url': img_url
            })

    return fighter_objs