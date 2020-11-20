import clang.cindex
from clang.cindex import TokenKind


class CodeChunkReplacement(object):
    def __init__(self, index, start_file_offset, end_file_offset, replacement_text):
        self.start_token_index = index
        self.start = start_file_offset
        self.end = end_file_offset
        self.replacement_text = replacement_text


class CodeRewriteRule(object):
    def __init__(self):
        self.start_index = 0
        self.end_index = 0

    def tokens_buffered(self):
        raise NotImplementedError()

    def consume_token(self, rewriter, index, token, text):
        raise NotImplementedError()


class CFile(object):
    def __init__(self, filename):
        self.text = None
        self.filename = filename

        with open(filename, 'r') as fh:
            self.text = fh.read()

        self.idx = clang.cindex.Index.create()
        self.parsed = self.idx.parse('_temp.c', args=['-std=c99'],
                                     unsaved_files=[('_temp.c', self.text)],
                                     options=0)

    def tokens(self, text=None):
        if text is not None:
            self.text = text
            self.parsed = self.idx.parse('_temp.c', args=['-std=c99'],
                                         unsaved_files=[('_temp.c', self.text)],
                                         options=0)

        return [t for t in self.parsed.get_tokens(extent=self.parsed.cursor.extent)]
