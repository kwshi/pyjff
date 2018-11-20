import lxml.etree as etree
import argparse


argument_parser = argparse.ArgumentParser()
argument_parser.add_argument('jff_path', metavar='jff-file', type=str)
args = argument_parser.parse_args()

with open(args.jff_path) as f:
    tree = etree.parse(f)
    root = tree.getroot()
    for element in root.getchildren():
        if element.tag == 'type':
            assert element.text == 'grammar'

        elif element.tag == 'production':
            pass
