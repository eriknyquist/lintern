import clang.cindex
from clang.cindex import TokenKind, Diagnostic

import ccsyspath

compiler_args = ['-std=c99']


def add_required_include_paths(extra_include_paths=[], compiler_path='clang'):
    include_paths = ccsyspath.system_include_paths('clang') + extra_include_paths

    for p in include_paths:
        compiler_args.extend(['-I', p])


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

    def reset(self):
        pass


class CFile(object):
    TEMP_FILENAME = '_temp.c'

    def __init__(self, filename, ignore_errors=False):
        self.text = None
        self.filename = filename
        self.ignore_errors = ignore_errors

        with open(filename, 'r') as fh:
            self.text = fh.read()

        self.idx = clang.cindex.Index.create()
        if not self._parse():
            self.parsed = None

    def _parse(self):
        self.parsed = self.idx.parse(self.TEMP_FILENAME, args=compiler_args,
                                     unsaved_files=[(self.TEMP_FILENAME, self.text)])

        if not self.ignore_errors:
            err_lines = []
            for d in self.parsed.diagnostics:
                if d.severity > Diagnostic.Warning:
                    err_lines.append(d.format().replace(self.TEMP_FILENAME, self.filename))

            if err_lines:
                print("\nFile '%s' has errors:\n\n%s\n" % (self.filename, '\n'.join(err_lines)))
                return False

        return True

    def tokens(self, text=None):
        if text is not None:
            self.text = text
            if not self._parse():
                return None

        return [t for t in self.parsed.get_tokens(extent=self.parsed.cursor.extent)]
