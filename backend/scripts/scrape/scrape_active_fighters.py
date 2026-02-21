from bs4 import BeautifulSoup
import requests
import json
import pandas as pd
ACTIVE_FIGHTER_URL = "https://www.ufc.com/athletes/all?filters%5B0%5D=status%3A23"

url_params = {
    "view_name": "all_athletes",
    "view_display_id": "page",
    "view_args": "",
    "view_path": "/athletes/all",
    "view_base_path": "",
    "filters[0]": "status:23",
    "page": 0,
    "pager_element": "0",
    "ajax_page_state[theme]": "ufc",
    "ajax_page_state[theme_token]": ""
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def scrape_active_fighters():
    """
    Scrapes the UFC website for active fighters and returns a set of their normalized names.
    """
    session = requests.Session()
    response = session.get(ACTIVE_FIGHTER_URL, headers=HEADERS)
    response.raise_for_status()
    
    # Parse response to extract required parameters
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Find drupal settings script tag and parse JSON
    drupal_settings_tag = soup.find("script", {"data-drupal-selector": "drupal-settings-json"})
    drupal_settings = json.loads(drupal_settings_tag.string)
    
    # Extract and add to url_params
    url_params["ajax_page_state[libraries]"] = drupal_settings["ajaxPageState"]["libraries"]
    
    ajax_views = drupal_settings["views"]["ajaxViews"]
    first_view = next(iter(ajax_views.values()))
    url_params["view_dom_id"] = first_view["view_dom_id"]

    response_list = []
    page = 0
    
    # Loop through pages until no more fighters are found
    while True:
        url_params["page"] = page
        response = session.get(ACTIVE_FIGHTER_URL, params=url_params, headers=HEADERS)
        soup = BeautifulSoup(response.text, "html.parser")
        
        fighters = soup.select(".c-listing-athlete__name")
        if not fighters:
            break
            
        response_list.append(soup)
        page += 1
    
    # Extract all fighter names from all pages
    fighter_names = []
    div_list = []
    for soup in response_list:
        divs = soup.find_all("div", class_="c-listing-athlete-flipcard__front")
        div_list.extend(divs)
        for div in divs:
            name = div.find("span", class_="c-listing-athlete__name")
            if name:
                fighter_names.append(name.text.strip())

    df = pd.DataFrame(fighter_names, columns=["Fighter Name"])
scrape_active_fighters()