#!/usr/bin/env python
"""
RO manager command parser and dispatcher
"""
import sys
import os
import os.path
import re
import codecs
import argparse
import logging

import command

__author__      = "Matthew Gamble (matthew.gamble@gmail.com), Graham Klyne (GK@ACM.ORG)"
__copyright__   = "Copyright 2011-2013, University of Oxford"
__license__     = "MIT (http://opensource.org/licenses/MIT)"

VERSION = "0.3.0"
CONFIG_FILE = "ro.config"


log = logging.getLogger(__name__)

# Make sure MiscUtils can be found on path
# Set up logging
if __name__ == "__main__":
    sys.path.append(os.path.join(sys.path[0],".."))
    logging.basicConfig()
    # Enable debug logging to a file
    if False:
        fileloghandler = logging.FileHandler("ro.log","w")
        fileloghandler.setLevel(logging.DEBUG)
        filelogformatter = logging.Formatter('%(asctime)s.%(msecs)03d %(levelname)s %(message)s', "%H:%M:%S")
        fileloghandler.setFormatter(filelogformatter)
        logging.getLogger('').addHandler(fileloghandler)


def getoptionvalue(val, prompt):
    if not val:
        if sys.stdin.isatty():
            val = raw_input(prompt)
        else:
            val = sys.stdin.readline()
            if val[-1] == '\n': val = val[:-1]
    return val


def run(config, options):
    status = 0
    cmd = options.command

    if not cmd:
        cmd = "help"

    if status != 0: return status

    if cmd == "help":
        status = command.help(config,args)
    elif cmd == "config":
        status = command.config(config, options, args)
    elif cmd == "init":
        status = command.init(options.name, config["robase"], creator=config["username"], verbose=options.verbose, force=options.force)
    elif cmd == "status":
        status = command.status(config["robase"], verbose=options.verbose)
    elif cmd == "add":
        status = command.add(config["robase"], options.file, recursive=options.recursive ,verbose=options.verbose)
    elif cmd == "remove":
        status = command.remove(config["robase"], options.file_or_uri, options.verbose, options.regexp)
    elif cmd == "ls":
        status = command.list(config["robase"])
    elif cmd == "bundle":
        status = command.bundle(config["robase"], options.file)
    elif cmd in ["annotate"]:
        status = command.annotate(config["robase"], file_uri_or_pattern=options.about, annotation_file_or_uri=options.contents, regexp=options.regexp)
    elif cmd == "annotations":
        status = command.annotations(config["robase"], file=options.uri)
#    elif cmd == "evaluate" or cmd == "eval":
#        status = command.evaluate(config, options, args)
    elif cmd == "manifest":
        status = command.manifest(config["robase"])
    else:
        print("{}: unrecognized command: {}".format(config['progname'], cmd))
        status = 2
    return status

def parseCommandArgs(argv):
    """
    Parse command line arguments

    argv -- argument list from command line

    """

    #usage="%prog [options] command [args...]\n\n"

    # create a parser for the command line options
    parser = argparse.ArgumentParser(prog="ro")
    # version option
    #parser.add_argument("-a", "--all",
    #                  action="store_true",
    #                  dest="all",
    #                  default=False,
    #                  help="All, list all files, depends on the context")
    parser.add_argument("-d", "--ro-directory", "--ro-uri",
                      dest="rodir",
                      help="Directory or URI of Research Object to process (defaults to current directory)")
    #parser.add_argument("-e", "--user-email",
    #                  dest="useremail",
    #                  help="Email address of research objects owner")
    parser.add_argument("-f", "--force",
                      action="store_true",
                      dest="force",
                      default=False,
                      help="Force, depends on the context")
    #parser.add_argument("-g", "--graph",
    #                  dest="graph",
    #                  help="Name of existing RDF graph used for annotation")
    #parser.add_argument("-i", "--ro-identifier",
    #                  dest="roident",
    #                  help="Identifier of Research Object (defaults to value based on name)")
    #parser.add_argument("-l", "--report-level",
    #                  dest="level",
    #                  default="may",
    #                  help="Level of report detail to generate (summary, must, should, may or full)")
    #parser.add_argument("-n", "--user-name",
    #                  dest="username",
    #                  help="Full name of research objects owner")
    #parser.add_argument("-o", "--output",
    #                  dest="outformat",
    #                  help="Output format to generate: TEXT, RDFXML, TURTLE, etc.")
    #parser.add_argument("-r", "--rosrs-uri",
    #                  dest="rosrs_uri",
    #                  help="URI of ROSRS service")
    #parser.add_argument("-s", "--secret", "--hidden",
    #                  action="store_true",
    #                  dest="hidden",
    #                  help="Include hidden files in RO content listing (when used with -a)")
    #parser.add_argument("-t", "--rosrs-access-token",
    #                  dest="rosrs_access_token",
    #                  help="ROSRS access token")
    parser.add_argument("-v", "--verbose",
                      action="store_true",
                      dest="verbose",
                      default=False,
                      help="display verbose output")
    #parser.add_argument("-w", "--wildcard", "--regexp",
    #                  action="store_true",
    #                  dest="wildcard",
    #                  default=False,
    #                  help="Interpret annotation target as wildcard/regexp for pattern matching")
    parser.add_argument("--debug",
                      action="store_true",
                      dest="debug",
                      default=False,
                      help="display debug output")
    #parser.add_argument("--asynchronous",
    #                  action="store_true",
    #                  dest="asynchronous",
    #                  default=False,
    #                  help="perform operation in asynchronous mode")
    #parser.add_argument("--freeze",
    #                  action="store_true",
    #                  dest="freeze",
    #                  default=False,
    #                  help="snaphot/archive and freeze in one step")
    #parser.add_argument("--new",
    #                  action="store_true",
    #                  dest="new",
    #                  default=False,
    #                  help="force to create a new RO from zip")

    subparsers = parser.add_subparsers(help="sub-command help",dest="command")

    parser_create = subparsers.add_parser("init", prog="init")
    parser_create.add_argument("name",
                      metavar="<name>",
                      help="Name of the research object")
    parser_create.add_argument("-d", "--ro-directory",
                      dest="rodir",
                      metavar="<dir>",
                      help="Directory of Research Object to initialize (defaults to current directory)")
    parser_create.add_argument("-i", "--id", "--ro-identifier",
                      dest="id",
                      metavar="<id>",
                      help="Identifier of Research Object (defaults to value based on name)")
    parser_create.add_argument("-f", "--force",
                      action="store_true",
                      dest="force",
                      default=False,
                      help="Force the init")

    parser_create = subparsers.add_parser("add", prog="add")
    parser_create.add_argument("-d", "--ro-directory",
                      dest="rodir",
                      metavar="<dir>",
                      help="Directory of Research Object to add the file to (defaults to current directory)")
    parser_create.add_argument("file",
                      metavar="<file>",
                      help="Name of the file or directory to add")
    parser_create.add_argument("-r", "--recursive",
                      action="store_true",
                      dest="recursive",
                      default=False,
                      help="Add all files in directory recursively")

    parser_create = subparsers.add_parser("remove", prog="remove")
    parser_create.add_argument("-d", "--ro-directory",
                      dest="rodir",
                      metavar="<dir>",
                      help="Directory of Research Object to remove the file from (defaults to current directory)")
    parser_create.add_argument("file_or_uri",
                      metavar="<file_or_uri>",
                      help="Name of the file or uri to remove")
    parser_create.add_argument("-e", "--regexp",
                      action="store_true",
                      dest="regexp",
                      default=False,
                      help="Interpret the given value as a regular expression")

    parser_create = subparsers.add_parser("status", prog="status")
    parser_create.add_argument("-d", "--ro-directory",
                      dest="rodir",
                      metavar="<dir>",
                      help="Directory of Research Object (defaults to current directory)")

    parser_create = subparsers.add_parser("ls", prog="ls")
    parser_create.add_argument("-d", "--ro-directory",
                      dest="rodir",
                      metavar="<dir>",
                      help="Directory of Research Object (defaults to current directory)")


    parser_create = subparsers.add_parser("bundle", prog="bundle")
    parser_create.add_argument("-d", "--ro-directory",
                      dest="rodir",
                      metavar="<dir>",
                      help="Directory of Research Object (defaults to current directory)")
    parser_create.add_argument("-f", "--file",
                      dest="file",
                      metavar="<file>",
                      help="Filename to use for research object bundle")

    parser_create = subparsers.add_parser("manifest", prog="manifest")
    parser_create.add_argument("-d", "--ro-directory",
                      dest="rodir",
                      metavar="<dir>",
                      help="Directory of Research Object (defaults to current directory)")

    parser_create = subparsers.add_parser("annotate", prog="annotate")
    parser_create.add_argument("-d", "--ro-directory",
                      dest="rodir",
                      metavar="<dir>",
                      help="Directory of Research Object (defaults to current directory)")
    parser_create.add_argument("about",
                      metavar="about",
                      help="URI aggregated in the ro that the annotation is about")
    parser_create.add_argument("-c", "--contents",
                      dest="contents",
                      metavar="contents",
                      help="URI that identifies the contents of the annotation")
    parser_create.add_argument("-e", "--regexp",
                      action="store_true",
                      dest="regexp",
                      default=False,
                      help="Interpret the about value as a regular expression")

    parser_create = subparsers.add_parser("annotations", prog="annotations")
    parser_create.add_argument("-d", "--ro-directory",
                      dest="rodir",
                      metavar="<dir>",
                      help="Directory of Research Object (defaults to current directory)")
    parser_create.add_argument("-i", "--uri",
                      dest="uri",
                      metavar="<uri>",
                      help="File or uri that you want to see annotations for")

    # parse command line now
    options = parser.parse_args(argv)
    return (options)

ro_command_usage = ()
# ro_command_usage = (
#     [ (["help"], argminmax(2, 2),
#           ["help"])
#     , (["config"], argminmax(2, 2),
#           ["config -b <robase> -n <username> -e <useremail> -r <rosrs_uri> -t <access_token>"])
#     , (["create"], argminmax(3, 3),
#           ["create <RO-name> [ -d <dir> ] [ -i <RO-ident> ]"])
#     , (["status"],argminmax(2, 3),
#           ["status [ -d <dir> | <uri> ]"])
#     , (["add"], argminmax(2, 3),
#           ["add [ -d <dir> ] [ -a ] [ file | directory ]"])
#     , (["remove"], argminmax(3, 3),
#           ["remove [ -d <dir> ] <file-or-uri>"
#           , "remove -d <dir> -w <pattern>"
#           ])
#     , (["list", "ls"], argminmax(2, 3),
#           ["list [ -a ] [ -s ] [ -d <dir> | <uri> ]"
#           , "ls   [ -a ] [ -s ] [ -d <dir> | <uri> ]"
#           ])
#     , (["annotate"], (lambda options, args: (len(args) == 3 if options.graph else len(args) in [4, 5])),
#           ["annotate [ -d <dir> ] <file-or-uri> <attribute-name> <attribute-value>"
#           , "annotate [ -d <dir> ] <file-or-uri> -g <RDF-graph>"
#           , "annotate -d <dir> -w <pattern> <attribute-name> <attribute-value>"
#           , "annotate -d <dir> -w <pattern> -g <RDF-graph>"
#           ])
#     , (["link"], (lambda options, args: (len(args) == 3 if options.graph else len(args) in [4, 5])),
#           ["link [ -d <dir> ] <file-or-uri> <attribute-name> <attribute-value>"
#           , "link [ -d <dir> ] <file-or-uri> -g <RDF-graph>"
#           , "link -d <dir> -w <pattern> <attribute-name> <attribute-value>"
#           , "link -d <dir> -w <pattern> -g <RDF-graph>"
#           ])
#     , (["annotations"], argminmax(2, 3),
#           ["annotations [ <file> | -d <dir> ] [ -o <format> ]"])
#     , (["evaluate", "eval"], argminmax(5, 6),
#           ["evaluate checklist [ -d <dir> ] [ -a | -l <level> ] [ -o <format> ] <minim> <purpose> [ <target> ]"])
#     , (["push"], (lambda options, args: (argminmax(2, 3) if options.rodir else len(args) == 3)),
#           ["push <zip> | -d <dir> [ -f ] [ -r <rosrs_uri> ] [ -t <access_token> ] [ --asynchronous ]"])
#     , (["checkout"], argminmax(2, 3),
#           ["checkout <RO-name> [ -d <dir>] [ -r <rosrs_uri> ] [ -t <access_token> ]"])
#     , (["dump"], argminmax(2, 3),
#           ["dump [ -d <dir> | <rouri> ] [ -o <format> ]"])
#     , (["manifest"], argminmax(2, 3),
#           ["manifest [ -d <dir> | <rouri> ] [ -o <format> ]"])
#     , (["snapshot"],  argminmax(4, 4),
#           ["snapshot <live-RO> <snapshot-id> [ --asynchronous ] [ --freeze ] [ -t <access_token> ] [ -r <rosrs_uri> ]"])
#     , (["archive"],  argminmax(4, 4),
#           ["archive <live-RO> <archive-id> [ --asynchronous ] [ --freeze ] [ -t <access_token> ]"])
#     , (["freeze"],  argminmax(3, 3),
#           ["freeze <RO-id>"])
#     ])



def help(progname, args):
    """
    Display ro command help.  See also ro --help
    """
    print("Available commands are:")
    for (cmds, test, usages) in ro_command_usage:
        for u in usages:
            print( "  %s %s" % (progname, u))
    helptext = (
        [ ""
        , "Supported annotation type names are: "
        , "\n".join([ "  %(name)s - %(description)s" % atype for atype in annotationTypes ])
        , ""
        , "See also:"
        , "  %(progname)s --help"
        , ""
        ])
    for h in helptext:
        print( h % {'progname': progname})
    return 0

def runCommand(config, robase, argv):
    """
    Run program with supplied configuration base directory, Base directory
    from which to start looking for research objects, and arguments.

    This is called by main function (below), and also by test suite routines.

    Returns exit status.
    """
    # @@TODO: robase is ignored: remove parameter here and from all calls
    options = parseCommandArgs(argv)
    if not options or options.debug:
        logging.basicConfig(level=logging.DEBUG)
        if True:
            # Enable debug logging to a file
            fileloghandler = logging.FileHandler("ro.log","w")
            fileloghandler.setLevel(logging.DEBUG)
            filelogformatter = logging.Formatter('%(asctime)s.%(msecs)03d %(levelname)s %(message)s', "%H:%M:%S")
            fileloghandler.setFormatter(filelogformatter)
            logging.getLogger('').addHandler(fileloghandler)
    else:
        logging.basicConfig(level=logging.INFO)
    log.debug("runCommand: configbase %s, robase %s, argv %s"%(config["configbase"], robase, repr(argv)))
    status = 1
    if options:
        status  = run(config, options)
    return status

def configfilename(configbase):
    return os.path.abspath(configbase+"/"+CONFIGFILE)

def writeconfig(configbase, config):
    """
    Write supplied configuration dictionary to indicated directory
    """
    with open(configfilename(configbase), 'w') as configfile:
        json.dump(config, configfile, indent=4)
        configfile.write("\n")
    return

def resetconfig(configbase):
    """
    Reset configuration in indicated directory
    """
    ro_config = {
        "username":             None,
        "useremail":            None,
        "annotationTypes":      None,
        "annotationPrefixes":   None,
        }
    writeconfig(configbase, ro_config)
    return

def readconfig(configbase):
    """
    Read configuration in indicated directory and return as a dictionary
    """
    ro_config = {
        "username":             None,
        "useremail":            None,
        "annotationTypes":      None,
        "annotationPrefixes":   None,
        }
    configfile = None
    try:
        with open(configfilename(configbase), 'r') as configfile:
            config  = json.load(configfile)
            ro_config.update(config)
        #TODO add exception handling for missing/unreadable config file
    except:
        pass
    return ro_config

def runMain():
    """
    Main program transfer function for setup.py console script
    """
    configbase = os.path.expanduser("~")
    config = readconfig(configbase)

    config["configbase"] = configbase
    progname = sys.argv.pop(0)
    config["progname"] = progname
    robase = os.getcwd()
    config["robase"] = robase
    return runCommand(config, robase, sys.argv)

if __name__ == "__main__":
    """
    Program invoked from the command line.
    """
    status = runMain()
    sys.exit(status)

#--------+---------+---------+---------+---------+---------+---------+---------+
