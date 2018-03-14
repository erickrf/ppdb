# -*- coding: utf-8 -*-

from __future__ import division, print_function, unicode_literals

"""
Classes and functions for dealing with data from the paraphrase database (PPDB)
"""

from six import string_types
from six.moves import cPickle


_ppdb_dict = None


class TransformationDict(dict):
    """
    Class storing a dictionary for phrasal, lexical and/or syntactic
    transformations.
    """
    def __init__(self):
        """
        Well, init the object.
        """
        # each key in self is a token, and each value is a tuple (set, dict).
        super(TransformationDict, self).__init__()

        # this indexes words in the middle of a RHS rule
        # ex: self.index[word1] == {(word2, word3): RHS-continuing-in-word1}
        # where RHS-continuing-in-word1 is a nested entry in self
        # ignore the above. now each key maps into (before, after) in the LHS
        # rules the key is part of
        self.index = {}

    def add(self, lhs, rhs):
        """
        Add a transformation rule.

        :param lhs: left-hand side, tuple of strings
        :param rhs: left-hand side, tuple of strings
        """
        d = self
        if len(lhs) == 0:
            return

        # this keeps track of the LHS before each new token
        # partial_lhs = []

        for i, token in enumerate(lhs):
            if token in d:
                rule_set, d = d[token]
            else:
                rule_set = set()
                new_d = TransformationDict()
                d[token] = (rule_set, new_d)
                d = new_d

            # if len(partial_lhs):
            #     self.index[token][tuple(partial_lhs)] = d
            if 0 < i < len(lhs) - 1:
                if token not in self.index:
                    self.index[token] = set()
                before = tuple(lhs[:i])
                after = tuple(lhs[i+1:])
                self.index[token].add((before, after))
            # partial_lhs.append(token)

        rule_set.add(rhs)

    def find_partial_expression(self, partial):
        """
        Look for a partial LHS rule.

        It looks for LHS rules with the given partial inside, but not at the
        beginning.

        :param partial: tuple of strings
        :return: a list of context tuples (before, after).
            before and after are tuples with the other tokens in the LHS.
        """
        first_token = partial[0]
        if first_token not in self.index:
            return []

        def find_all_paths(d):
            paths = []
            for key in d:
                paths_under_key = [[key] + path
                                   for path in find_all_paths(d[key][1])]

                if len(paths_under_key) == 0:
                    paths_under_key = [[key]]
                paths.extend(paths_under_key)

            return paths

        sought_lhs_tail = tuple(partial[1:])
        contexts = []
        lhs_heads = [head for head, tail in self.index[first_token]
                     if tail[:len(sought_lhs_tail) + 1] == sought_lhs_tail]
        for lhs_head in lhs_heads:
            # d contains transformations with "lhs_head" + "first_token"
            # we know lhs_tail is also contained here
            d = self[lhs_head][1][first_token][1]

            for token in sought_lhs_tail:
                d = d[token][1]

            # explore all paths in d to complete the LHS in a depth-first search
            contexts_after = find_all_paths(d)
            contexts.extend([(lhs_head, context_after)
                             for context_after in contexts_after])

        return contexts

    def get_rhs(self, lhs):
        """
        Return the right-hand side of the rules with the given left-hand side.

        :param lhs: tuple/list of strings
        :return: a set with all the fillers of the right-hand side of the rule
        """
        return self[lhs][0]

    def __getitem__(self, lhs):
        if isinstance(lhs, string_types):
            if lhs in self:
                return super(TransformationDict, self).__getitem__(lhs)
            return set(), TransformationDict()

        d = self
        for token in lhs:
            if token not in d:
                return set(), TransformationDict()

            rule_set, d = d[token]

        return rule_set, d

    def get_subdict(self, lhs):
        """
        Return the TransformationDict associated with the given lhs
        """
        return self[lhs][1]


def load_ppdb(path, is_trivial=lambda e1, e2: False,
              clean_expression=lambda x: x, force=False):
    """
    Load a paraphrase file from Paraphrase Database.

    A call to this function is necessary before using the other ones in this
    module. Calls after the module has been loaded have no effect, unless force
    is True.

    :param path: path to the file
    :param is_trivial: a function that takes two lists of strings (the LHS and
        RHS of the rule) and returns whether this is a trivial rule that should
        be ignored.
    :param clean_expression: a function that takes a list of strings (either the
        RHS or LHS of a rule) and cleans it, usually removing articles.
    :param force: if False and the dictionary is already loaded, do nothing.
        If True, always load the dictionary.
    :return: a nested dictionary containing transformations.
        each level of the dictionary has one token of the right-hand side of
        the transformation rule mapping to a tuple (transformations, dict):
        ex:
        {'poder': (set(),
                   {'legislativo': (set('legislatura',
                                    {})})
        }
    """
    global _ppdb_dict
    if _ppdb_dict is not None and not force:
        return _ppdb_dict

    if path.endswith('.pickle'):
        with open(path, 'rb') as f:
            _ppdb_dict = cPickle.load(f)
        return _ppdb_dict

    transformations = TransformationDict()

    with open(path, 'rb') as f:
        for line in f:
            line = line.decode('utf-8')
            # discard lines with unrecoverable encoding errors
            if '\\ x' in line or 'xc3' in line:
                continue
            fields = line.split('|||')
            lhs = fields[1].strip().split()
            rhs = fields[2].strip().split()

            lhs = tuple(clean_expression(lhs))
            rhs = tuple(clean_expression(rhs))

            if len(lhs) == 0 or len(rhs) == 0:
                continue

            # filter out trivial number/gender variations
            if is_trivial(lhs, rhs):
                continue

            # add rhs to the transformation dictionary
            transformations.add(lhs, rhs)

    _ppdb_dict = transformations

    return transformations


def search(haystack, needle):
    """
    Search list `haystack` for sublist `needle` using Boyer-Moore algorithm.
    """
    if len(needle) == 0:
        return 0
    char_table = make_char_table(needle)
    offset_table = make_offset_table(needle)
    i = len(needle) - 1
    while i < len(haystack):
        j = len(needle) - 1
        while needle[j] == haystack[i]:
            if j == 0:
                return i
            i -= 1
            j -= 1
        i += max(offset_table[len(needle) - 1 - j],
                 char_table.get(haystack[i], -1))
    return -1


def make_char_table(needle):
    """
    Makes the jump table based on the mismatched character information.
    """
    table = {}
    for i in range(len(needle) - 1):
        table[needle[i]] = len(needle) - 1 - i
    return table


def make_offset_table(needle):
    """
    Makes the jump table based on the scan offset in which mismatch occurs.
    """
    table = []
    last_prefix_position = len(needle)
    for i in reversed(range(len(needle))):
        if is_prefix(needle, i + 1):
            last_prefix_position = i + 1
        table.append(last_prefix_position - i + len(needle) - 1)
    for i in range(len(needle) - 1):
        slen = suffix_length(needle, i)
        table[slen] = len(needle) - 1 - i + slen
    return table


def is_prefix(needle, p):
    """
    Is needle[p:end] a prefix of needle?
    """
    j = 0
    for i in range(p, len(needle)):
        if needle[i] != needle[j]:
            return 0
        j += 1
    return 1


def suffix_length(needle, p):
    """
    Returns the maximum length of the substring ending at p that is a suffix.
    """
    length = 0
    j = len(needle) - 1
    for i in reversed(range(p + 1)):
        if needle[i] == needle[j]:
            length += 1
        else:
            break
        j -= 1

    return length


def get_rhs(lhs):
    """
    Return the possible RHS of a given LHS.

    :param lhs: token or list of tokens
    :return: list of tuples
    """
    return _ppdb_dict.get_rhs(lhs)
