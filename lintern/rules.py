from clang.cindex import TokenKind

from lintern.cfile import (
        CodeRewriteRule, original_text_from_tokens, find_statement_beginning,
        builtin_signed_type_names, builtin_unsigned_type_names,
        builtin_type_names
)


class OneInitPerLineRule(CodeRewriteRule):
    """
    This rule rewrites a line that declares & initializes multiple values in a single
    statement, to separate each declaration + initialization on its own line.

    For example:

       static const int a = 2, *b = NULL, **c = NULL;

    Becomes:

        static const int a = 2;
        static const int *b = NULL;
        static const int **c = NULL;
    """
    STATE_START = 0
    STATE_ID = 1
    STATE_EQUALS = 2
    STATE_VALUES = 3

    def __init__(self):
        super(OneInitPerLineRule, self).__init__()
        self.state = self.STATE_START
        self.commas = 0
        self.tokens = 0

    def tokens_buffered(self):
        return self.tokens

    def replacement_code(self, tokens, text):
        subtoks = tokens[self.start_index:self.end_index + 1]
        typename = subtoks[0].spelling

        firsttok = find_statement_beginning(tokens, self.start_index)
        typename = text[firsttok.offset:subtoks[0].extent.end.offset]

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

        lines = []
        for g in groups:
            origtext = original_text_from_tokens(g, text)
            lines.append("%s %s;" % (typename, origtext))

        ret = "\n".join(lines)
        return ret

    def consume_token(self, index, tokens, text):
        token = tokens[index]
        ret = None

        if self.state == self.STATE_START:
            self.tokens = 0

            if (token.kind == TokenKind.KEYWORD) and (token.spelling in builtin_type_names):
                self.start_index = index
                self.state = self.STATE_ID

        elif self.state == self.STATE_ID:
            if token.kind == TokenKind.IDENTIFIER:
                self.state = self.STATE_EQUALS
            elif token.kind == TokenKind.PUNCTUATION:
                if token.spelling != "*":
                    self.state = self.STATE_START
            elif token.kind == TokenKind.KEYWORD:
                if token.spelling not in ['const', 'volatile']:
                    self.state = self.STATE_START
            else:
                self.state = self.STATE_START

        elif self.state == self.STATE_EQUALS:
            if token.kind == TokenKind.PUNCTUATION:
                if token.spelling == '=':
                    self.state = self.STATE_VALUES
                elif token.spelling != '*':
                    self.state = self.STATE_START

            else:
                self.state = self.STATE_START

        elif self.state == self.STATE_VALUES:
            if token.kind == TokenKind.PUNCTUATION:
                if token.spelling == ';':
                    if self.commas > 0:
                        self.end_index = index
                        ret = self.replacement_code(tokens, text)

                    self.state = self.STATE_START
                    self.commas = 0

                elif token.spelling == ',':
                    self.commas += 1

        if (self.state != self.STATE_START):
            self.tokens += 1

        return ret
