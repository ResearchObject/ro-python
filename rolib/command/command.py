# command.py

"""
Basic command functions for ro command line tool
"""

__author__      = "Matthew Gamble, Graham Klyne (GK@ACM.ORG)"
__copyright__   = "Copyright 2011-2013, University of Oxford, 2014-2015, University of Manchester"
__license__     = "MIT (http://opensource.org/licenses/MIT)"

from future.standard_library import install_aliases
install_aliases()

import sys, select
import os
import os.path
import re
import datetime
import logging


from urllib.parse import urlparse, urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError

#from legacy.ro_utils import EvoType
from xml.parsers import expat
from httplib2 import RelativeURIError
import time
try:
    # Running Python 2.5 with simplejson?
    import simplejson as json
except ImportError:
    import json

log = logging.getLogger(__name__)

#import legacy.ro_settings
#import legacy.ro_utils
#import legacy.ro_uriutils

from rolib.annotation import annotationTypes, annotationPrefixes

from zipfile import ZipFile

from rolib.manifest import Manifest
from rolib.bundle import Bundle

RDFTYP = ["RDFXML","N3","TURTLE","NT","JSONLD","RDFA"]
VARTYP = ["JSON","CSV","XML"]

MANIFEST_DIR    = ".ro"
MANIFEST_FILE   = "manifest.json"


RDFTYPPARSERMAP = (
    { "RDFXML": "xml"
    , "N3":     "n3"
    , "TURTLE": "n3"
    , "NT":     "nt"
    , "JSONLD": "jsonld"
    , "RDFA":   "rdfa"
    })

RDFTYPSERIALIZERMAP = (
    { "RDFXML": "pretty-xml"
    , "N3":     "n3"
    , "TURTLE": "turtle"
    , "NT":     "nt"
    , "JSONLD": "jsonld"
    })

def manifest_directory(ro_dir):
    return os.path.join(ro_dir, MANIFEST_DIR)

def manifest_file(ro_dir):
    return os.path.join(ro_dir, MANIFEST_DIR, MANIFEST_FILE)

def directory_and_manifest_exist(ro_dir):
    manifestdir = manifest_directory(ro_dir)
    manifestfilepath = manifest_file(ro_dir)
    if os.path.isdir(manifestdir) and os.path.isfile(manifestfilepath):
        return True
    else:
        return False

def sanitize_filename_for_identifier(filename, rodir):
    """
    Filenames need to have their root as the ro root directory
    Assume that the file is located within ro folder
    """
    filename = os.path.relpath(filename, rodir)
    if filename[0:2] == './':
        filename = filename[2:]
    filename = os.path.join(os.sep, filename)
    return filename

def sanitize_name_for_identifier(name):
    """
    Turn resource object name into an identifier containing only letters, digits and underscore characters
    """
    name = re.sub(r"\s", '_', name)         # spaces, etc. -> underscores
    name = re.sub(r"\W", "", name)          # Non-identifier characters -> remove
    return name

def config(progname, configbase, options, args):
    """
    Update RO repository access configuration
    """
    robase = os.path.realpath(options.robasedir)
    ro_config = {
        "robase":               getoptionvalue(robase,
                                "RO local base directory:       "),
        "rosrs_uri":            getoptionvalue(options.rosrs_uri,
                                "URI for ROSRS service:         "),
        "rosrs_access_token":   getoptionvalue(options.rosrs_access_token,
                                "Access token for ROSRS service:"),
        "username":             getoptionvalue(options.username,
                                "Name of research object owner: "),
        "useremail":            getoptionvalue(options.useremail,
                                "Email address of owner:        "),
        # Built-in annotation types and prefixes
        "annotationTypes":      annotationTypes,
        "annotationPrefixes":   annotationPrefixes
        }
    ro_config["robase"] = os.path.abspath(ro_config["robase"])
    if options.verbose:
        print(("ro config -b %(robase)s" % ro_config))
        print(( "          -r %(rosrs_uri)s" % ro_config))
        print(( "          -t %(rosrs_access_token)s" % ro_config))
        print(("          -n %(username)s -e %(useremail)s" % ro_config))
    ro_utils.writeconfig(configbase, ro_config)
    if options.verbose:
        print(("ro configuration written to %s" % (os.path.abspath(configbase))))
    return 0


def init(name, dir, id=None, creator=None, verbose=False, force=False):
    """
    Create a new Research Object.

    ro init name [-f] [ -d dir ] [ -i id ]
    """

    id = id or sanitize_name_for_identifier(name)
    timestamp = datetime.datetime.now().replace(microsecond=0)

    if verbose:
        print("ro create \{}\" -d \"{}\" -i \"{}\"".format(name,dir,id))
    manifestdir = manifest_directory(dir)
    log.debug("manifestdir: " + manifestdir)
    manifestfilepath = manifest_file(dir)
    log.debug("manifestfilepath: " + manifestfilepath)

    try:
        os.makedirs(manifestdir)
    except OSError:
        if os.path.isdir(manifestdir):
            # Someone else created it...
            if force:
                pass
            else:
                print(".ro folder already exists, use --force to init an existing ro.")
                return 1
        else:
            # There was an error on creation, so make sure we know about it
            raise

    #Create the manifest
    manifest = Manifest(id=id)
    manifest.createdBy = creator
    manifest.createdOn = timestamp
    manifest.title = name
    manifest.description = name

    log.debug("manifest: " + manifest.to_json())
    with open(manifestfilepath, 'w') as manifest_filehandle:
        manifest_filehandle.write(manifest.to_json())
    return 0

def status(dir, verbose=False):
    """
    Display status of a designated research object

    ro status [ -d dir ]
    """

    manifestfilepath = manifest_file(dir)
    if not directory_and_manifest_exist(dir):
        print("Could not find manifest file: {}".format(manifestfilepath))
        return 1

    manifest = Manifest(filename=manifestfilepath)
    print("Research Object status")
    print("  Identifier: {}".format(manifest.id))
    print("  Title: {}".format(manifest.title))
    print("  Creator:")
    if manifest.createdBy.name:
        print("     Name: {}".format(manifest.createdBy.name))
    if manifest.createdBy.orcid:
        print("     Orcid: {}".format(manifest.createdBy.orcid))
    if manifest.createdBy.uri:
        print("    URI: {}".format(manifest.createdBy.uri))
    print("  Created: {}".format(manifest.createdOn))
    print("  Aggregates:")
    aggregates = [aggregate.uri for aggregate in manifest.aggregates]
    for aggregate in aggregates:
        print("       {}".format(aggregate))
    #Establish the Unaggregated files
    files = []
    for dirpath, dirnames, filenames in os.walk(dir):
        #make the path relative to the top dir of the ro
        dirpath = os.path.relpath(dirpath, dir)
        files += [sanitize_filename_for_identifier(os.path.join(dirpath, filename), dir) for filename in filenames]
    for aggregate in aggregates:
        if aggregate in files:
            files.remove(aggregate)
    print("")
    print("Unaggregated files:")
    for file in files:
        print(file)
    print("")

    return 0

def in_directory(file, directory):
    #make both absolute
    directory = os.path.join(os.path.realpath(directory), '')
    file = os.path.realpath(file)

    #return true, if the common prefix of both is equal to directory
    #e.g. /a/b/c/d.rst and directory is /a/b, the common prefix is /a/b
    return os.path.commonprefix([file, directory]) == directory


def add(dir, file_or_directory, createdBy=None, createdOn=None, mediatype=None, recursive=False, verbose=False, force=False):
    """
    Add files to a research object manifest

    ro add [ -d dir ] file
    ro add [ -d dir ] [-r] [directory]

    Use -r/--recursive to add subdirectories recursively

    If no file or directory specified, defaults to current directory.
    """

    #TODO check for file_or_directory = '.'
    #TODO work out what root directory of ro is and make all files relative to that

    #os.path.relpath
    if not in_directory(file_or_directory, dir):
        print("Error: Can't add files outside the ro directory")
        return 1

    files = []
    if os.path.isdir(file_or_directory):
        if recursive:
            for dirpath, dirnames, filenames in os.walk(file_or_directory):
                #make the path relative to the top dir of the ro
                dirpath = os.path.relpath(dirpath, dir)
                files += [os.path.join(dirpath, filename) for filename in filenames]
        else:
            files = [os.path.join(file_or_directory, filename) for filename in os.listdir(file_or_directory) if os.path.isfile(os.path.join(file_or_directory, filename))]
    else:
        if os.path.isfile(file_or_directory):
            files = [file_or_directory]
        else:
            print("Error - File does not exist: {}".format(file_or_directory))
    # Read and update manifest
    if verbose:
        print("ro add -d ") #TODO fix print
    manifest_file_path = manifest_file(dir)
    manifest = Manifest(filename=manifest_file_path)
    for file in files:
        file = sanitize_filename_for_identifier(file, dir)
        manifest.add_aggregate(file, createdBy=createdBy, createdOn=createdOn, mediatype=mediatype)

    with open(manifest_file_path, 'w') as manifest_filehandle:
        manifest_filehandle.write(manifest.to_json())

    return 0

def remove(dir, file_uri_or_pattern, verbose=False, regexp=False):
    """
    Remove a specified research object component or components

    remove [ -d <dir> ] <file-or-uri>
    remove -d <dir> -w <pattern>
    """
    #Get the manifest file for this ro
    manifest_file_path = manifest_file(dir)
    manifest = Manifest(filename=manifest_file_path)

    if regexp:
        try:
            pattern = re.compile(file_uri_or_pattern)
        except re.error as e:
            #print('''%(rocmd)s remove -w "%(rofile)s" <...> : %(err)s''' % ro_options)
            return 1
        for aggregate in [ aggregate for aggregate in manifest.aggregates if pattern.search(str(aggregate.uri)) ]:
            manifest.remove_aggregate(aggregate)
        for annotation in [ annotation for annotation in manifest.annotations if pattern.search(str(annotation.uri)) ]:
            manifest.remove_annotation(annotation)
    else:
        aggregate = manifest.get_aggregate(file_uri_or_pattern)
        if aggregate:
            manifest.remove_aggregate(aggregate)
        annotation = manifest.get_annotation(file_uri_or_pattern)
        if annotation:
            manifest.remove_annotation(annotation)

    with open(manifest_file_path, 'w') as manifest_filehandle:
        manifest_filehandle.write(manifest.to_json())

    return 0

def list(dir):
    """
    List contents of a designated research object

    -a displays files present in directory as well as aggregated resources
    -h includes hidden files in display

    ro list [ -d dir ]
    ro ls   [ -d dir ]
    """

    manifestfilepath = manifest_file(dir)
    if not directory_and_manifest_exist(dir):
        print("Could not find manifest file: {}".format(manifestfilepath))
        return 1

    manifest = Manifest(filename=manifestfilepath)
    print("{} aggregates:".format(manifest.id))
    aggregates = [aggregate.uri for aggregate in manifest.aggregates]
    for aggregate in aggregates:
        print("       {}".format(aggregate))

    return 0

def annotate(dir, file_uri_or_pattern, attributename=None, attributevalue=None, annotation_file_or_uri=None, regexp=False):
    """
    Annotate a specified research object component

    ro annotate file attribute-name [ attribute-value ]
    ro annotation file -f file_or_uri
    """
    manifestfilepath = manifest_file(dir)
    if not directory_and_manifest_exist(dir):
        print("Could not find manifest file: {}".format(manifestfilepath))
        return 1

    manifest = Manifest(filename=manifestfilepath)
    files = []
    if regexp:
        try:
            pattern = re.compile(file_uri_or_pattern)
        except re.error as e:
            #print('''%(rocmd)s remove -w "%(rofile)s" <...> : %(err)s''' % ro_options)
            return 1
        files = [ aggregate for aggregate in manifest.aggregates if pattern.search(str(aggregate.uri)) ]

    else:
        files = [file_uri_or_pattern]

    if annotation_file_or_uri:
        #we are adding an annotation about file_uri_or_pattern using annotation_file_or_uri as the contents of the annotation
        for file in files:
            if os.path.isfile(annotation_file_or_uri):
                if not annotation_file_or_uri.startswith(".ro/annotations/"):
                    annotation_file_or_uri = sanitize_filename_for_identifier(annotation_file_or_uri, dir)
            manifest.add_annotation(about=file, contents=annotation_file_or_uri)

    with open(manifestfilepath, 'w') as manifest_filehandle:
        manifest_filehandle.write(manifest.to_json())


    return 0

def annotations(dir, file=None):
    """
    Display annotations

    ro annotations [ file | -d dir ]
    """
    manifestfilepath = manifest_file(dir)
    if not directory_and_manifest_exist(dir):
        print("Could not find manifest file: {}".format(manifestfilepath))
        return 1

    manifest = Manifest(filename=manifestfilepath)
    print("Annotations:")
    for annotation in manifest.annotations:
        if file and annotation.about and annotation.about != file:
            continue
        print("---")
        print("id:       {}".format(annotation.uri))
        if annotation.about:
            print("about:    {}".format(annotation.about))
        if annotation.contents:
            print("contents: {}".format(annotation.contents))

    return 0

def manifest(dir):
    """
    Dump RDF of manifest
    """
    manifestfilepath = manifest_file(dir)
    if not directory_and_manifest_exist(dir):
        print("Could not find manifest file: {}".format(manifestfilepath))
        return 1

    with open(manifestfilepath) as manifestfile:
        for line in manifestfile:
            print(line,end='')
    print("")
    return 0

def bundle(dir, file):
    """
    Create a Research Object Bundle
    """
    manifestfilepath = manifest_file(dir)
    if not directory_and_manifest_exist(dir):
        print("Could not find manifest file: {}".format(manifestfilepath))
        return 1

    manifest = Manifest(filename=manifestfilepath)
    bundle = Bundle.create_from_manifest(file, manifest)
    bundle.close()


# End.
