#from . import grammar
from . import grammar
from . import jff_parser

_structure_type_modules = {
    'grammar': grammar,
}


class NotYetSupported(Exception):
    def __init__(self, structure_type):
        self.structure_type = structure_type
        self.message = 'JFLAP structure type {} not yet supported in pyjff'.format(
            structure_type)


def run(structure):

    if structure.type not in _structure_type_modules:
        raise NotYetSupported(structure.type)

    structure_module = _structure_type_modules[structure.type]
    return structure_module.run(structure_module.parse(structure))


def parse_and_run(path):
    return run(jff_parser.parse_jff(path))
