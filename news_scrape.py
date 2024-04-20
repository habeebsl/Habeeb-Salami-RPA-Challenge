import os
import re
import random
import time
from datetime import datetime
import shutil

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
import pandas as pd

from robocorp import workitems
from robocorp.tasks import task


class NewsScraper:
    """
    A class to scrape news data from the LA Times 
    website and download images related to the news
    articles.
    """

    def __init__(self, download_path):
        """
        Initialize the NewsScraper with the download path.

        Args:
        - download_path (str): The path to the directory where images will be downloaded.
        """
        self.driver = self.setup_driver()
        self.download_path = download_path

    def setup_driver(self):
        """
        Set up the WebDriver for Chrome.

        Returns:
        - webdriver.Chrome: An instance of the Chrome WebDriver.
        """
        chrome_options = Options()
        chrome_options.add_argument("--disable-cache")
        return webdriver.Chrome(options=chrome_options)

    def find_search_phrase(self, text, phrase):
        """
        Find the number of occurrences of a phrase in a text.

        Args:
        - text (str): The text to search for the phrase.
        - phrase (str): The phrase to search for in the text.

        Returns:
        - int: The number of occurrences of the phrase in the text.
        """
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
        """
        Check if the title or description contains a money pattern.

        Args:
        - title (str): The title of the news article.
        - description (str): The description of the news article.

        Returns:
        - bool: True if the money pattern is found, False otherwise.
        """
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
        """
        Generate a random string to be used as image filenames.

        Returns:
        - str: A random string of alphanumeric characters.
        """
        numbers_and_letters = [
            "a", "1", "b", "2", "c",
            "3", "d", "4", "e", "5",
            "f", "6", "g", "7", "h",
            "8", "i", "9", "j", "10",
            "k", "11", "l", "12", "m",
            "13", "n", "14", "o"
        ]

        generated_img_slug = []

        for _ in range(10):
            random_num = random.randint(0, len(numbers_and_letters) - 1)
            generated_img_slug.append(str(numbers_and_letters[random_num]))
        return "".join(generated_img_slug)

    def extractor(self, phrase):
        """
        Extract data based on a search phrase from the LA Times website.

        Args:
        - phrase (str): The search phrase to use for extracting data.

        Returns:
        - list: A list of extracted data containing news article information.
        """
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
            time_convert = datetime.fromtimestamp(int(timestamp_obj) / 1000)
            days_limit = datetime.now() - time_convert
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
                    print(f"Error: HTTPError - {e.reason}")

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
        """
        Scrape news data based on a keyword from the LA Times website.

        Args:
        - keyword (str): The keyword to search for news articles.

        Outputs:
        - Excel file: Saves extracted data to an Excel file.
        """
        self.driver.get("https://www.latimes.com/")
        output_dir = r"output/images"
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
            os.mkdir(output_dir)
        else:
            os.mkdir(output_dir)
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
    """
    Get the search phrase from the Robocorp work item input.
    If no search phrase is provided, default to "food".
    """
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
