import re
import urllib
from pdf2image import convert_from_bytes
# from PyPDF2.pdf import PdfFileReader
# from PyPDF2.utils import PdfReadError
from tika import parser
# import pdfplumber
from numpy.lib.type_check import imag
import requests
# import fitz # PyMuPDF
import io
from PIL import Image
# import PyPDF2
import nltk.tokenize as tk
from paperscraper.scrapers.base.base_scraper import BaseScraper
from paperscraper.scrapers.sem_scraper import detect_sem
import os

"""A scraper for American Chemical Society (ACS) articles"""

class ACS(BaseScraper):
    
    def __init__(self, driver):
        self.driver = driver
        self.website = ["pubs.acs.org"]
        self.metadata = None
        self.fig_nums = set()
        self.keygels = set()

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

    def is_number(self, s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    def get_body(self, soup):
        # print("keygels: ", self.keygels)
        moduli = []
        accept = ["~", "±", "to", "and", "Pa"]
        modulus_types = ["compressive", "young’s", "storage", "tensile", "elastic", "shear"]
        # print(self.fig_labels)
        for section in soup.find("div", {"class":"article_content-left"}).find_all():
            if section.name == "div" and "class" in section.attrs.keys():
                if "NLM_back" in section["class"]:
                    break
            # if not any([fig in section.getText() for fig in self.fig_labels]):
            #     print(section.getText())
            #     continue
            sentences = tk.sent_tokenize(section.getText())
            modulus = ""
            modFound = False
            for s in sentences:
                if "modulus" not in s and "moduli" not in s:
                    continue
                start = -1
                words = tk.word_tokenize(s)

                curr_gel = []
                for w in words:
                    for system in self.keygels:
                        if system in w or w in system:
                            curr_gel.append(w)
                            break
                
                if len(curr_gel) == 0:
                    continue
                # scraping modulus
                for i in range(len(words)):
                    # one word modulus
                    if words[i].lower() in modulus_types:
                        modulus = words[i].lower() 
                    # young's modulus
                    if "".join(words[i:i+3]).lower() in modulus_types:
                        modulus = "".join(words[i:i+3]).lower() 
                    # if words[i] == "modulus" or words[i] == moduli:
                    #     modFound = True
                    if start < 0 and self.is_number(words[i][-1]):
                        start = i
                    elif start > 0 and not self.is_number(words[i][-1]) and not any([a in words[i] for a in accept]):
                        start = -1
                    if start > 0 and len(curr_gel) > 0 and modulus != "" and "Pa" in words[i]:
                        measure = ''.join(words[start:i+1])
                        mod_pair = {"gel": curr_gel.pop(0), "modulus": modulus, "measurement": measure, "sentence": s}
                        # modFound = False
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

    def get_proper(self, sent):
        words = sent.split(" ")
        proper = []
        puncs = [",", ".", ";"]
        for i in range(len(words)):
            w = words[i]
            if self.is_number(w):
                proper.append(w)
            elif len(w) > 1 and any([w[i].isupper() for i in range(1, len(w))]) and "SEM" not in w and "TEM" not in w:
                proper.append(w)
            if "hydrogel" in w:
                # if words[i-1] not in proper and words[i-1].lower() != "the":
                #     proper.append(words[i-1])
                break
        for p in proper:
            if len(p) > 0 and p[-1] in puncs:
                p = p[:-1]
        return " ".join(proper)

    def check_valid_label(self, label):
        splitter = ""
        if ", " in label:
            splitter = ", "
        elif "-" in label:
            splitter = "-"
        else:
            splitter = ","
        sub_figs = label.split(splitter)
        for sf in sub_figs:
            if len(sf) > 2:
                return False
        return True

    def split_cap(self, cap_sent):
        process_cap = {}
        for sent in cap_sent:
            if "SEM" not in sent or "hydrogel" not in sent:
                continue
            res = sent.split("(")
            # print(res)
            sub = 0
            while sub < len(res):
                # print(res[sub])
                if ")" not in res[sub]:
                    sub += 1
                    continue
                split_sub = res[sub].split(")")
                # print(split_sub)
                label = split_sub[0]
                if sub > 0 and not self.check_valid_label(label):
                    res[sub-1:sub+1] = ["".join(res[sub-1:sub+1])]
                    sub -= 1
                    split_sub = res[sub].split(")")
                    # print("recombination")
                    # print(split_sub)
                    label = split_sub[0]
                gel = "".join(split_sub[1:])
                process_cap[label] = gel
                sub+=1
        return process_cap

    def get_figures(self, soup):
        figures = []
        doi = self.get_doi(soup).replace('/', '_')
        for s in soup.find_all("figure", {"class": "article__inlineFigure"}):
            fig_num = s.find("h2", {"class": "fig-label"})
            fig = {}
            caption = s.find("figcaption")
            backup = s.find('img')
            image = s.find("a", {"title": "High Resolution Image"})
            lnk = "https://pubs.acs.org"

            if image and backup:
                if requests.get(lnk+image['href']).status_code != 200:
                    if requests.get(lnk+backup['src']).status_code != 200:
                        continue
                    else:
                        lnk += backup['src']
                else:
                    lnk += image['href']
            else:
                continue
            if fig_num and caption and image and fig_num.getText() not in self.fig_nums:
                self.fig_nums.add(fig_num.getText())
                fig["num"] = fig_num.getText()
                # fig["caption"] = caption.getText()
                fig["SEM"] = []
                if "SEM" in caption.getText():
                    images_dir = os.path.join('sem/', doi)
                    if not os.path.exists(images_dir):
                        os.mkdir(images_dir)
                    content = requests.get(lnk).content
                    file_n = os.path.basename(lnk)
                    file_split = os.path.splitext(file_n)
                    if file_split[1] == '.gif':
                        file_n = os.path.splitext(file_n)[0]+'.jpeg'
                        im = Image.open(io.BytesIO(content))
                        im.save(os.path.join(images_dir, file_n))
                    else:
                        with open(os.path.join(images_dir, file_n), "wb") as f:
                            f.write(content)
                    fig['link'] = '=HYPERLINK(\"'+os.path.join(images_dir, os.path.basename(lnk))+'\",\"img_folder\")'
                    SEM_dir = os.path.join(images_dir, 'SEM')
                    if not os.path.exists(SEM_dir):
                        os.mkdir(SEM_dir)
                    detect_sem(source=images_dir,imgsz=416,conf_thres=0.75)
                    # This part is for actual acquisition:
                    
                    cap_sent = tk.sent_tokenize(caption.getText())
                    
                    cap_sent = self.split_cap(cap_sent)

                    for label in cap_sent.keys():
                        gel = self.get_proper(cap_sent[label])
                            
                        # print(gel + ": " + label)

                        if gel != "" and label != "":
                            fig["SEM"].append({"fig_num": label, "gel": gel, "sentence":cap_sent[label]})
                            gel = gel.split(" ")
                            for el in gel:
                                if el != "" and el[0] != "m" and not self.is_number(el):
                                    self.keygels.add(el)
                    
                    # just get the image
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

    def text_pages(self, file):
        raw_xml = parser.from_buffer(file, xmlContent=True)
        body = raw_xml['content'].split('<body>')[1].split('</body>')[0]
        body_without_tag = body.replace("<p>", "").replace("</p>", "").replace("<div>", "").replace("</div>","").replace("<p />","")
        text_pages = body_without_tag.split("""<div class="page">""")[1:]
        num_pages = len(text_pages)
        if num_pages==int(raw_xml['metadata']['xmpTPg:NPages']) : #check if it worked correctly
            return text_pages

    def get_support(self, soup):
        try:
            pdf_url = "https://pubs.acs.org" + \
                soup.find("a", {"class": "suppl-anchor"})['href']
        except:
            return None
        print("pdf_url: " + pdf_url)
        file_n = os.path.basename(pdf_url)
        file_split = os.path.splitext(file_n)
        if file_split[1] != ".pdf":
            return None
        s = requests.Session()    
        r = s.get(pdf_url, stream=True)
        cookies = dict(r.cookies)
        r = s.post(pdf_url, 
            cookies=cookies)
        f = io.BytesIO(r.content)

        # print(pdf_url)

        # req = urllib.request.Request(pdf_url)
        # f = io.StringIO(urllib.request.urlopen(req).read())
        pdf = self.text_pages(f)
        if not pdf:
            return
        image_reader = convert_from_bytes(r.content)
        supp_figures = []
        for i in range(len(pdf)):
            text = pdf[i]
            # print("Page %d text: %s" % (i, text))
            # images = image_reader[i].getImageList()
            im = image_reader[i]
            doi = self.get_doi(soup).replace('/', '_')
            # images_dir = os.path.join('sem/', doi)
            modulus_key = ["rheology", "modulus", "moduli", "compressive", "young’s", "storage", "tensile", "elastic", "shear"]
            if not text or \
                ("SEM" not in text and not any(m in text for m in modulus_key)):
                continue
            doi = self.get_doi(soup).replace('/', '_')
            images_dir = "sem/%s/supp" % doi
            if not os.path.exists(images_dir):
                os.makedirs(images_dir)
            im_name = "supp_%d.jpg" % i
            im.save(os.path.join(images_dir, im_name))

            captions = text.split("Figure ")
            for c in captions:
                fig = {}
                fig["link"] = '=HYPERLINK(\"'+os.path.join(images_dir, im_name)+'\",\"sup_img\")'
                if "SEM" in c:
                    fig["SEM"] = []
                    SEM_dir = os.path.join(images_dir, 'SEM')
                    if not os.path.exists(SEM_dir):
                        os.mkdir(SEM_dir)
                    detect_sem(source=images_dir,imgsz=416,conf_thres=0.75)
                    
                    cap_sent = tk.sent_tokenize(c)
                    # print("tokenize: %s" % cap_sent)
                    fig["num"] = cap_sent.pop(0)
                    cap_sent = self.split_cap(cap_sent)
                    # print("split: %s" % cap_sent)
                    if not cap_sent:
                        continue

                    for label in cap_sent.keys():
                        gel = self.get_proper(cap_sent[label])
                            
                        # print(gel + ": " + label)

                        if gel != "" and label != "":
                            fig["SEM"].append({"fig_num": label, "gel": gel, "sentence":cap_sent[label]})
                            gel = gel.split(" ")
                            for el in gel:
                                if el != "" and el[0] != "m" and not self.is_number(el):
                                    self.keygels.add(el)
                fig['modulus'] = []
                if any(m in c for m in modulus_key):
                    words = tk.word_tokenize(c)
                    curr_gel = []
                    modulus = []
                    for w in words:
                        for system in self.keygels:
                            if system in w or w in system:
                                curr_gel.append(w)
                                break
                    for m in modulus_key:
                        if m in c:
                            modulus.append(m)
                    fig['modulus'].append({"gel": ", ".join(curr_gel), "moduli": ", ".join(modulus)})
                if fig:
                    supp_figures.append(fig)

        return supp_figures

