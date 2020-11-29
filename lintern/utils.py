from clang.cindex import TokenKind


builtin_unsigned_type_names = [
    'unsigned', 'unsigned int', 'uint8_t', 'uint16_t', 'uint32_t', 'uint64_t',
    'unsigned short', 'unsigned long', 'unsigned long long',
    'unsigned char'
]

builtin_signed_type_names = [
    'int', 'int8_t', 'int16_t', 'int32_t', 'int64_t', 'short', 'long', 'long long',
    'char', 'bool', 'float', 'double'
]


builtin_type_names = builtin_signed_type_names + builtin_unsigned_type_names


def find_next_toplevel_semicolon_index(tokens, index=0):
    end_index = None
    depth = 0
    i = index

    while i < len(tokens):
        tok = tokens[i]

        if tok.kind == TokenKind.PUNCTUATION:
            if tok.spelling == '(':
                depth += 1
            elif tok.spelling == ')':
                depth -= 1
            elif (depth == 0) and (tok.spelling == ';'):
                end_index = i
                break

        i += 1

    return end_index


def find_last_matching_char(toks, pair=['(', ')']):
    paren_depth = 0

    for i in range(len(toks)):
        token = toks[i]
        if (token.kind == TokenKind.PUNCTUATION) and (token.spelling == pair[0]):
            paren_depth += 1
        elif (token.kind == TokenKind.PUNCTUATION) and (token.spelling == pair[1]):
            paren_depth -= 1

            if paren_depth == 0:
                return i + 1

    return None


def find_last_matching_rparen(toks):
    return find_last_matching_char(toks, pair=['(', ')'])


def find_last_matching_rbrace(toks):
    return find_last_matching_char(toks, pair=['{', '}'])


def get_configured_indent(config):
    indentchar = ' ' if config.indent_type == 'space' else '\t'
    return indentchar * config.indent_level


def get_line_indent(token, text):
    i = token.extent.start.offset
    ret = ""

    while (i >= 0) and (text[i] != '\n'):
        if text[i] in [' ', '\t', '\v']:
            ret = text[i] + ret
        else:
            ret = ""

        i -= 1

    return ret


def default_value_for_type(typename):
    if typename not in builtin_type_names:
        return None

    if typename in builtin_unsigned_type_names:
        return '0u'
    elif typename == 'bool':
        return 'false'
    elif typename == 'float':
        return '0.0f'
    elif typename == 'double':
        return '0.0'
    elif typename == 'char':
        return '\'\\0\''

    return '0'


def find_statement_beginning_index(tokenlist, index):
    i = index

    while i > 0:
        t = tokenlist[i]
        if (i < index) and (t.kind == TokenKind.COMMENT):
            return i + 1

        elif t.kind == TokenKind.PUNCTUATION:
            if (i < index) and (t.spelling in ['{', '}', ';']):
                return i + 1

        i -= 1

    return index


def original_text_from_tokens(tokenlist, text):
    if not tokenlist:
        return ''

    start = tokenlist[0].extent.start.offset
    end = tokenlist[-1].extent.end.offset
    return text[start:end]


