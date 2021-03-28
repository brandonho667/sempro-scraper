from paperscraper import PaperScraper
from selenium import webdriver
from bs4 import BeautifulSoup
import json
import pkg_resources

class JournalScraper:
    def __init__(self, webdriver_path=None):

        options = webdriver.ChromeOptions()
        options.add_argument('headless')

        webdriver_path = pkg_resources.resource_filename('paperscraper', 'webdrivers/chromedriver.exe')
       
        if webdriver_path is not None:
            self.webdriver_path = webdriver_path

        self.driver = webdriver.Chrome(webdriver_path, options=options)
        self.ps = PaperScraper()
    
    def get_ACS_links(self, search, pages):
        links = []
        driver = self.driver
        for p in range(0, pages):
            driver.get("https://pubs.acs.org/action/doSearch?AllField=%s&startPage=%s&pageSize=100" % (search, p))
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            for s in soup.find_all("div", {"class": "issue-item_metadata"}):
                links.append("https://pubs.acs.org" + s.find("a")["href"])
        return links
        
    def scrape_journals(self, search):
        paper_links = []
        paper_links += self.get_ACS_links(search, 1)
        print(paper_links)
        # add more to get more links
        journal_data = {}
        for l in paper_links:
            journal_data[l] = self.ps.extract_from_url(l)
        return journal_data

if __name__ == '__main__':
    js = JournalScraper()
    journal_data = js.scrape_journals("hydrogel sem")
    with open('data.txt', 'w') as outfile:
        json.dump(journal_data, outfile)
