from lintern import rules
from lintern.cfile import CFile


class CodeRewriter(object):
    rewrite_rules = [
        rules.OneInitPerLineRule()
    ]

    def __init__(self, filenames=[]):
        self.files = [CFile(f) for f in filenames]

    def _rewrite_file(self, cf):
        tokens = cf.tokens()
        for i in range(len(tokens)):
            print(tokens[i].kind, tokens[i].spelling)
            for r in self.rewrite_rules:
                ret = r.consume_token(i, tokens, cf.text)
                if ret is not None:
                    print(ret)

    def rewrite(self):
        for f in self.files:
            self._rewrite_file(f)

r = CodeRewriter(['test.c'])
r.rewrite()
