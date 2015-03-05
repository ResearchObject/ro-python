#!/usr/bin/python
# ro_manifest.py

"""
Research Object manifest read, write, decode functions
"""

__author__      = "Matthew Gamble"
__copyright__   = "Copyright 2015 University of Manchester"
__license__     = "MIT (http://opensource.org/licenses/MIT)"

import sys
import os
import os.path
import json
import re
import urlparse
import urllib
import logging
import ssl

from urllib2 import build_opener as urllib_build_opener
from urllib2 import HTTPSHandler
import urlparse as urllib_parse
from httplib import HTTPSConnection

from rdflib.plugin import register,Parser
register('json-ld',Parser,'rdflib_jsonld.parser', 'JsonLDParser')

from rdflib.term import URIRef

log = logging.getLogger(__name__)

#import MiscUtils.ScanDirectories

import rdflib
###import rdflib.namespace
#from rdflib import URIRef, Namespace, BNode
#from rdflib import Literal

import pyld as pyld
from pyld import jsonld
from pyld.jsonld import JsonLdProcessor

from rdflib.namespace import RDF, DCTERMS
from .namespaces import RO, OA, ORE, BUNDLE, PAV

class ProvenancePropertiesMixin(object):

    @property
    def authored_by(self):
        return get_property(PAV.authoredBy)

    @property
    def authored_on(self):
        return get_property(PAV.authoredOn)

    @property
    def created_by(self):
        return get_property(PAV.createdBy)

    @property
    def created_on(self):
        return get_property(PAV.createdOn)

    @property
    def curated_by(self):
        return get_property(PAV.curatedBy)

    @property
    def curated_on(self):
        return get_property(PAV.curatedOn)

    @property
    def contributed_by(self):
        return get_property(PAV.contributedBy)

    @property
    def contributed_on(self):
        return get_property(PAV.contributedOn)

    @property
    def retrievedBy(self):
        return get_property(PAV.retrievedBy)

    @property
    def retrievedOn(self):
        return get_property(PAV.retrievedOn)

    def get_property(self,property):
        return self._graph.value(self._id, property, None)

    def set_property(self,property):
        return self._graph.set(self._id, property, None)

class Manifest(ProvenancePropertiesMixin):
    """Manifest Class

    Attributes:


    """

    def __init__(self,filename=None,format="json-ld"):
        if filename is None:
            self._graph = rdflib.Graph()
            self._id = None
        else:
            self.read(filename,format=format)

    def read(self, filename, format="json-ld"):
        log.debug("readFromJson: "+filename)
        self._graph = rdflib.Graph()
        self._graph.parse(filename, format=format)
        self._id  = self._graph.value(None, RDF.type, RO.ResearchObject)


    def write(self, filename, format="json-ld"):
        self._graph.serialize(destination=filename, format=format, base=getRoUri(rodir))
        return

    @property
    def uri(self):
        return self._id

    @uri.setter
    def uri(self,uri):
        uri = URIRef(uri)
        self._graph.remove((self._id,RDF.type,RO.ResearchObject))
        self._graph.add((uri,RDF.type,RO.ResearchObject))
        self._id = uri;

    @property
    def created_on(self):
        return self._graph.value(self._id, PAV.createdOn, None)

    @created_on.setter
    def created_on(self,timestamp):
        if self._id is not None:
            self._graph(add((self._id,PAV.createdOn,timestamp.isoformat())))



#    'rotitle':        rdfGraph.value(subject, DCTERMS.title,       None),
#    'rocreator':      rdfGraph.value(subject, DCTERMS.creator,     None),
#    'rocreated':      rdfGraph.value(subject, DCTERMS.created,     None),
#    'rodescription':  rdfGraph.value(subject, DCTERMS.description, None),

    def aggregates(self):
        """
        Returns iterator over all resources aggregated by a manifest.
        """
        #log.debug("getAggregatedResources %s"%str(self._id))
        for r in self._graph.objects(subject=self._id, predicate=ORE.aggregates):
            yield r


    def annotations(self):
        """
        Returns iterator over all annotations in this manifest
        """

        #log.debug("getAllAnnotations %s"%str(self._id))
        for r in self._graph.objects(subject=self._id, predicate=BUNDLE.hasAnnotation):
            yield r


    def add_aggregated_resource(self,uri,createdBy=None,createdOn=None,mediatype=None):
        pass

class Aggregate(object):
    pass



def readManifest(rodir):
    """
    Read manifest file for research object, return dictionary of manifest values.
    """
    rdfGraph = readManifestGraph(rodir)
    subject  = rdfGraph.value(None, RDF.type, RO.ResearchObject)
    strsubject = ""
    if isinstance(subject, rdflib.URIRef): strsubject = str(subject)
    manifestDict = {
        'ropath':         rodir,
        'rouri':          strsubject,
        'roident':        rdfGraph.value(subject, DCTERMS.identifier,  None),
        'rotitle':        rdfGraph.value(subject, DCTERMS.title,       None),
        'rocreator':      rdfGraph.value(subject, DCTERMS.creator,     None),
        'rocreated':      rdfGraph.value(subject, DCTERMS.created,     None),
        'rodescription':  rdfGraph.value(subject, DCTERMS.description, None),
        }
    return manifestDict


def addAggregatedResources(ro_dir, ro_file, recurse=True):
    log.debug("addAggregatedResources: dir %s, file %s"%(ro_dir, ro_file))
    ro_graph = readManifestGraph(ro_dir)
    if ro_file.endswith(os.path.sep):
        ro_file = ro_file[0:-1]
    rofiles = [ro_file]
    #if os.path.isdir(ro_file):
#        rofiles = filter( notHidden,
#                            MiscUtils.ScanDirectories.CollectDirectoryContents(
#                                os.path.abspath(ro_file), baseDir=os.path.abspath(ro_dir),
#                                listDirs=False, listFiles=True, recursive=recurse, appendSep=False)
#                        )
    s = getComponentUri(ro_dir, ".")
    for f in rofiles:
        log.debug("- file %s"%f)
        stmt = (s, ORE.aggregates, getComponentUri(ro_dir, f))
        if stmt not in ro_graph: ro_graph.add(stmt)
    writeManifestGraph(ro_dir, ro_graph)
    return

def getAggregatedResources(ro_dir):
    """
    Returns iterator over all resources aggregated by a manifest.

    Each value returned by the iterator is a resource URI.
    """
    ro_graph = readManifestGraph(ro_dir)
    subject  = getRoUri(ro_dir)
    log.debug("getAggregatedResources %s"%str(subject))
    for r in ro_graph.objects(subject=subject, predicate=ORE.aggregates):
        yield r
    return

def getFileUri(path):
    """
    Like getComponentUri, except that path may be relative to the current directory
    """
    filebase = "file://"
    if not path.startswith(filebase):
        path = filebase+os.path.join(os.getcwd(), path)
    return rdflib.URIRef(path)

def getUriFile(uri):
    """
    Return file path string corresponding to supplied RO or RO component URI
    """
    filebase = "file://"
    uri = str(uri)
    if uri.startswith(filebase):
        uri = uri[len(filebase):]
    return uri

def getRoUri(roref):
    uri = roref
    if urlparse.urlsplit(uri).scheme == "":
        base = "file://"+urllib.pathname2url(os.path.abspath(os.getcwd()))+"/"
        uri  = urlparse.urljoin(base, urllib.pathname2url(roref))
    if not uri.endswith("/"): uri += "/"
    return rdflib.URIRef(uri)

def getComponentUri(ro_dir, path):
    """
    Return URI for component where relative reference is treated as a file path
    """
    if urlparse.urlsplit(path).scheme == "":
        path = urlparse.urljoin(str(getRoUri(ro_dir)), urllib.pathname2url(path))
    return rdflib.URIRef(path)

def getComponentUriAbs(ro_dir, path):
    """
    Return absolute URI for component where relative reference is treated as a URI reference
    """
    return rdflib.URIRef(urlparse.urljoin(str(getRoUri(ro_dir)), path))

def getComponentUriRel(ro_dir, path):
    #log.debug("getComponentUriRel: ro_dir %s, path %s"%(ro_dir, path))
    file_uri = urlparse.urlunsplit(urlparse.urlsplit(str(getComponentUriAbs(ro_dir, path))))
    ro_uri   = urlparse.urlunsplit(urlparse.urlsplit(str(getRoUri(ro_dir))))
    #log.debug("getComponentUriRel: ro_uri %s, file_uri %s"%(ro_uri, file_uri))
    if ro_uri is not None and file_uri.startswith(ro_uri):
        file_uri_rel = file_uri.replace(ro_uri, "", 1)
    else:
        file_uri_rel = path
    #log.debug("getComponentUriRel: file_uri_rel %s"%(file_uri_rel))
    return rdflib.URIRef(file_uri_rel)

def getGraphRoUri(rodir, rograph):
    """
    Extract graph URI from supplied manifest graph
    """
    return rograph.value(None, RDF.type, RO.ResearchObject)


#def notHidden(f):
#    return re.match("\.|.*/\.", f) == None


def main():

    m = Manifest("bundle.json")
    for a in m.aggregates():
        print a

    print PAV.test

    m.uri = "http://www.example.org/crap"


    print m.uri
    print m.created_on

if __name__ == "__main__":
    main()
