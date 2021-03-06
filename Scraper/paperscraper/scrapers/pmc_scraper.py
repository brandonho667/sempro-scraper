from paperscraper.scrapers.base.base_scraper import BaseScraper
import nltk.tokenize as tk

"""A scraper of a PMC articles"""


class PMC(BaseScraper):

    def __init__(self, driver):
        self.driver = driver
        self.website = ["ncbi.nlm.nih.gov"]

    def get_authors(self, soup):
        author_links = soup.find("div", {"class": "contrib-group fm-author"}).findAll("a")
        authors = {}

        for i in range(len(author_links)):
            authors['a' + str(i + 1)] = {'last_name': author_links[i].contents[0].split(" ")[-1],
                                         'first_name': author_links[i].contents[0].split(" ")[0]}

        return authors

    def get_abstract(self, soup):
        # TODO get working
        pass
        # abstract = soup.find("div", id=lambda x: x and x.startswith('__abstract'))
        # print(abstract)
        # print(soup.find("p", id="__p1"))
        # [tag.unwrap() for tag in abstract.findAll(["em", "i", "b", "sub", "sup"])]
        # return abstract.find("p").contents[0]

    def get_body(self, soup):
        def is_number(s):
            try:
                float(s)
                return True
            except ValueError:
                return False
        moduli = []
        for section in soup.find("div", {"class":"jig-ncbiinpagenav"}).find_all():
            if "Acknowledgments" in section.getText():
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
                        mod_pair = {"modulus": modulus, "measurement": ''.join(words[start:i+1])}
                        if mod_pair in moduli:
                            continue
                        else:
                            moduli.append(mod_pair)
                        # print(modulus + ": " + ''.join(words[start:i+1]))
                        start = -1
                        modulus = ""
                    # if start > 0 and not (words[i].isdigit() or words[i] == "??"):
                    #     start = -1
                    #     modulus = ""
        return moduli

    def get_doi(self, soup):
        return soup.find("span", {"class": "doi"}).find("a").getText()
    
    def get_figures(self, soup):
        figures = []
        for s in soup.find_all("div", {"class": "fig iconblock whole_rhythm"}):
            fig = {}
            caption = s.find("div", {"class": "caption"})
            image = s.find("img", {"class": "tileshop"})
            if caption and image:
                fig["link"] = "https://www.ncbi.nlm.nih.gov" + image["src"]
                # fig["caption"] = caption.get_text()
                if fig not in figures and "SEM" in caption.get_text():
                    figures.append(fig)
        return figures

    def get_keywords(self, soup):
        keywords = soup.find("span", {"class": "kwd-text"})
        [tag.unwrap() for tag in keywords.findAll(["em", "i", "b", "sub", "sup"])]
        return keywords.getText().split(", ")

    def get_pdf_url(self, soup):
        return "https://www.ncbi.nlm.nih.gov/" + soup.find("div", {"class": "format-menu"}).findAll("li")[3].find("a")[
            'href']

    def get_title(self, soup):
        return soup.find("h1", {"class": "content-title"}).getText()

    def get_support(self, soup):
        pass
