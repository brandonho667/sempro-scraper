from paperscraper import PaperScraper
from selenium import webdriver
from bs4 import BeautifulSoup
import json
import pkg_resources
import csv
import os

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

    def get_PMC_links(self, search, pages):
        links = []
        driver = self.driver
        driver.get("https://www.ncbi.nlm.nih.gov/pmc/?term=%s" % search)
        for p in range(0, pages):
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            for s in soup.find_all("div", {"class": "rprt"}):
                links.append("https://www.ncbi.nlm.nih.gov" + s.find("a")["href"])
            driver.find_element_by_xpath("//a[@title='Next page of results']").click()
        return links    
    
    def scrape_journals(self, search, filename):
        paper_links = []
        # paper_links = ["https://pubs.acs.org/doi/10.1021/acsami.5b00184"]
        paper_links += self.get_ACS_links(search, 2)
        # paper_links += self.get_PMC_links(search, 5)
        # paper_links += self.get_PMC_links(search, 1)
        print(paper_links)
        # add more to get more links
        journal_data = {}
        header = ['link', 'title', 'num', 'letter', 'hydrogel', 'sentence', 'image']
        with open(filename, 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(header)
        for l in paper_links:
            link_data = self.ps.extract_from_url(l)
            if 'figures' in link_data and link_data['figures']: #  or len(link_data["body"]) > 0
                rows = []
                for fig in link_data['figures']:
                    for sub in fig['SEM']:
                        rows.append([l, link_data['title'],fig['num'], sub['fig_num'], sub['gel'], sub['sentence'], fig['link']])
                with open(filename, 'a+', newline='', encoding="utf-8") as csvfile:
                    csvwriter = csv.writer(csvfile)
                    for r in rows:
                        csvwriter.writerow(r)
            if 'support' in link_data and link_data['support']:
                rows = []
                for fig in link_data['support']:
                    if 'SEM' in fig:
                        for sub in fig['SEM']:
                            rows.append([l, link_data['title'],fig['num'], sub['fig_num'], sub['gel'], sub['sentence'], fig['link']])
                with open(filename, 'a+', newline='', encoding="utf-8") as csvfile:
                    csvwriter = csv.writer(csvfile)
                    for r in rows:
                        csvwriter.writerow(r)
                # journal_data[l] = link_data
        # return journal_data

if __name__ == '__main__':
    js = JournalScraper()
    if not os.path.exists("./sem"):
        os.makedirs("./sem")
    journal_data = js.scrape_journals("hydrogel sem", './test.csv')
    # with open('./datasets/test_figures.json', 'w') as outfile:
    #     json.dump(journal_data, outfile)
