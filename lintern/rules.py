from clang.cindex import TokenKind, CursorKind

from lintern.cfile import CodeRewriteRule, CodeChunkReplacement
from lintern.utils import (
        original_text_from_tokens, find_statement_beginning_index,
        builtin_signed_type_names, builtin_unsigned_type_names, builtin_type_names,
        default_value_for_type, get_line_indent, get_configured_indent,find_last_matching_rparen,
        find_last_matching_rbrace, find_next_toplevel_semicolon_index
)


def add_semicolon_if_required(index, tokens, subtoks):
    if (subtoks[-1].kind != TokenKind.PUNCTUATION) or (subtoks[-1].spelling != ';'):
        if (index + len(subtoks)) < len(tokens):
            nexttok = tokens[index + len(subtoks)]
            if (nexttok.kind == TokenKind.PUNCTUATION) and (nexttok.spelling == ';'):
                subtoks.append(nexttok)


class BracesAroundCodeBlocks(CodeRewriteRule):
    """
This rule rewrites code blocks following if/else, for, while and do/while statements,
ensuring that they are surrounded by braces.

For example:

::

    if (check1())
       func1();
    else if (check2())
        if (check3())
            func2();

Becomes:

::

    if (check1())
    {
       func1();
    }
    else if (check2())
    {
        if (check3())
        {
            func2();
        }
    }

    """
    def __init__(self):
        super(BracesAroundCodeBlocks, self).__init__()
        self.tokens = 0
        self.last_cursor_kind = None

    def _code_block_after_conditional(self, rewriter, index, tokens, text):
        # Find the closing paren. of conditional statement
        start_index = find_last_matching_rparen(tokens)

        if start_index is None:
            return None

        if tokens[start_index].kind == TokenKind.PUNCTUATION:
            if tokens[start_index].spelling == '{':
                # Statement is already using braces.
                return None

        end_index = find_next_toplevel_semicolon_index(tokens) + 1
        if end_index is None:
            return None

        tokens = tokens[:end_index]
        origindent = get_line_indent(tokens[0], text)
        indent = get_configured_indent(rewriter.config)

        newtext = original_text_from_tokens(tokens[:start_index], text)
        newtext += "\n" + origindent + "{"
        newtext += "\n" + (origindent + indent) + original_text_from_tokens(tokens[start_index:], text)
        newtext += "\n" + origindent + "}"


        ret = CodeChunkReplacement(index,
                                   tokens[0].extent.start.offset,
                                   tokens[-1].extent.end.offset,
                                   newtext)

        return ret

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

        toks = list(tokens[index].cursor.get_tokens())
        add_semicolon_if_required(index, tokens, toks)
        return self._code_block_after_conditional(rewriter, index, toks, text)

    def rewrite_for_stmt(self, rewriter, index, tokens, text):
        toks = list(tokens[index].cursor.get_tokens())
        add_semicolon_if_required(index, tokens, toks)
        return self._code_block_after_conditional(rewriter, index, toks, text)

    def check_rewrite_ifelse_stmt(self, rewriter, index, tokens, text):
        tok = tokens[index]
        if tok.kind != TokenKind.KEYWORD:
            return None

        if tok.spelling == 'if':
            return self._code_block_after_conditional(rewriter, index, tokens[index:], text)
        elif tok.spelling == 'else':
            if index < (len(tokens) - 1):
                if ((tokens[index + 1].kind == TokenKind.KEYWORD) and
                    (tokens[index + 1].spelling == 'if')):
                    return self._code_block_after_conditional(rewriter, index, tokens[index:], text)

                elif ((tokens[index + 1].kind == TokenKind.PUNCTUATION) and
                      (tokens[index + 1].spelling == '{')):
                    # Statement is already using braces
                    return None

                else:
                    toks = tokens[index:]
                    end_index = find_next_toplevel_semicolon_index(toks) + 1
                    if end_index is None:
                        return None

                    toks = toks[:end_index]

                    origindent = get_line_indent(toks[0], text)
                    indent = get_configured_indent(rewriter.config)

                    newtext = toks[0].spelling
                    newtext += "\n" + origindent + "{"
                    newtext += ("\n" + (origindent + indent) +
                                original_text_from_tokens(toks[1:], text))
                    newtext += "\n" + origindent + "}"

                    ret = CodeChunkReplacement(index,
                                               toks[0].extent.start.offset,
                                               toks[-1].extent.end.offset,
                                               newtext)
                    return ret

        return None

    def consume_token(self, rewriter, index, tokens, text):
        token = tokens[index]
        ret = None

        ret = self.check_rewrite_ifelse_stmt(rewriter, index, tokens, text)
        if ret:
            return ret

        if token.cursor.kind == CursorKind.DO_STMT:
            ret = self.rewrite_do_stmt(rewriter, index, tokens, text)

        elif token.cursor.kind == CursorKind.WHILE_STMT:
            ret = self.rewrite_while_stmt(rewriter, index, tokens, text)

        elif token.cursor.kind == CursorKind.FOR_STMT:
            ret = self.rewrite_for_stmt(rewriter, index, tokens, text)

        self.last_cursor_kind = token.cursor.kind
        return ret


class PrototypeFunctionDeclarations(CodeRewriteRule):
    """
This rule rewrites function declarations and implementations with no function
parameters, to ensure 'void' is used in place of function parameters.

For example:

::

    void function();

    void function()
    {
        return;
    }

Becomes:

::

    void function(void);

    void function(void)
    {
        return;
    }

    """
    def __init__(self):
        super(PrototypeFunctionDeclarations, self).__init__()
        self.tokens = 0

    def consume_token(self, rewriter, index, tokens, text):
        token = tokens[index]
        if token.cursor.kind == CursorKind.FUNCTION_DECL:
            decl_toks = [t for t in token.cursor.get_tokens()]

            # Find opening paren of param declarations
            lparen_index = None
            for i in range(len(decl_toks)):
                t = decl_toks[i]
                if (t.kind == TokenKind.PUNCTUATION) and (t.spelling == '('):
                    lparen_index = i
                    break

            if lparen_index is None:
                return

            if lparen_index >= len(decl_toks):
                return None

            if ((decl_toks[lparen_index + 1].kind != TokenKind.PUNCTUATION) or
                (decl_toks[lparen_index + 1].spelling != ')')):
                # Already has something in the parameter declaration
                return None

            decl_toks = decl_toks[:lparen_index + 2]

            newtext = original_text_from_tokens(decl_toks[:-1], text)
            newtext += "void)"

            ret = CodeChunkReplacement(index,
                                       decl_toks[0].extent.start.offset,
                                       decl_toks[-1].extent.end.offset,
                                       newtext)
            return ret


class InitializeCanonicals(CodeRewriteRule):
    """
This rule rewrites declarations of canonical data types that have no initial
value, and adds a sane initial value.

For example:

::

    volatile float x, *X;
    static const bool y;
    short *z;

Becomes:

::

    volatile float x = 0.0f, *X = NULL;
    static const bool y = false;
    short *z = NULL;

    """
    def rewrite_var_decl(self, rewriter, index, startindex, endindex, tokens, text):
        varindex = index + 1
        if tokens[index].spelling == 'unsigned':
            if tokens[index + 1].spelling in builtin_type_names:
                varindex += 1

        decls_only = tokens[varindex:endindex + 1]
        toks = tokens[startindex:endindex + 1]
        decls = []
        declbuf = []
        inits_needed = 0
        bdepth = 0
        pdepth = 0
        is_pointer = False
        needs_init = True

        for i in range(len(decls_only)):
            tok = decls_only[i]
            if tok.kind == TokenKind.PUNCTUATION:
                if (pdepth == 0) and (bdepth == 0) and (tok.spelling in [',', ';']):
                    if needs_init:
                        inits_needed += 1

                    decls.append((needs_init, is_pointer, declbuf))
                    is_pointer = False
                    needs_init = True
                    declbuf = []

                elif tok.spelling == '(':
                    pdepth += 1
                    declbuf.append(tok)

                elif tok.spelling == ')':
                    pdepth -= 1
                    declbuf.append(tok)

                elif tok.spelling == '{':
                    bdepth += 1
                    declbuf.append(tok)

                elif tok.spelling == '}':
                    bdepth -= 1
                    declbuf.append(tok)

                elif tok.spelling == '*':
                    is_pointer = True
                    declbuf.append(tok)

                else:
                    declbuf.append(tok)

            else:
                declbuf.append(tok)

            if tok.spelling in ['=', '[']:
                needs_init = False

        if not decls or not decls[0]:
            return None

        if inits_needed == 0:
            # All values are already initialized
            return None

        newdecls = []
        for needs_init, is_pointer, decl in decls:
            # Check if already initialized
            newtext = original_text_from_tokens(decl, text)

            if needs_init:
                if is_pointer:
                    value = 'NULL'
                else:
                    value = default_value_for_type(tokens[index].spelling)

                newtext += " = %s" % value

            newdecls.append(newtext)

        newtext = original_text_from_tokens(tokens[startindex:varindex], text) + ' '
        newtext += ', '.join(newdecls) + ";"

        ret = CodeChunkReplacement(index,
                                   tokens[startindex].extent.start.offset,
                                   tokens[endindex].extent.end.offset,
                                   newtext)
        return ret

    def consume_token(self, rewriter, index, tokens, text):
        tok = tokens[index]

        if (tok.kind == TokenKind.KEYWORD) and (tok.spelling in builtin_type_names):
            if tok.cursor.kind == CursorKind.VAR_DECL:
                # Find statement beginning
                startindex = find_statement_beginning_index(tokens, index)

                # Find statement end
                endindex = find_next_toplevel_semicolon_index(tokens, index)

                return self.rewrite_var_decl(rewriter, index, startindex, endindex, tokens, text)

        return None


class OneDeclarationPerLine(CodeRewriteRule):
    """
This rule rewrites lines that declare & initialize multiple values in a single
statement, to separate each declaration + initialization on its own line and
statement.

For example:

::

   static const int a = 2, *b = NULL, **c = NULL;

Becomes:

::

    static const int a = 2;
    static const int *b = NULL;
    static const int **c = NULL;

    """
    STATE_START = 0
    STATE_ID = 1
    STATE_EQUALS = 2
    STATE_VALUES = 3

    def __init__(self):
        super(OneDeclarationPerLine, self).__init__()
        self.state = self.STATE_START
        self.commas = 0
        self.tokens = 0
        self.depth = 0

    def tokens_buffered(self):
        return self.tokens

    def replacement_code(self, tokens, text):
        subtoks = tokens[self.start_index:self.end_index + 1]
        typename = subtoks[0].spelling

        if typename == 'unsigned':
            if subtoks[1].kind == TokenKind.KEYWORD:
                typename = '%s %s' % (typename, subtoks[1].spelling)

        firsttok_index = find_statement_beginning_index(tokens, self.start_index)
        firsttok = tokens[firsttok_index]
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
                if token.cursor.kind != CursorKind.PARM_DECL:
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

                elif token.spelling == '(':
                    self.depth += 1
                elif token.spelling == ')':
                    self.depth -= 1
                elif (self.depth == 0) and (token.spelling == ','):
                    self.commas += 1

        if (self.state != self.STATE_START):
            self.tokens += 1

        return ret


class TerminateElseIfWithElse(CodeRewriteRule):
    """
Rewrites else-if chains to ensure they are terminated with an 'else' clause.

For example:

::

    if (check1())
    {
        func1();
    }
    else if (check2())
    {
        func2();
    }

Becomes:

::

    if (check1())
    {
        func1();
    }
    else if (check2())
    {
        func2();
    }
    else
    {
        ;
    }

    """

    def rewrite_if_stmt(self, rewriter, index, tokens, text):
        # Check if there are else-if clauses but a missing else clause
        has_else = False
        has_elseif = False

        for i in range(len(tokens)):
            t = tokens[i]
            if t.kind == TokenKind.KEYWORD:
                if t.spelling == 'else':
                    if ((i < (len(tokens) - 1)) and
                        (tokens[i + 1].kind == TokenKind.KEYWORD) and
                        (tokens[i + 1].spelling == 'if')):
                        has_elseif = True
                    else:
                        has_else = True

        # If statement already has an 'else' clause, or if statement
        # has no else-if clause, no rewrite needed.
        if has_else or (not has_elseif):
            return None

        # No else clause, we need to add one.
        origindent = get_line_indent(tokens[0], text)
        indent = get_configured_indent(rewriter.config)

        newtext = original_text_from_tokens(tokens, text)
        newtext += "\n" + origindent + "else"
        newtext += "\n" + origindent + "{"
        newtext += "\n" + origindent + indent + ";"
        newtext += "\n" + origindent + "}"

        ret = CodeChunkReplacement(index,
                                   tokens[0].extent.start.offset,
                                   tokens[-1].extent.end.offset,
                                   newtext)

        return ret

    def consume_token(self, rewriter, index, tokens, text):
        if tokens[index].cursor.kind == CursorKind.IF_STMT:
            toks = list(tokens[index].cursor.get_tokens())
            add_semicolon_if_required(index, tokens, toks)
            return self.rewrite_if_stmt(rewriter, index, toks, text)


class ExplicitUnusedFunctionParams(CodeRewriteRule):
    """
This rule rewrites function implementations to explicitly mark unused function
parameters with "void".

For example:

::

    int func(int a, int b)
    {
        return b + 2;
    }

Becomes:

::

    int func(int a, int b)
    {
        (void) a;

        return b + 2;
    }
    """

    def rewrite_func_impl(self, paramnames, rewriter, index, tokens, text):
        # Find opening brace
        lbrace_index = None
        for i in range(len(tokens)):
            tok = tokens[i]
            if (tok.kind == TokenKind.PUNCTUATION) and (tok.spelling == '{'):
                lbrace_index = i
                break

        if lbrace_index is None:
            return None

        # Now, count no. of references of each param within the function body
        refs = {n: 0 for n in paramnames}
        for i in range(lbrace_index, len(tokens), 1):
            tok = tokens[i]
            if tok.kind == TokenKind.IDENTIFIER:
                if tok.spelling in refs:
                    refs[tok.spelling] += 1

        not_used = []
        for n in refs:
            if refs[n] == 0:
                not_used.append(n)

        if not not_used:
            # All params are referenced
            return None

        # Get indent from current first line of function body
        origindent = get_line_indent(tokens[lbrace_index + 1], text)

        newtext = ("\n" + origindent).join(["(void) %s;" % n for n in not_used])
        newtext += "\n"

        ret = CodeChunkReplacement(index,
                                   tokens[lbrace_index + 1].extent.start.offset,
                                   tokens[lbrace_index].extent.end.offset,
                                   newtext)

        return ret

    def consume_token(self, rewriter, index, tokens, text):
        if tokens[index].cursor.kind == CursorKind.FUNCTION_DECL:
            paramnames = [a.displayname for a in list(tokens[index].cursor.get_arguments())]
            if not paramnames:
                # No function params
                return None

            toks = list(tokens[index].cursor.get_tokens())
            return self.rewrite_func_impl(paramnames, rewriter, index, toks, text)

        return None
