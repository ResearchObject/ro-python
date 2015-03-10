#!/usr/local/bin/python3
# ro_manifest.py
"""Research Object manifest read, write, decode functions
"""
import sys
import os
import os.path
import json
import re
import logging
import ssl
from abc import ABCMeta
from types import SimpleNamespace
from datetime import time

try:
    import urllib.parse
except ImportError:
    import urlparse
import urllib

import rdflib
from rdflib.plugin import register, Parser
register('json-ld', Parser, 'rdflib_jsonld.parser', 'JsonLDParser')
from rdflib.term import URIRef
from rdflib.namespace import RDF, DCTERMS

import pyld as pyld
from pyld import jsonld
from pyld.jsonld import JsonLdProcessor

from namespaces import RO, OA, ORE, BUNDLE, PAV


log = logging.getLogger(__name__)


__author__ = "Matthew Gamble"
__copyright__ = "Copyright 2015 University of Manchester"
__license__ = "MIT (http://opensource.org/licenses/MIT)"


class ProvenancePropertiesMixin(object):

    def __getattribute__(self,name):
        print("getattribute")
        if(name in ["authoredBy", "createdBy", "curatedBy", "contributedBy", "retrievedBy"]):
            for agent in list(super().__getattribute___(self,name)):
                if isinstance(agent,Agent):
                    return Agent
                else:
                    return Agent(**agent)


    def get_property(self, property):
        return self.__dict__[property]

    def set_property(self, property, value):
        self.___dict__[property] = value

    @property
    def authoredOn(self):
        return self.get_property("authoredOn")

    @property
    def createdOn(self):
        print("hello")
        return self.get_property("createdOn")


    @property
    def curatedOn(self):
        return self.get_property("curatedOn")

    @property
    def contributedOn(self):
        return self.get_property("contributedOn")


    @property
    def retrievedOn(self):
        return self.get_property("retrievedOn")

    @createdOn.setter
    def createdOn(self, timestamp):
        if self._id is not None:
            self._graph(add((self._id, PAV.createdOn, timestamp.isoformat())))


class JSONLDObject(object):

    @property
    def context(self):
        return self.__dict__["@context"]

    @context.setter
    def context(self, value):
        self.__dict__["@context"] = value


class ManifestEntry(SimpleNamespace, JSONLDObject):

    #Does this need to be ab Abstract Base Class anymore?
    __metaclass__ = ABCMeta

    def __init__(self, **kwargs):
        super(ManifestEntry, self).__init__(**kwargs)

    @property
    def uri(self):
        return self.id

    @uri.setter
    def uri(self, uri):
        #TODO validate to ensure that it is a valid URI etc.?
        self.id = uri

class Agent(ManifestEntry):
    pass

class Aggregate(ManifestEntry, ProvenancePropertiesMixin):

    def __init__(self, uri, createdBy=None, createdOn=None, mediatype=None, **kwargs):
        #do whatever initialization of properties we need to here
        super(Aggregate, self).__init__(id=uri, createdBy=createdBy, mediatype=mediatype, **kwargs)
        self.__getattribute__ = ProvenancePropertiesMixin.__getattribute__


class Annotation(ManifestEntry, ProvenancePropertiesMixin):

    def __init__(self, uri=None, target=None, body=None, **kwargs):
        super(Annotation, self).__init__(uri=uri, target=target, body=body, **kwargs)


    @property
    def about(self):
        return self.about

    @about.setter
    def about(self, value):
        self.about = value

    @property
    def content(self):
        return self.content

    @content.setter
    def content(self, value):
        self.__dict__["content"] = value


class Manifest(ManifestEntry, ProvenancePropertiesMixin):

    def __init__(self, filename=None, contents=None, format="json-ld"):

        self.id = "/"

        if filename is not None:
            log.debug("Manifest read: "+filename)
            with open(filename) as file:
                contents = json.load(file)
        if contents is not None:
            super(Manifest, self).__init__(**contents)
        if self.annotations is not None:
           self.__dict__["annotations"] = [Annotation(**a) for a in self.annotations]
        if self.aggregates is not None:
           self.__dict__["aggregates"] = [Aggregate(**a) for a in self.aggregates]


    def to_json(self):
        return json.dumps(self.__dict__, indent=4, cls=ManifestEncoder)


    @property
    def aggregates(self):
        """
        Returns generator over all Aggregates aggregated by this manifest.
        """
        #log.debug("getAggregatedResources %s"%str(self._id))
        for a in self.__dict__["aggregates"]:
            yield a

    def get_aggregate(self, uri):
        for a in self.aggregates:
            if(a.uri == uri):
                return a


    def add_aggregate(self):
        #check for duplicate annotation based upon uri
        pass

    @property
    def annotations(self):
        """
        Returns generator over all Annotations aggregated by this manifest.
        """
        #log.debug("getAllAnnotations %s"%str(self._id))
        for a in self.__dict__["annotations"]:
            yield a


    def add_annotation(self, annotation):
        pass


class ManifestEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ManifestEntry):
            return obj.__dict__
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)

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

    m.help = "test"
    for a in m.aggregates:
        print(a)

    for a in m.annotations:
        print(a)

    for a in m.annotations:
        a.content = "test"

    for a in m.annotations:
        print(a)

    m.uri = "http://www.example.org/crap"

    print(m.uri)
    print(m.createdOn)

    context = "@context"
    print(m.context)

    print(m.__dict__["@context"])


    a = m.get_aggregate("/README.txt")
    print(a)
    creator = a.createdBy
    print(creator)

    tp = type(a)
    print(tp)
    print(tp.mro())



#    print(m.to_json())

#    print(m.foaf:title)
#    print m.curated_on
#    print m.to_json()

if __name__ == "__main__":
    main()
