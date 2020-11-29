from lintern import rules
from lintern.cfile import CFile


rewrite_rules = [
    rules.BracesAroundCodeBlocks(),
    rules.PrototypeFunctionDeclarations(),
    rules.OneDeclarationPerLine(),
    rules.InitializeCanonicals(),
    rules.TerminateElseIfWithElse(),
    rules.ExplicitUnusedFunctionParams()
]

class CodeRewriter(object):
    def __init__(self, args, config_data):
        self.config = args
        self.rules = []
        self.files = []

        for f in args.filename:
            fobj = CFile(f, ignore_errors=args.ignore_errors)
            if fobj.parsed is None:
                # Parse failed
                self.files = None
                return

            # Parse successful
            self.files.append(fobj)

        # Build list of rules that are enabled in the config file
        for r in rewrite_rules:
            name = r.__class__.__name__
            if (name in config_data) and (config_data[name] == True):
                self.rules.append(r)

    def _rewrite_file(self, cf):
        tokens = cf.tokens()
        if not tokens:
            return None

        i = 0
        restart = False

        for r in self.rules:
            r.reset()
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
                if tokens is None:
                    return None

                i = ret.start_token_index
                r.reset()

        return cf.text

    def rewrite(self):
        for f in self.files:
            new_file_content = self._rewrite_file(f)
            if new_file_content is None:
                return

            if self.config.in_place:
                with open(f.filename, 'w') as fh:
                    fh.write(new_file_content)
            else:
                print(new_file_content)
