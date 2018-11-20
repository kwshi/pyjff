import lxml.etree as etree
import collections as co

xml_parser = etree.XMLParser(remove_comments=True)

Structure = co.namedtuple('Structure', ('type', 'body'))


def _parse_xml_tree(root):
    children = root.getchildren()
    if not children:
        return root.tag, True, root.text

    return root.tag, False, tuple(map(_parse_xml_tree, children))


def _parse_jff_xml(path):
    with open(path) as f:
        tree = etree.parse(f, xml_parser)
        root = tree.getroot()
        return _parse_xml_tree(root)


def _parse_jff_structure_type(root_children):
    for tag, leaf, children in root_children:
        if tag == 'type':
            assert leaf
            return children


def _parse_jff_structure_body(root_children):
    return tuple(child for child in root_children if child[0] != 'type')


def _parse_jff_structure(xml_tree):
    tag, root_leaf, root_children = xml_tree
    assert tag == 'structure'
    assert not root_leaf

    return Structure(_parse_jff_structure_type(root_children), _parse_jff_structure_body(root_children))


def parse_jff(path):
    return _parse_jff_structure(_parse_jff_xml(path))
