from lintern import rules
from lintern.cfile import CFile


rewrite_rules = [
    rules.BracesAroundCodeBlocks(),
    rules.PrototypeFunctionDeclarations(),
    rules.OneDeclarationPerLine(),
    rules.InitializeCanonicals(),
    rules.TerminateElseIfWithElse()
]

class CodeRewriter(object):
    def __init__(self, args, config_data):
        self.config = args
        self.files = [CFile(f) for f in args.filename]
        self.rules = []

        # Build list of rules that are enabled in the config file
        for r in rewrite_rules:
            name = r.__class__.__name__
            if (name in config_data) and (config_data[name] == True):
                self.rules.append(r)

    def _rewrite_file(self, cf):
        tokens = cf.tokens()
        i = 0
        restart = False

        for r in self.rules:
            i = 0
            while i < len(tokens):
                ret = r.consume_token(self, i, tokens, cf.text)
                if ret is None:
                    # No replacement text generated, move to the next token
                    i += 1
                    continue

                # This rule generated some replacement text; need to perform the
                # rewrite for the given CodeChunkReplacement, re-generate the stream
                # of tokens for the entire file, and continue the token-processing
                # loop starting from the first token of our new replacement code.
                newtext = cf.text[:ret.start] + ret.replacement_text + cf.text[ret.end:]
                tokens = cf.tokens(text=newtext)
                i = ret.start_token_index

        return cf.text

    def rewrite(self):
        for f in self.files:
            new_file_content = self._rewrite_file(f)
            if self.config.in_place:
                with open(f.filename, 'w') as fh:
                    fh.write(new_file_content)
            else:
                print(new_file_content)
