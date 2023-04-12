import xml.etree.ElementTree as ET


class ParseCoverage:
    def __init__(self):
        self.x = 4

    def parse(self, xmlfile):

        # create element tree object
        tree = ET.parse(xmlfile)

        # get root element
        root = tree.getroot()

        # create empty list for news items
        newsitems = []
        return ["hello", "cov"]