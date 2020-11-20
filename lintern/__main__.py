from lintern.rewriter import rewrite_rules

from lintern.rewriter import CodeRewriter

import yaml

import argparse
import sys
import os


def get_default_config_data():
    return {r.__class__.__name__ : True for r in rewrite_rules}

def verify_config_data(cfg_data):
    default = get_default_config_data()

    for key in cfg_data:
        if key not in default:
            return "unrecognised option '%s'" % key

        if not isinstance(cfg_data[key], bool):
            return "invalid value '%s' for option '%s'" % (str(cfg_data[key]), key)

    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--indent-type', default='space', dest='indent_type',
                        choices=['space', 'tab'], help="Set the type of indentation to be used")
    parser.add_argument('-l', '--indent-level', default=4, dest='indent_level',
                        help="Set the number of characters to use for a single indent level")
    parser.add_argument('-f', '--config-file', default='.lintern', dest='config_file',
                        help="Filename to read configuration from")
    parser.add_argument('-i', '--in-place', action='store_true', dest='in_place',
                        help="Re-write files in place. Default behaviour is to print "
                        "modified files to stdout.")
    parser.add_argument('-g', '--generate-config', action='store_true', dest='gen_config',
                        help="Generate default configuration data, and print to stdout.")
    parser.add_argument('filename', nargs='*')
    args = parser.parse_args()

    if args.gen_config:
        print("\n" + yaml.dump(get_default_config_data()))
        return 0

    if not args.filename:
        print("Please provide one or more input filenames.")
        return 1

    if os.path.isfile(args.config_file):
        cfg_data = None

        try:
            with open(args.config_file, 'r') as fh:
                cfg_data = yaml.load(fh, Loader=yaml.FullLoader)
        except:
            print("Malformed file '%s', stopping." % args.config_file)
            return 1

        if cfg_data is None:
            print("Empty config file '%s', using default options." % args.config_file)
            cfg_data = get_default_config_data()
        else:
            result = verify_config_data(cfg_data)
            if result is not None:
                print("Error reading file %s: %s" % (args.config_file, result))
                return 1
    else:
        print("configuration file '%s' not found, using default options." % args.config_file)
        cfg_data = get_default_config_data()

    r = CodeRewriter(args, cfg_data)
    r.rewrite()
    return 0

if __name__ == "__main__":
    sys.exit(main())
