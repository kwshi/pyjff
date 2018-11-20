import parser
import argparse
import functools as ft
import collections as co
import pprint as pp
import itertools as it


argument_parser = argparse.ArgumentParser()
argument_parser.add_argument("jff_path", metavar="jff-file", type=str)
args = argument_parser.parse_args()

_original = co.namedtuple('original', ('symbol',))
_term = co.namedtuple('term', ('symbol',))
_bin = co.namedtuple('bin', ('string',))
_start = co.namedtuple('start', ())


def _parse_rule(rule):
    tag, leaf, (
        (left_tag, left_leaf, left),
        (right_tag, right_leaf, right),
    ) = rule

    assert tag == "production"
    assert not leaf

    assert left_tag == "left"
    assert left_leaf

    assert right_tag == "right"
    assert right_leaf

    return left, right


def _parse_grammar(structure):
    structure_type, body = structure
    assert structure_type == "grammar"

    rules = {}
    for left, target in map(_parse_rule, body):
        assert len(left) == 1

        if left not in rules:
            rules[left] = set()

        if target is None:
            rules[left].add(())
            continue

        rules[left].add(tuple(target))

    return rules


def _copy_rules(rules):
    return {left: set(targets) for left, targets in rules.items()}


def _chomsky_normalize_rename(rules):
    return {
        ("original", left): {
            tuple(("original", symbol) for symbol in target)
            for target in targets
        }
        for left, targets in rules.items()
    }


def _chomsky_normalize_start(rules, start):

    new_rules = {**rules, ('start',): {(start,)}}
    _copy_rules(rules)
    new_rules['start', ] = {(start,)}

    return new_rules


def _compute_symbols(rules):
    symbols = set()
    for source, targets in rules.items():
        for target in targets:
            symbols |= set(target)

    return symbols


def _chomsky_normalize_term(rules):

    new_rules = {
        source: {
            tuple(
                ("term", symbol) if symbol not in rules else symbol
                for symbol in target
            )
            for target in targets
        }
        for source, targets in rules.items()
    }
    for symbol in _compute_symbols(rules) - set(rules.keys()):
        new_rules[("term", symbol)] = {(symbol,)}

    return new_rules


def _chomsky_normalize_bin(rules):

    new_rules = {}
    for source, targets in rules.items():
        new_rules[source] = set()
        for target in targets:

            if len(target) <= 2:
                new_rules[source].add(target)
                continue

            new_rules[source].add((target[0], ("bin", target[1:])))
            for symbol_i, symbol in enumerate(target[1:-2], start=1):

                new_rules["bin", target[symbol_i:]] = {
                    (symbol, ("bin", target[symbol_i + 1:]))
                }

            new_rules["bin", target[-2:]] = {target[-2:]}

    return new_rules


def _inline_nullable(string, symbol):
    if symbol not in string:
        yield string
        return

    index = string.index(symbol)
    for rest in _inline_nullable(string[index + 1:], symbol):
        yield string[:index] + rest
        yield string[: index + 1] + rest


def _chomsky_normalize_del(rules):

    nullables = set()
    new_nullables = True
    while new_nullables:
        new_nullables = False
        for source, targets in rules.items():
            if source in nullables:
                continue

            for target in targets:
                nullable = True
                for symbol in target:
                    if symbol not in nullables:
                        nullable = False
                        break
                if nullable:
                    nullables.add(source)
                    new_nullables = True
                    break

    new_rules = _copy_rules(rules)
    for source, targets in rules.items():
        for target in targets:
            for nullable in set(target) & nullables:
                for new_target in _inline_nullable(target, nullable):
                    new_rules[source].add(new_target)

    for source in nullables:
        new_rules[source].discard(())

    return new_rules


def _chomsky_normalize_unit_for_symbol(rules, source, seen=set()):
    for target in rules[source]:
        if not (len(target) == 1 and target[0] in rules):
            yield target
            continue

        for symbol in target:
            if symbol in seen:
                continue

            yield from _chomsky_normalize_unit_for_symbol(
                rules, symbol, seen | {source}
            )


def _chomsky_normalize_unit(rules):
    return {
        source: set(_chomsky_normalize_unit_for_symbol(rules, source))
        for source in rules
    }


def _chomsky_normalize(rules, start):
    return _chomsky_normalize_prettify(
        _chomsky_normalize_unit(
            _chomsky_normalize_del(
                _chomsky_normalize_bin(
                    _chomsky_normalize_term(
                        _chomsky_normalize_start(
                            _chomsky_normalize_rename(rules), start
                        )
                    )
                )
            )
        )
    )


def _prettify_symbol(symbol):
    symbol_type, *args = symbol
    if symbol_type == "original":
        return args[0]
    elif symbol_type == "term":
        return "T{}".format(_prettify_symbol(args[0]))
    elif symbol_type == "start":
        return "start"
    elif symbol_type == "bin":
        return tuple(map(_prettify_symbol, args[0]))
    return symbol


def _chomsky_normalize_prettify(rules):
    return {
        _prettify_symbol(source): {
            tuple(_prettify_symbol(symbol) for symbol in target)
            for target in targets
        }
        for source, targets in rules.items()
    }


def _cyk_products(rules, string):
    singles = co.defaultdict(set)
    pairs = co.defaultdict(set)
    for source, targets in rules.items():
        for target in targets:
            (singles if len(target) == 1 else pairs)[source].add(
                target
            )

    products = co.defaultdict(lambda: co.defaultdict(set))
    for source, targets in singles.items():
        for target in targets:
            products[source][target].add(target)

    for substring_length in range(2, len(string) + 1):
        for position in range(len(string) - substring_length + 1):
            substring = string[position: position + substring_length]
            for split in range(1, substring_length):
                left_string, right_string = (
                    substring[:split],
                    substring[split:],
                )
                for source, targets in pairs.items():
                    for left, right in targets:
                        if (
                            left_string in products[left]
                            and right_string in products[right]
                        ):
                            for left_tree, right_tree in it.product(
                                products[left][left_string],
                                products[right][right_string],
                            ):

                                products[source][substring].add(
                                    (
                                        (left, left_tree),
                                        (right, right_tree),
                                    )
                                )

    return products


def _cyk(rules, string, start):
    for tree in _cyk_products(rules, string)[start][string]:
        yield start, tree


def _format_parse_tree_lines(tree):
    node, children = tree

    if len(children) == 1:
        yield "{!r},".format((node, children))
        return

    node, (left, right) = tree
    head = "({!r}, ".format(node)
    left_lines = _format_parse_tree_lines(left)
    yield head + next(left_lines)
    for line in left_lines:
        yield " " * len(head) + line
    for line in _format_parse_tree_lines(right):
        yield " " * len(head) + line


def _format_parse_tree(tree):
    return "\n".join(_format_parse_tree_lines(tree))


cnf = _chomsky_normalize(
    _parse_grammar(parser._parse_jff_structure(args.jff_path)),
    ("original", "S"),
)

for tree in _cyk(cnf, tuple("000#100"), "S"):
    print(_format_parse_tree(tree))
