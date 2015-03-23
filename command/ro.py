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
MANIFEST_DIR    = ".ro"
MANIFEST_FILE   = "manifest.json"
MANIFEST_FORMAT = "application/rdf+xml"

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


def run(config, options, args):
    status = 0
    progname = ro_utils.progname(args)
    config.progname = progname
    if len(args) < 2:
        print "%s No command given"%(progname)
        print "Enter '%s help' to show a list of commands"
        status = 2
    else:
        status = command.check_command_args(progname, options, args)
    if status != 0: return status
    #@@TODO: refactor to use command/usage table in rocommand for dispatch
    if args[1] == "help":
        status = command.help(config,args)
    elif args[1] == "config":
        status = command.config(config, options, args)
    elif args[1] == "create":

        print("create")


        #status = command.init(roname, )
    elif args[1] == "status":
        status = command.status(config, options, args)
    elif args[1] == "add":
        status = command.add(config, options, args)
    elif args[1] == "remove":
        status = command.remove(config, options, args)
    elif args[1] in ["list", "ls"]:
        status = command.list(config, options, args)
    elif args[1] in ["annotate","link"]:
        status = command.annotate(config, options, args)
    elif args[1] == "annotations":
        status = command.annotations(config, options, args)
    elif args[1] == "evaluate" or args[1] == "eval":
        status = command.evaluate(config, options, args)
    elif args[1] == "checkout":
        status = command.checkout(config, options, args)
    elif args[1] == "push":
        status = command.push(config, options, args)
    elif args[1] == "dump":
        status = command.dump(config, options, args)
    elif args[1] == "manifest":
        status = command.manifest(config, options, args)
    elif args[1] == "snapshot":
        status = command.snapshot(config, options, args)
    elif args[1] == "archive":
        status = command.archive(config, options, args)
    elif args[1] == "freeze":
        status = command.freeze(config, options, args)
    else:
        print "%s: unrecognized command: %s"%(config.progname,args[1])
        status = 2
    return status

def parseCommandArgs(argv):
    """
    Parse command line arguments

    prog -- program name from command line
    argv -- argument list from command line

    Returns a pair consisting of options specified as returned by
    OptionParser, and any remaining unparsed arguments.
    """
    # create a parser for the command line options
    parser = optparse.OptionParser(
                usage="%prog [options] command [args...]\n\n",
                version="%prog "+ro_settings.VERSION)
    # version option
    parser.add_option("-a", "--all",
                      action="store_true",
                      dest="all",
                      default=False,
                      help="All, list all files, depends on the context")
    parser.add_option("-b", "--ro-base",
                      dest="robasedir",
                      help="Base of local directory tree used for ROs")
    parser.add_option("-d", "--ro-directory", "--ro-uri",
                      dest="rodir",
                      help="Directory or URI of Research Object to process (defaults to current directory)")
    parser.add_option("-e", "--user-email",
                      dest="useremail",
                      help="Email address of research objects owner")
    parser.add_option("-f", "--force",
                      action="store_true",
                      dest="force",
                      default=False,
                      help="Force, depends on the context")
    parser.add_option("-g", "--graph",
                      dest="graph",
                      help="Name of existing RDF graph used for annotation")
    parser.add_option("-i", "--ro-identifier",
                      dest="roident",
                      help="Identifier of Research Object (defaults to value based on name)")
    parser.add_option("-l", "--report-level",
                      dest="level",
                      default="may",
                      help="Level of report detail to generate (summary, must, should, may or full)")
    parser.add_option("-n", "--user-name",
                      dest="username",
                      help="Full name of research objects owner")
    parser.add_option("-o", "--output",
                      dest="outformat",
                      help="Output format to generate: TEXT, RDFXML, TURTLE, etc.")
    parser.add_option("-r", "--rosrs-uri",
                      dest="rosrs_uri",
                      help="URI of ROSRS service")
    parser.add_option("-s", "--secret", "--hidden",
                      action="store_true",
                      dest="hidden",
                      help="Include hidden files in RO content listing (when used with -a)")
    parser.add_option("-t", "--rosrs-access-token",
                      dest="rosrs_access_token",
                      help="ROSRS access token")
    parser.add_option("-v", "--verbose",
                      action="store_true",
                      dest="verbose",
                      default=False,
                      help="display verbose output")
    parser.add_option("-w", "--wildcard", "--regexp",
                      action="store_true",
                      dest="wildcard",
                      default=False,
                      help="Interpret annotation target as wildcard/regexp for pattern matching")
    parser.add_option("--debug",
                      action="store_true",
                      dest="debug",
                      default=False,
                      help="display debug output")
    parser.add_option("--asynchronous",
                      action="store_true",
                      dest="asynchronous",
                      default=False,
                      help="perform operation in asynchronous mode")
    parser.add_option("--freeze",
                      action="store_true",
                      dest="freeze",
                      default=False,
                      help="snaphot/archive and freeze in one step")
    parser.add_option("--new",
                      action="store_true",
                      dest="new",
                      default=False,
                      help="force to create a new RO from zip")
    # parse command line now
    (options, args) = parser.parse_args(argv)
    if len(args) < 2: parser.error("No command present")
    return (options, args)

def runCommand(configbase, robase, argv):
    """
    Run program with supplied configuration base directory, Base directory
    from which to start looking for research objects, and arguments.

    This is called by main function (below), and also by test suite routines.

    Returns exit status.
    """
    # @@TODO: robase is ignored: remove parameter here and from all calls
    (options, args) = parseCommandArgs(argv)
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
    log.debug("runCommand: configbase %s, robase %s, argv %s"%(config.configbase, robase, repr(argv)))
    status = 1
    if options:
        status  = run(config.configbase, options, args)
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
            ro_config  = json.load(configfile)
        #TODO add exception handling for missing/unreadable config file
    return ro_config

def runMain():
    """
    Main program transfer function for setup.py console script
    """
    configbase = os.path.expanduser("~")
    robase = os.getcwd()
    config = readconfig(configbase)
    config.configbase = configbase
    return runCommand(config, robase, sys.argv)

if __name__ == "__main__":
    """
    Program invoked from the command line.
    """
    status = runMain()
    sys.exit(status)

#--------+---------+---------+---------+---------+---------+---------+---------+
