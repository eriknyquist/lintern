from clang.cindex import TokenKind

from lintern.cfile import CodeRewriteRule
from lintern.cfile import (
        builtin_signed_type_names, builtin_unsigned_type_names,
        builtin_type_names
)

class OneInitPerLineRule(CodeRewriteRule):
    STATE_START = 0
    STATE_ID = 1
    STATE_EQUALS = 2
    STATE_VALUES = 3

    def __init__(self):
        super(OneInitPerLineRule, self).__init__()
        self.state = self.STATE_START
        self.commas = 0

    def build_replacement_code(self, tokens):
        subtoks = tokens[self.start_index:self.end_index + 1]
        typename = subtoks[0].spelling

        # Group tokens between commas, starting from the first ID
        groups = []
        buf = []
        for i in range(1, len(subtoks), 1): # First ID is index 1
            tok = subtoks[i]
            if (tok.kind == TokenKind.PUNCTUATION) and (tok.spelling in [',', ';']):
                groups.append(buf)
                buf = []
            else:
                buf.append(tok)

        lines = ["%s %s;" % (typename, " ".join([t.spelling for t in g])) for g in groups]
        ret = "\n".join(lines)
        return ret

    def consume_token(self, index, tokens, text):
        token = tokens[index]
        ret = None

        if self.state == self.STATE_START:
            if (token.kind == TokenKind.KEYWORD) and (token.spelling in builtin_type_names):
                self.start_index = index
                self.state = self.STATE_ID

        elif self.state == self.STATE_ID:
            if token.kind == TokenKind.IDENTIFIER:
                self.state = self.STATE_EQUALS
            elif token.kind == TokenKind.PUNCTUATION:
                if token.spelling != "*":
                    self.state = self.STATE_START
            else:
                self.state = self.STATE_START

        elif self.state == self.STATE_EQUALS:
            if token.kind == TokenKind.PUNCTUATION:
                if token.spelling == '=':
                    self.state = self.STATE_VALUES
                elif token.spelling != '*':
                    self.state = self.STATE_START

            elif token.kind == TokenKind.KEYWORD:
                if token.spelling not in ['const', 'volatile']:
                    self.state = self.STATE_START
            else:
                self.state = self.STATE_START

        elif self.state == self.STATE_VALUES:
            if token.kind == TokenKind.PUNCTUATION:
                if token.spelling == ';':
                    if self.commas > 0:
                        self.end_index = index
                        ret = self.build_replacement_code(tokens)

                    self.state = self.STATE_START
                    self.commas = 0

                elif token.spelling == ',':
                    self.commas += 1

        return ret
