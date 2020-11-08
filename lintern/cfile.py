import clang.cindex
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


def find_statement_beginning(tokenlist, index):
    i = index

    while i > 0:
        t = tokenlist[i]
        if t.kind == TokenKind.PUNCTUATION:
            if (i < index) and (t.spelling in ['{', '}', ';']):
                return tokenlist[i + 1].extent.start

        i -= 1

    return None


def original_text_from_tokens(tokenlist, text):
    start = tokenlist[0].extent.start.offset
    end = tokenlist[-1].extent.end.offset
    return text[start:end]


class CodeChunkReplacement(object):
    def __init__(self, start_file_offset, end_file_offset, replacement_text):
        self.start = start_file_offset
        self.end = start_file_offset
        self.replacement_text = replacement_text


class CodeRewriteRule(object):
    def __init__(self):
        self.start_index = 0
        self.end_index = 0

    def tokens_buffered(self):
        raise NotImplementedError()

    def consume_token(self, index, token, text):
        raise NotImplementedError()


class CFile(object):
    def __init__(self, filename):
        self.text = None

        with open(filename, 'r') as fh:
            self.text = fh.read()

        self.idx = clang.cindex.Index.create()
        self.parsed = self.idx.parse('_temp.c', args=['-std=c99'],
                                     unsaved_files=[('_temp.c', self.text)],
                                     options=0)

    def tokens(self):
        return [t for t in self.parsed.get_tokens(extent=self.parsed.cursor.extent)]
