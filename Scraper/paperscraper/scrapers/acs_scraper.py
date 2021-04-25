import re
import nltk.tokenize as tk
from paperscraper.scrapers.base.base_scraper import BaseScraper

"""A scraper for American Chemical Society (ACS) articles"""


class ACS(BaseScraper):
    
    def __init__(self, driver):
        self.driver = driver
        self.website = ["pubs.acs.org"]
        self.metadata = None
        self.SEM = 0
        self.mech = 0

    def get_authors(self, soup):
        if self.metadata is None:
            self.metadata = eval(soup.find("input", {"name": "meta-data"}).get("value"))
        authors = self.metadata["authors"]
        # print(authors)
        # authors = {}

        # for i in range(len(author_links)):
        #     authors['a' + str(i + 1)] = {'last_name': author_links[i].contents[0].split(" ")[-1],
        #                                  'first_name': author_links[i].contents[0].split(" ")[0]}

        return authors

    def get_abstract(self, soup):
        if self.metadata is None:
            self.metadata = eval(soup.find("input", {"name": "meta-data"}).get("value"))
        return soup.find("p", {'class': 'articleBody_abstractText'}).getText()

    def get_body(self, soup):
        def is_number(s):
            try:
                float(s)
                return True
            except ValueError:
                return False
        moduli = []
        accept = ["~", "±", "to", "and", "Pa"]
        for section in soup.find("div", {"class":"article_content-left"}).find_all():
            if section.name == "div" and "class" in section.attrs.keys():
                if "NLM_back" in section["class"]:
                    break
            sentences = tk.sent_tokenize(section.getText())
            for s in sentences:
                if "Pa" not in s:
                    continue
                modulus = ""
                start = -1
                words = tk.word_tokenize(s)
                for i in range(len(words)):
                    if words[i] == "modulus":
                        modulus = words[i-1] + " " + words[i]
                    if start < 0 and is_number(words[i][-1]):
                        start = i
                    elif start > 0 and not is_number(words[i][-1]) and not any([a in words[i] for a in accept]):
                        start = -1
                    if start > 0 and modulus != "" and "Pa" in words[i]:
                        measure = ''.join(words[start:i+1])
                        mod_pair = {"modulus": modulus, "measurement": measure}
                        if mod_pair in moduli:
                            continue
                        else:
                            moduli.append(mod_pair)
                        # print(modulus + ": " + ''.join(words[start:i+1]))
                        start = -1
                    # if start > 0 and not (words[i].isdigit() or words[i] == "±"):
                    #     start = -1
                    #     modulus = ""
        return moduli

    def get_doi(self, soup):
        if self.metadata is None:
            self.metadata = eval(soup.find("input", {"name": "meta-data"}).get("value"))
        return self.metadata["identifiers"]["doi"]

    def get_figures(self, soup):

        figures = []
        for s in soup.find_all("figure", {"class": "article__inlineFigure"}):
            fig = {}
            caption = s.find("figcaption")
            image = s.find("a", {"title": "High Resolution Image"})
            if caption and image:
                fig["link"] = image["href"]
                fig["caption"] = caption.get_text()
                if fig not in figures and ("SEM" in fig["caption"] or "modulus" in fig["caption"]):
                    figures.append(fig)

        return figures

    """ Used to get the keywords from the article
    
    There are no keywords provided for ACS Articles. Still looking for equivalent.
    """

    def get_keywords(self, soup):
        pass

    def get_pdf_url(self, soup):
        return "https://pubs.acs.org" + \
               soup.find("a", {"title": "PDF"})['href']

    def get_title(self, soup):
        return soup.find("span", {"class": "hlFld-Title"}).getText()
