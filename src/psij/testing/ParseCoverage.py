import xml.etree.ElementTree as ET


class ParseCoverage:
    def __init__(self):
        self.x = 4

    def parse(self, xmlfile):

        # create element tree object
        tree = ET.parse(xmlfile)

        # get root element
        root = tree.getroot()

        # iterate over all "class" elements
        for class_elem in root.iter('class'):
            # get the name and filename attributes
            class_name = class_elem.attrib['name']
            class_filename = class_elem.attrib['filename']

            # iterate over all "line" elements within the "class" element
            for line_elem in class_elem.iter('line'):
                # get the number and hits attributes
                line_number = line_elem.attrib['number']
                line_hits = line_elem.attrib['hits']

                # do something with the class name, filename, line number, and hits
                print(f"Class: {class_name}, Filename: {class_filename}, Line: {line_number}, Hits: {line_hits}")

        return ["hello", "cov"]