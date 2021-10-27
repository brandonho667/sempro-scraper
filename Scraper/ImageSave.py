import json
import requests
from os.path import basename


with open('./datasets/PMC_Images.json') as json_file:
    data = json.load(json_file)
    for link in data:
        for fig in data[link]["figures"]:
            lnk = fig["link"] #, "./images/"+data[link]["title"]+"_"+fig["num"]
            print(lnk)
            with open("./images/pmc/"+ basename(lnk), "wb") as f:
                f.write(requests.get(lnk).content)

