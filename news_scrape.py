import os
import re
import random
import time
from datetime import datetime

import urllib.request
import urllib.error

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException, ElementClickInterceptedException

from bs4 import BeautifulSoup
# import pandas as pd

from robocorp import workitems
from robocorp.tasks import task


class NewsScraper:
    
    def __init__(self, download_path):
        self.driver = self.setup_driver()
        self.download_path = download_path

    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--disable-cache")
        return webdriver.Chrome(options=chrome_options)

    def find_search_phrase(self, text, phrase):
        count = 0
        if phrase in text:
            text_list = text.split(" ")
            for i in text_list:
                if i == phrase:
                    count += 1
            return count
        else:
            return 0

    def contains_money(self, title, description):
        possible_patterns = re.compile(
            r"""(\$)(\d+)
            \s?(\b\w+\b)
            \s?(dollar|dollars|USD)?""", 
            re.IGNORECASE
            )
        
        title_finder = possible_patterns.findall(title)
        desc_finder = possible_patterns.findall(description)
        if title_finder:
            return True
        elif desc_finder:
            return True
        else:
            return False

    def random_slug(self):
        numbers_and_letters = [
            "a", "1", "b", "2", "c", 
            "3", "d", "4", "e", "5", 
            "f", "6", "g", "7", "h", 
            "8", "i", "9", "j", "10", 
            "k", "11", "l", "12", "m", 
            "13", "n", "14", "o"
            ]
        
        generated_img_slug = []
        
        for i in range(10):
            random_num = random.randint(0, len(numbers_and_letters) - 1)
            generated_img_slug.append(str(numbers_and_letters[random_num]))
        return "".join(generated_img_slug)

    def extractor(self, phrase):
        time.sleep(5)
        self.driver.refresh()
        get_new_elem = self.driver.find_element(By.CLASS_NAME, "search-results-module-results-menu")
        needed_data = get_new_elem.get_attribute("outerHTML")

        soup = BeautifulSoup(needed_data, "html.parser")
        select_time = soup.find_all("p", class_="promo-timestamp")
        select_image_outer = soup.find_all("div", class_="promo-media")
        joined = "".join([str(tag) for tag in select_image_outer])
        new_soup = BeautifulSoup(joined, "html.parser")
        select_image_inner = new_soup.find_all("img")
        select_title = soup.find_all("h3", class_="promo-title")
        select_description = soup.find_all("p", class_="promo-description")

        data_list = []

        for i in range(0, len(select_time)):
            timestamp_obj = select_time[i].get("data-timestamp")
            time_convert = datetime.fromtimestamp(int(timestamp_obj)/1000)
            days_limit = datetime.now()-time_convert
            if days_limit.days < 5:
                iterary = []
                equivalent_title = select_title[i]
                title_text = equivalent_title.get_text(strip=True)
                iterary.append(title_text)
                equivalent_description = select_description[i]
                description_text = equivalent_description.get_text(strip=True)
                iterary.append(description_text)
                equivalent_time = select_time[i]
                iterary.append(equivalent_time.get_text(strip=True))
                equivalent_image = select_image_inner[i]
                src_path = equivalent_image.get('src')
                img_path = os.path.join(self.download_path, f"{self.random_slug()}.jpg")

                try:
                    urllib.request.urlretrieve(src_path, img_path)
                except urllib.error.URLError as e:
                    print(f"Error: URLError - {e.reason}")
                except urllib.error.HTTPError as e:
                    print("Error: HTTPError - {e.reason}")

                iterary.append(img_path)
                title_phrase_num = self.find_search_phrase(title_text, phrase)
                iterary.append(title_phrase_num)
                description_phrase_num = self.find_search_phrase(description_text, phrase)
                iterary.append(description_phrase_num)
                money_present = self.contains_money(title_text, description_text)
                iterary.append(money_present)
                data_list.append(iterary)
            else:
                return None
            
        return data_list

    def scrape_data(self, keyword):
        self.driver.get("https://www.latimes.com/")
        if os.path.exists(r"output/images"):
            os.remove(r"output/images")
            os.mkdir(r"output/images")
        else:
            os.mkdir(r"output/images")
        try:
            search_button = WebDriverWait(
                self.driver, 10).until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "body > ps-header > header > div.flex.\[\@media_print\]\:hidden > button"
                )))
            search_button.click()

            search_box = WebDriverWait(self.driver, 15).until(EC.presence_of_element_located((By.NAME, "q")))
            search_box.send_keys(keyword)
            search_box.send_keys(Keys.ENTER)

            date_dropdown = WebDriverWait(
                self.driver, 10).until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, 
                """body > div.page-content > 
                ps-search-results-module > form > 
                div.search-results-module-ajax > 
                ps-search-filters > div > main > 
                div.search-results-module-results-header >
                div.search-results-module-sorts >
                div > label > select
                """)))

            select = Select(date_dropdown)
            select.select_by_visible_text("Newest")

            extracted_data = self.extractor(keyword)
        except NoSuchElementException:
            print(f"There are not any results that match {keyword}")
        try:
            while True:
                next_page = WebDriverWait(
                    self.driver, 10).until(EC.element_to_be_clickable(
                    (By.CLASS_NAME, "search-results-module-next-page"
                    )))
                
                next_page.click()
                data = self.extractor(keyword)
                if data is None:
                    print("done")
                    break
                else:
                    extracted_data.extend(data)

        except ElementClickInterceptedException:
            print(f"Click Intercepted Error: Another element is intercepting the click action to the next page.")

        df = pd.DataFrame(extracted_data, columns=[
            "Title", 
            "Description", 
            "Time", 
            "Image", 
            "Count of Search Phrases in Title", 
            "Count of Search Phrases in Description", 
            "Contains Money"
            ])
        
        df.index = df.index + 1
        try:
            df.to_excel(os.path.join(self.download_path, "news_scrape.xlsx"))
        except PermissionError:
            print("Permission Error: Be Sure to close the Excel file before running the program")


@task
def search_phrase():
    try:
        input = workitems.inputs.current
        return input.payload.get("search_phrase")
    except:
        input = workitems.inputs.current
        input.payload = {"search_phrase": "food"}
        return input.payload.get("search_phrase")

if __name__ == "__main__":
    try:
        scraper = NewsScraper(r"output/images")
        scraper.scrape_data(search_phrase())

    except TimeoutException:
        print("Timeout Error: Make sure you have a stable internet connection")

    except WebDriverException as e:
        if "net::ERR_INTERNET_DISCONNECTED" in str(e):
            print("Internet Disconnected Error: Your internet connection is down.")
        else:
            print(f"WebDriverException: {str(e)}")

             