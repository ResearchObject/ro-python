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
import codecs

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

from namespaces import RO, OA, ORE, BUNDLE, PAV


log = logging.getLogger(__name__)


__author__ = "Matthew Gamble"
__copyright__ = "Copyright 2015 University of Manchester"
__license__ = "MIT (http://opensource.org/licenses/MIT)"


class ProvenancePropertiesMixin(object):


    def get_property(self, property):
        return self.__dict__[property]

    def set_property(self, property, value):
        self.___dict__[property] = value

    @property
    def authoredOn(self):
        return self.get_property("authoredOn")

    @property
    def createdOn(self):
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
        self.set_property("createdOn",timestamp.isoformat())


class JSONLDObject(SimpleNamespace, object):
    """
    A class that provides attribute based access to an instances __dict__

    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        #self.__getattribute__ = JSONLDObject.__getattribute__

    @classmethod
    def register_class_for_property(cls , property, newCls):
        pass

    @property
    def context(self):
        return self.__dict__["@context"]

    @context.setter
    def context(self, value):
        self.__dict__["@context"] = value


    def __getattribute__(self, attr):
        """

        """
        map = {"annotations": Annotation,"aggregates": Aggregate, "authoredBy": Agent, "createdBy": Agent, "curatedBy": Agent, "contributedBy": Agent, "retrievedBy": Agent}

        if(attr in map.keys()):
            cls = map[attr]
            value = super().__getattribute__(attr)
            if value is not None:
                if isinstance(value,list):
                    #use a copy of the list being returned as we might be modifying it
                    for i in list(value):
                        if not isinstance(i,cls):
                            #Objectify the value and replace original with objectified
                            #version in the __dict__
                            object = cls(**i)#TODO might not be a dict
                            value.remove(i)
                            value.append(object)
                elif not isinstance(value,cls):
                    try:
                        value = cls(**value)
                    except TypeError:
                        value = cls(value)
                    self.__setattr__(attr,value)
            return value
        else:
            return super().__getattribute__(attr)


    def populated(self):
        """
        Return a dictionary of all of the objects attributes that have been
        populated i.e. where the value in the key value pair is not None
        """
        return {key: value for (key,value) in self.__dict__.items() if value is not None}


class ManifestEntry(JSONLDObject):

    #Does this need to be ab Abstract Base Class anymore?
    __metaclass__ = ABCMeta

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        #make a check to ensure that they each have a uri - if not then generate
        #one?

    @property
    def uri(self):
        return self.id

    @uri.setter
    def uri(self, uri):
        self.id = uri

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, rhs):
        return self.id.__eq__(rhs.id)


class Agent(ManifestEntry):
    pass

class Aggregate(ManifestEntry, ProvenancePropertiesMixin):

    def __init__(self, uri, createdBy=None, createdOn=None, mediatype=None, **kwargs):
        #do whatever initialization of properties we need to here
        super(Aggregate, self).__init__(id=uri, createdBy=createdBy, mediatype=mediatype, **kwargs)


class Annotation(ManifestEntry, ProvenancePropertiesMixin):

    def __init__(self, uri=None, target=None, body=None, **kwargs):
        super().__init__(uri=uri, target=target, body=body, **kwargs)


class Manifest(ManifestEntry, ProvenancePropertiesMixin):

    def __init__(self, filename=None, file=None, contents=None, format="json-ld"):

        self.id = "/"
        self.aggregates = []
        self.annotates = []
        if filename is not None:
            with open(filename) as file:
                contents = json.load(file)
        elif file is not None:
            with file:
                reader = codecs.getreader('UTF-8')
                contents = json.load(reader(file))
        if contents is not None:
            super(Manifest, self).__init__(**contents)


    def to_json(self):
        return json.dumps(self.__dict__, indent=4, cls=ManifestEncoder)


    def get_aggregate(self, uri):
        for a in self.aggregates:
            if(a.uri == uri):
                return a


    def add_aggregate(self,aggregate, update=False):
        """
        Adds the aggregate to the list of Aggregates.
        If an aggregate with the same id already exists:
         If update is False (default) then the add is ignored
         If update is True then the existing one will be overwritten

        """
        if update:
            if aggregate in self.aggregates:
                self.remove_aggregate(aggregate.uri)
                self.aggregates.append(aggregate)
        else:
            if aggregate not in self.aggregates:
                self.aggregates.append(aggregate)

    def remove_aggregate(self,aggregate_or_uri, remove_annotations=False):
        if isinstance(aggregate_or_uri,str):
            aggregate_or_uri = Aggregate(aggregate_or_uri)
        self.aggregates.remove(aggregate_or_uri)
        if remove_annotations:
            remove_annotations_for(aggregate_or_uri)

    def add_annotation(self, annotation):
        if annotation not in self.annotations:
            self.annotations.append(annotation)

    def remove_annotation(self, annotation_or_uri):
        if isinstance(annotation_or_uri,str):
            annotation_or_uri = Annotation(uri=annotation_or_uri)
        self.annotations.remove(annotation_or_uri)

    def remove_annotations_for(self, manifest_entry):
        """
        Remove any annotations that have this manifest_entry as a target
        """
        for a in list(self.annotations):
            if a.target == manifest_entry.id:
                self.remove_annotation(a)

class ManifestEncoder(json.JSONEncoder):
    """
    Custom JSONEncoder for any object that is a subclass of ManifestEntry that
    returns the Objects __dict__
    """
    def default(self, obj):
        if isinstance(obj, ManifestEntry):
            return obj.populated()
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
    creator.name = "A different name"
    print(creator)

    m.add_aggregate(Aggregate("www.example.org/test"))
    m.add_aggregate(Aggregate("www.example.org/test",created_by="test"),update=True)
#   print(m.to_json())

#   print(m.foaf:title)
#   print m.curated_on
    print(m.to_json())

if __name__ == "__main__":
    main()
