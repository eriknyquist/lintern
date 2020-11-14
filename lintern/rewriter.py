import sys
from lintern import rules
from lintern.cfile import CFile

import argparse


class CodeRewriter(object):
    rewrite_rules = [
        rules.BracesForCodeBlocksRule(),
        rules.PrototypeFunctionDeclsRule(),
        rules.OneInitPerLineRule(),
        rules.InitializeCanonicalsRule()
    ]

    def __init__(self, config):
        self.config = config
        self.files = [CFile(f) for f in config.filename]

    def _rewrite_file(self, cf):
        tokens = cf.tokens()
        i = 0
        restart = False

        for r in self.rewrite_rules:
            i = 0
            while i < len(tokens):
                #print(tokens[i].kind, tokens[i].spelling)
                ret = r.consume_token(self, i, tokens, cf.text)
                if ret is None:
                    i += 1
                    continue

                newtext = cf.text[:ret.start] + ret.replacement_text + cf.text[ret.end:]
                tokens = cf.tokens(text=newtext)
                i = ret.start_token_index

        return cf.text

    def rewrite(self):
        for f in self.files:
            print(self._rewrite_file(f))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--indent-type', default='space', dest='indent_type',
                        choices=['space', 'tab'], help="Set the type of indentation to be used")
    parser.add_argument('-l', '--indent-level', default=4, dest='indent_level',
                        help="Set the number of characters to use for a single indent level")
    parser.add_argument('filename', nargs='*')
    args = parser.parse_args()

    if not args.filename:
        print("Please provide one or more input filenames.")
        return 1

    r = CodeRewriter(args)
    r.rewrite()
    return 0

if __name__ == "__main__":
    sys.exit(main())
