from clang.cindex import TokenKind, CursorKind

from lintern.cfile import (
        CodeRewriteRule, CodeChunkReplacement, original_text_from_tokens,
        find_statement_beginning, builtin_signed_type_names, builtin_unsigned_type_names,
        builtin_type_names, default_value_for_type
)


class PrototypeFunctionDeclsRule(CodeRewriteRule):
    """
    This rule rewrites function declarations and implementations with no function
    parameters, to ensure 'void' is used in place of function parameters.

    For example:

        void function();

    Becomes:

        void function(void);
    """
    def __init__(self):
        super(PrototypeFunctionDeclsRule, self).__init__()
        self.tokens = 0

    def consume_token(self, index, tokens, text):
        token = tokens[index]
        if token.cursor.kind == CursorKind.FUNCTION_DECL:
            decl_toks = [t for t in token.cursor.get_tokens()]

            end_index = None
            for i in range(len(decl_toks)):
                t = decl_toks[i]
                if (t.kind == TokenKind.PUNCTUATION) and (t.spelling == ')'):
                    end_index = i + 1

            if end_index is None:
                return

            decl_toks = decl_toks[:end_index]
            if decl_toks[-2].kind != TokenKind.PUNCTUATION:
                return None

            if decl_toks[-2].spelling != "(":
                return None

            newtext = original_text_from_tokens(decl_toks[:-1], text)
            newtext += "void)"

            ret = CodeChunkReplacement(index,
                                       decl_toks[0].extent.start.offset,
                                       decl_toks[-1].extent.end.offset,
                                       newtext)
            return ret


class InitializeCanonicalsRule(CodeRewriteRule):
    """
    This rule rewrites declarations of canonical data types that have no initial
    value, and adds a sane initial value.

    For example:

        volatile float x;
        static const bool y;

    Becomes:

        volatile float x = 0.0f;
        static const bool y = false;

    NOTE: This rule does *not* work with multiple declarations in a single
    statement, so the OneInitPerLineRule *must* run before this one.
    """
    STATE_START = 0
    STATE_ID = 1
    STATE_END = 2

    def __init__(self):
        super(InitializeCanonicalsRule, self).__init__()
        self.state = self.STATE_START
        self.tokens = 0

    def replacement_code(self, tokens, text):
        subtoks = tokens[self.start_index:self.end_index + 1]
        typename = subtoks[0].spelling

        if typename == 'unsigned':
            if subtoks[1].kind == TokenKind.KEYWORD:
                typename = '%s %s' % (typename, subtoks[1].spelling)

        firsttok = find_statement_beginning(tokens, self.start_index)
        fulltype = text[firsttok.extent.start.offset:subtoks[0].extent.start.offset] + typename

        origtext = original_text_from_tokens(subtoks[:-1], text)
        typeval = default_value_for_type(typename)
        newtext = "%s = %s;" % (origtext, typeval)

        ret = CodeChunkReplacement(self.start_index,
                                   subtoks[0].extent.start.offset,
                                   subtoks[-1].extent.end.offset,
                                   newtext)
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
            if (token.kind == TokenKind.KEYWORD) and (token.spelling in builtin_type_names):
                pass
            elif token.kind == TokenKind.IDENTIFIER:
                self.state = self.STATE_END
            elif token.kind == TokenKind.PUNCTUATION:
                if token.spelling != "*":
                    self.state = self.STATE_START
            elif token.kind == TokenKind.KEYWORD:
                if token.spelling not in ['const', 'volatile']:
                    self.state = self.STATE_START
            else:
                self.state = self.STATE_START

        elif self.state == self.STATE_END:
            self.state = self.STATE_START
            if token.kind == TokenKind.PUNCTUATION:
                if token.spelling == ';':
                    self.end_index = index
                    self.state = self.STATE_START
                    return self.replacement_code(tokens, text)

                elif token.spelling in ['=', ',']:
                    self.state = self.STATE_START

        if (self.state != self.STATE_START):
            self.tokens += 1

        return ret


class OneInitPerLineRule(CodeRewriteRule):
    """
    This rule rewrites lines that declare & initialize multiple values in a single
    statement, to separate each declaration + initialization on its own line and
    statement.

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

        if typename == 'unsigned':
            if subtoks[1].kind == TokenKind.KEYWORD:
                typename = '%s %s' % (typename, subtoks[1].spelling)

        firsttok = find_statement_beginning(tokens, self.start_index)
        fulltype = text[firsttok.extent.start.offset:subtoks[0].extent.start.offset] + typename

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
            lines.append("%s %s;" % (fulltype, origtext))

        indent = " " * (firsttok.extent.start.column - 1)
        newtext = ("\n%s" % indent).join(lines)

        ret = CodeChunkReplacement(self.start_index,
                                   firsttok.extent.start.offset,
                                   subtoks[-1].extent.end.offset,
                                   newtext)
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
            if (token.kind == TokenKind.KEYWORD) and (token.spelling in builtin_type_names):
                pass
            elif token.kind == TokenKind.IDENTIFIER:
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
                elif token.spelling == ',':
                    self.commas += 1
                    self.state = self.STATE_VALUES
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
