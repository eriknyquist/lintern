from lintern import rules
from lintern.cfile import CFile


class CodeRewriter(object):
    rewrite_rules = [
        rules.PrototypeFunctionDeclsRule(),
        rules.OneInitPerLineRule(),
        rules.InitializeCanonicalsRule()
    ]

    def __init__(self, filenames=[]):
        self.files = [CFile(f) for f in filenames]

    def _rewrite_file(self, cf):
        tokens = cf.tokens()
        i = 0
        restart = False

        for r in self.rewrite_rules:
            i = 0
            while i < len(tokens):
                #print(tokens[i].kind, tokens[i].spelling)
                ret = r.consume_token(i, tokens, cf.text)
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

r = CodeRewriter(['test.c'])
r.rewrite()
