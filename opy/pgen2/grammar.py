# Copyright 2004-2005 Elemental Security, Inc. All Rights Reserved.
# Licensed to PSF under a Contributor Agreement.

"""This module defines the data structures used to represent a grammar.

These are a bit arcane because they are derived from the data
structures used by Python's 'pgen' parser generator.

There's also a table here mapping operators to their names in the
token module; the Python tokenize module reports all operators as the
fallback token code OP, but the parser needs the actual token code.

"""

# Python imports
import collections
import pickle
import marshal

from . import token


class Grammar(object):
    """Pgen parsing tables conversion class.

    Once initialized, this class supplies the grammar tables for the
    parsing engine implemented by parse.py.  The parsing engine
    accesses the instance variables directly.  The class here does not
    provide initialization of the tables; several subclasses exist to
    do this (see the conv and pgen modules).

    The load() method reads the tables from a pickle file, which is
    much faster than the other ways offered by subclasses.  The pickle
    file is written by calling dump() (after loading the grammar
    tables using a subclass).  The report() method prints a readable
    representation of the tables to stdout, for debugging.

    The instance variables are as follows:

    symbol2number -- a dict mapping symbol names to numbers.  Symbol
                     numbers are always 256 or higher, to distinguish
                     them from token numbers, which are between 0 and
                     255 (inclusive).

    number2symbol -- a dict mapping numbers to symbol names;
                     these two are each other's inverse.

    states        -- a list of DFAs, where each DFA is a list of
                     states, each state is a list of arcs, and each
                     arc is a (i, j) pair where i is a label and j is
                     a state number.  The DFA number is the index into
                     this list.  (This name is slightly confusing.)
                     Final states are represented by a special arc of
                     the form (0, j) where j is its own state number.

    dfas          -- a dict mapping symbol numbers to (DFA, first)
                     pairs, where DFA is an item from the states list
                     above, and first is a set of tokens that can
                     begin this grammar rule (represented by a dict
                     whose values are always 1).

    labels        -- a list of (x, y) pairs where x is either a token
                     number or a symbol number, and y is either None
                     or a string; the strings are keywords.  The label
                     number is the index in this list; label numbers
                     are used to mark state transitions (arcs) in the
                     DFAs.

    start         -- the number of the grammar's start symbol.

    keywords      -- a dict mapping keyword strings to arc labels.

    tokens        -- a dict mapping token numbers to arc labels.

    """

    def __init__(self):
        self.symbol2number = {}
        self.number2symbol = {}
        self.states = []
        self.dfas = {}
        self.labels = [(0, "EMPTY")]
        self.keywords = {}
        self.tokens = {}
        self.symbol2label = {}
        self.start = 256

    def dump(self, filename):
        """Dump the grammar tables to a pickle file.

        dump() recursively changes all dict to OrderedDict, so the pickled file
        is not exactly the same as what was passed in to dump(). load() uses the
        pickled file to create the tables, but  only changes OrderedDict to dict
        at the top level; it does not recursively change OrderedDict to dict.
        So, the loaded tables are different from the original tables that were
        passed to load() in that some of the OrderedDict (from the pickled file)
        are not changed back to dict. For parsing, this has no effect on
        performance because OrderedDict uses dict's __getitem__ with nothing in
        between.
        """
        with open(filename, "wb") as f:
            d = _make_deterministic(self.__dict__)
            pickle.dump(d, f, 2)  # protocol 2
            # d isn't marshallable.  But neither is self.__dict__.
            # Probably have to go through and marshal each member.
            #marshal.dump(self.__dict__, f)

            if 0:
              s = ''
              s += marshal.dumps(self.symbol2number)
              s += marshal.dumps(self.number2symbol)
              s += marshal.dumps(self.dfas)
              s += marshal.dumps(self.labels)
              s += marshal.dumps(self.keywords)
              s += marshal.dumps(self.tokens)
              s += marshal.dumps(self.symbol2label)
              s += marshal.dumps(self.start)
              print('Marshalled bytes: %d' % len(s))

    def load(self, f):
        d = pickle.load(f)
        self.__dict__.update(d)

    def copy(self):
        """
        Copy the grammar.
        """
        new = self.__class__()
        for dict_attr in ("symbol2number", "number2symbol", "dfas", "keywords",
                          "tokens", "symbol2label"):
            setattr(new, dict_attr, getattr(self, dict_attr).copy())
        new.labels = self.labels[:]
        new.states = self.states[:]
        new.start = self.start
        return new

    def report(self):
        """Dump the grammar tables to standard output, for debugging."""
        from pprint import pprint
        print("s2n")
        pprint(self.symbol2number)
        print("n2s")
        pprint(self.number2symbol)
        print("states")
        pprint(self.states)
        print("dfas")
        pprint(self.dfas)
        print("labels")
        pprint(self.labels)
        print("start", self.start)


def _make_deterministic(top):
    if isinstance(top, dict):
        return collections.OrderedDict(
            sorted(((k, _make_deterministic(v)) for k, v in top.items())))
    if isinstance(top, list):
        return [_make_deterministic(e) for e in top]
    if isinstance(top, tuple):
        return tuple(_make_deterministic(e) for e in top)
    return top


# Map from operator to number (since tokenize doesn't do this)

opmap_raw = """
( LPAR
) RPAR
[ LSQB
] RSQB
: COLON
, COMMA
; SEMI
+ PLUS
- MINUS
* STAR
/ SLASH
| VBAR
& AMPER
< LESS
> GREATER
= EQUAL
. DOT
% PERCENT
` BACKQUOTE
{ LBRACE
} RBRACE
@ AT
@= ATEQUAL
== EQEQUAL
!= NOTEQUAL
<> NOTEQUAL
<= LESSEQUAL
>= GREATEREQUAL
~ TILDE
^ CIRCUMFLEX
<< LEFTSHIFT
>> RIGHTSHIFT
** DOUBLESTAR
+= PLUSEQUAL
-= MINEQUAL
*= STAREQUAL
/= SLASHEQUAL
%= PERCENTEQUAL
&= AMPEREQUAL
|= VBAREQUAL
^= CIRCUMFLEXEQUAL
<<= LEFTSHIFTEQUAL
>>= RIGHTSHIFTEQUAL
**= DOUBLESTAREQUAL
// DOUBLESLASH
//= DOUBLESLASHEQUAL
-> RARROW
"""

opmap = {}
for line in opmap_raw.splitlines():
    if line:
        op, name = line.split()
        opmap[op] = getattr(token, name)
