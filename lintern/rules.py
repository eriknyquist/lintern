from clang.cindex import TokenKind, CursorKind

from lintern.cfile import (
        CodeRewriteRule, CodeChunkReplacement, original_text_from_tokens,
        find_statement_beginning, builtin_signed_type_names, builtin_unsigned_type_names,
        builtin_type_names, default_value_for_type, get_line_indent, get_configured_indent
)


class BracesForCodeBlocksRule(CodeRewriteRule):
    """
    This rule rewrites code blocks following if/else, for, while and do/while statements,
    ensuring that they are surrounded by curly braces.

    For example:

        if (check1())
           func1();
        else if (check2())
            func2();

    Becomes:

        if (check1())
        {
           func1();
        }
        else if (check2())
        {
            func2();
        }
    """
    def __init__(self):
        super(BracesForCodeBlocksRule, self).__init__()
        self.tokens = 0
        self.last_cursor_kind = None

    def _add_semicolon_if_required(self, index, tokens, subtoks):
        if (subtoks[-1].kind != TokenKind.PUNCTUATION) or (subtoks[-1].spelling != ';'):
            nexttok = tokens[index + len(subtoks)]
            if (nexttok.kind == TokenKind.PUNCTUATION) and (nexttok.spelling == ';'):
                subtoks.append(nexttok)

    def _find_last_rparen_index(self, subtoks):
        paren_depth = 0

        for i in range(len(subtoks)):
            token = subtoks[i]
            if (token.kind == TokenKind.PUNCTUATION) and (token.spelling == '('):
                paren_depth += 1
            elif (token.kind == TokenKind.PUNCTUATION) and (token.spelling == ')'):
                paren_depth -= 1

                if paren_depth == 0:
                    return i + 1

        return None

    def _code_block_after_conditional(self, rewriter, index, tokens, text):
        toks = list(tokens[index].cursor.get_tokens())
        self._add_semicolon_if_required(index, tokens, toks)

        # Find the closing paren. of conditional statement
        start_index = self._find_last_rparen_index(toks)

        if start_index is None:
            return None

        if toks[start_index].kind == TokenKind.PUNCTUATION:
            if toks[start_index].spelling == '{':
                # Statement is already using braces.
                return None

        origindent = get_line_indent(toks[0], text)
        indent = get_configured_indent(rewriter.config)

        newtext = original_text_from_tokens(toks[:start_index], text)
        newtext += "\n" + origindent + "{"
        newtext += "\n" + (origindent + indent) + original_text_from_tokens(toks[start_index:], text)
        newtext += "\n" + origindent + "}"

        ret = CodeChunkReplacement(index,
                                   toks[0].extent.start.offset,
                                   toks[-1].extent.end.offset,
                                   newtext)

        return ret

    def rewrite_if_stmt(self, rewriter, index, tokens, text):
        toks = list(tokens[index].cursor.get_tokens())

    def rewrite_do_stmt(self, rewriter, index, tokens, text):
        toks = list(tokens[index].cursor.get_tokens())

        if (toks[1].kind == TokenKind.PUNCTUATION) and (toks[1].spelling == '{'):
            # Do statement is already using braces
            return None

        # Find while statement at the end
        end_index = None
        for i in range(len(toks)):
            tok = toks[i]
            if (tok.kind == TokenKind.PUNCTUATION) and (tok.spelling == ';'):
                end_index = i
                break

        if end_index is None:
            return None

        toks = toks[:end_index + 1]

        origindent = get_line_indent(toks[0], text)
        indent = get_configured_indent(rewriter.config)

        newtext = toks[0].spelling
        newtext += "\n" + origindent + "{"
        newtext += "\n" + (origindent + indent) + original_text_from_tokens(toks[1:], text)
        newtext += "\n" + origindent + "}"

        ret = CodeChunkReplacement(index,
                                   toks[0].extent.start.offset,
                                   toks[-1].extent.end.offset,
                                   newtext)

        return ret

    def rewrite_while_stmt(self, rewriter, index, tokens, text):
        if self.last_cursor_kind == CursorKind.DO_STMT:
            # This is the 'while' part of a do-while statement, no braces to add
            return None

        return self._code_block_after_conditional(rewriter, index, tokens, text)

    def rewrite_for_stmt(self, rewriter, index, tokens, text):
        return self._code_block_after_conditional(rewriter, index, tokens, text)

    def consume_token(self, rewriter, index, tokens, text):
        token = tokens[index]
        ret = None

        if token.cursor.kind == CursorKind.IF_STMT:
            ret = self.rewrite_if_stmt(rewriter, index, tokens, text)

        elif token.cursor.kind == CursorKind.DO_STMT:
            ret = self.rewrite_do_stmt(rewriter, index, tokens, text)

        elif token.cursor.kind == CursorKind.WHILE_STMT:
            ret = self.rewrite_while_stmt(rewriter, index, tokens, text)

        elif token.cursor.kind == CursorKind.FOR_STMT:
            ret = self.rewrite_for_stmt(rewriter, index, tokens, text)

        self.last_cursor_kind = token.cursor.kind
        return ret


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

    def consume_token(self, rewriter, index, tokens, text):
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
        typeval = 'NULL' if self.is_pointer else default_value_for_type(typename)
        newtext = "%s = %s;" % (origtext, typeval)

        ret = CodeChunkReplacement(self.start_index,
                                   subtoks[0].extent.start.offset,
                                   subtoks[-1].extent.end.offset,
                                   newtext)
        return ret

    def consume_token(self, rewriter, index, tokens, text):
        token = tokens[index]
        ret = None

        if self.state == self.STATE_START:
            self.tokens = 0
            self.is_pointer = False

            if (token.kind == TokenKind.KEYWORD) and (token.spelling in builtin_type_names):
                self.start_index = index
                self.state = self.STATE_ID

        elif self.state == self.STATE_ID:
            if (token.kind == TokenKind.KEYWORD) and (token.spelling in builtin_type_names):
                pass

            elif token.kind == TokenKind.IDENTIFIER:
                self.state = self.STATE_END

            elif token.kind == TokenKind.PUNCTUATION:
                if token.spelling == "*":
                    self.is_pointer = True
                else:
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

        indent = get_line_indent(firsttok, text)
        newtext = ("\n%s" % indent).join(lines)

        ret = CodeChunkReplacement(self.start_index,
                                   firsttok.extent.start.offset,
                                   subtoks[-1].extent.end.offset,
                                   newtext)
        return ret

    def consume_token(self, rewriter, index, tokens, text):
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
