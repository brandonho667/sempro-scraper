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
        body = []

        # def is_reference(tag):
        #     prev_neg = False
        #     if tag.previous_sibling:
        #         prev_neg = "-" == tag.previous_sibling.string
        #     is_ion = "+" in tag.getText()
        #     is_anion = "-" in tag.getText() or prev_neg
        #     return tag.name == "sup" and not (is_ion or is_anion)

        # # Take out the references, tables, and figures
        # [s.extract() for s in soup.find_all(is_reference)]
        # [s.extract() for s in soup.find_all("table")]
        # [s.extract() for s in soup.find_all("figure")]

        # article_sections = soup.find_all("div", class_='NLM_sec')

        # for section in article_sections:

        #     sectionTitle = section.find('h2')

        #     if sectionTitle:
        #         sectionTitle = section.find('h2').get_text()
        #     else:
        #         sectionTitle = "NO SECTION HEADER PROVIDED"

        #     paragraphs = section.find_all("div", class_="NLM_p")

        #     for i, paragraph in enumerate(paragraphs):
        #         paragraph_text = paragraph.get_text()
        #         body.append({"text": paragraph_text, "meta": {"section": sectionTitle, "paragraph": i + 1}})


        def is_number(s):
            try:
                float(s)
                return True
            except ValueError:
                return False
        moduli = {}
        c = 0
        for section in soup.find("div", {"class":"article_content-left"}).find_all():
            if section.name == "div" and "class" in section.attrs.keys():
                if "NLM_back" in section["class"]:
                    break
            sentences = tk.sent_tokenize(section.getText())
            for s in sentences:
                modulus = ""
                start = -1
                words = tk.word_tokenize(s)
                for i in range(len(words)):
                    if words[i] == "modulus":
                        modulus = words[i-1] + " " + words[i]
                        # print(words)
                    elif modulus != "" and start < 0 and is_number(words[i][-1]):
                        # print(words[i])
                        start = i
                    elif start > 0 and modulus != "" and "Pa" in words[i]:
                        if modulus in moduli.keys():
                            if ''.join(words[start:i+1]) in moduli.values():
                                continue
                            moduli[modulus+str(c)] = ''.join(words[start:i+1])
                            c+=1
                        else:
                            moduli[modulus] = ''.join(words[start:i+1])
                        print(modulus + ": " + ''.join(words[start:i+1]))
                        start = -1
                        modulus = ""
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
                if "SEM" in fig["caption"] or "modulus" in fig["caption"]:
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
