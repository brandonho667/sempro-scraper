import time
from nltk.tokenize import sent_tokenize
from paperscraper import PaperScraper
from selenium import webdriver
from bs4 import BeautifulSoup
import json
import pkg_resources
import csv
import os
from selenium.webdriver.chrome.options import Options
import shutil
import tika
import random
tika.initVM()

class JournalScraper:
    def __init__(self, webdriver_path=None):

        options = webdriver.ChromeOptions()
        options.add_argument('headless')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_argument("--log-level=3")
        webdriver_path = pkg_resources.resource_filename('paperscraper', 'webdrivers/chromedriver.exe')
       
        if webdriver_path is not None:
            self.webdriver_path = webdriver_path
        self.driver = webdriver.Chrome(webdriver_path, options=options)
        self.ps = PaperScraper(self.driver)
    
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
    
    def is_scraped(self, link):
        filename = "_".join(link.split("/")[-2:])
        return os.path.isdir("./sem/"+ filename)

    def del_link(self, link):
        filename = "_".join(link.split("/")[-2:])
        if os.path.isdir("./sem/"+ filename):
            shutil.rmtree("./sem/"+ filename)

    def scrape_journals(self, search, filename, file_mod):
        count = 0
        t, n = 0, 0
        paper_links = []
        # paper_links = ["https://pubs.acs.org/doi/10.1021/ja044401g"]
        paper_links += self.get_ACS_links(search, 20)
        # paper_links += self.get_PMC_links(search, 5)
        # paper_links += self.get_PMC_links(search, 1)
        print("Scraping %d papers..." % len(paper_links))
        # add more to get more links
        journal_data = {}
        cache = open('cache').read().splitlines()
        if not os.path.exists("./"+filename):
            header = ['link', 'title', 'num', 'letter', 'hydrogel', 'sentence', 'figure', 'SEM']
            with open(filename, 'w', newline='') as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow(header)
        if not os.path.exists("./"+file_mod):
            mod_header = ['link', 'title', 'gel', 'modulus', 'sentence', 'measurement']
            with open(file_mod, 'w', newline='') as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow(mod_header)
        for i, l in enumerate(paper_links):
            print("Scraping paper %d: %s" % (i, l))
            if self.is_scraped(l) or l in cache:
                print(" -- Already checked, skipping")
                continue
            start = time.perf_counter()
            link_data = self.ps.extract_from_url(l)
            rows = []
            mod_rows = []
           
            if 'figures' in link_data and link_data['figures']: #  or len(link_data["body"]) > 0
                for fig in link_data['figures']:
                    if 'SEM' in fig:
                        for sub in fig['SEM']:
                            rows.append([l, link_data['title'],fig['num'], sub['fig_num'], sub['gel'], sub['sentence'], fig['link'], fig['folder']])
                    if 'modulus' in fig:
                        mod = fig['modulus']
                        mod_rows.append([l, link_data['title'],mod['gel'],mod['moduli'],mod['sentence'],fig['link']])
            if 'body' in link_data and link_data['body']:
                for mod in link_data['body']:
                    # print('adding:', mod)
                    mod_rows.append([l, link_data['title'],mod['gel'],mod['modulus'],mod['sentence'],mod['measurement']])

            if 'support' in link_data and link_data['support']:
                for fig in link_data['support']:
                    if 'SEM' in fig:
                        for sub in fig['SEM']:
                            rows.append([l, link_data['title'],fig['num'], sub['fig_num'], sub['gel'], sub['sentence'], fig['link'], fig['folder']])
                    if 'modulus' in fig:
                        for mod in fig['modulus']:
                            mod_rows.append([l, link_data['title'], mod['gel'], mod['moduli'], mod['sentence'], fig['link']])
            
            if len(rows) == 0 or len(mod_rows) == 0:
                print(' -- No SEM and/or modulus found for %s, adding to skip cache'%l)
                self.del_link(l)
                with open('cache', 'a') as file:
                    file.write(l+'\n')
                continue

            with open(filename, 'a+', newline='', encoding="utf-8") as csvfile:
                csvwriter = csv.writer(csvfile)
                for r in rows:
                    csvwriter.writerow(r)
            
            with open(file_mod, 'a+', newline='', encoding="utf-8") as csvfile:
                    csvwriter = csv.writer(csvfile)
                    for r in mod_rows:
                        csvwriter.writerow(r)
                # journal_data[l] = link_data
            elapsed = time.perf_counter() - start
            n += 1
            t += elapsed

            print(' -- scrape time:', elapsed)
            print(' -- cum ave:', t/n)
            time.sleep(random.randint(1,5))
            count += 1
            if count%200 == 0:
                # print("completed 200 scrapes, taking a break so i don't get caught by acs") 
                time.sleep(300)
                break

        # return journal_data

if __name__ == '__main__':
    js = JournalScraper()
    if not os.path.exists("./sem"):
        os.makedirs("./sem")
    journal_data = js.scrape_journals("hydrogel sem", './SEM.csv', './modulus.csv')
    # with open('./datasets/test_figures.json', 'w') as outfile:
    #     json.dump(journal_data, outfile)
