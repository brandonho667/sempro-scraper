from collections import OrderedDict
from pprint import pprint
from unittest import TestCase
import unittest
import json
from paperscraper import PaperScraper


class TestACS(TestCase):
    TEST_URL = "https://pubs.acs.org/doi/10.1021/acsami.8b06804"

    @classmethod
    def setUpClass(cls):
        cls.scraper = PaperScraper()

    @classmethod
    def tearDownClass(cls):
        cls.scraper.__exit__(None, None, None)

    def test_valid_extraction_1(self):
        scraper = self.scraper

        if scraper.is_scrapable(self.TEST_URL):
            # pprint(dict(scraper.extract_from_url(self.TEST_URL)))
            with open('data.txt', 'w') as outfile:
                json.dump(scraper.extract_from_url(self.TEST_URL), outfile)
            self.assertIsInstance(scraper.extract_from_url(self.TEST_URL), OrderedDict)

    # def test_valid_extraction_2(self):
    #     scraper = self.scraper

    #     if scraper.is_scrapable(self.TEST_URL):
    #         pprint(dict(scraper.extract_from_url(self.TEST_URL)))
    #         self.assertIsInstance(scraper.extract_from_url(self.TEST_URL), OrderedDict)

if __name__ == '__main__':
    unittest.main()

