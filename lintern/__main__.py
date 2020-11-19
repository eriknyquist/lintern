from lintern.rewriter import rewrite_rules

from lintern.rewriter import CodeRewriter

import yaml

import argparse
import sys


def get_default_config_string():
    data = {r.__class__.__name__ : True for r in rewrite_rules}
    return yaml.dump(data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--indent-type', default='space', dest='indent_type',
                        choices=['space', 'tab'], help="Set the type of indentation to be used")
    parser.add_argument('-l', '--indent-level', default=4, dest='indent_level',
                        help="Set the number of characters to use for a single indent level")
    parser.add_argument('-i', '--in-place', action='store_true', dest='in_place',
                        help="Re-write files in place. Default behaviour is to print "
                        "modified files to stdout.")
    parser.add_argument('-g', '--generate-config', action='store_true', dest='gen_config',
                        help="Generate default configuration data, and print to stdout.")
    parser.add_argument('filename', nargs='*')
    args = parser.parse_args()

    if args.gen_config:
        print("\n" + get_default_config_string())
        return 0

    if not args.filename:
        print("Please provide one or more input filenames.")
        return 1

    r = CodeRewriter(args)
    r.rewrite()
    return 0

if __name__ == "__main__":
    sys.exit(main())
