import lxml.etree as etree


xml_parser = etree.XMLParser(remove_comments=True)


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


def _parse_jff_structure(path):
    tag, root_leaf, root_children = _parse_jff_xml(path)
    assert tag == 'structure'
    assert not root_leaf

    structure_type = _parse_jff_structure_type(root_children)
    body = _parse_jff_structure_body(root_children)

    return structure_type, body
