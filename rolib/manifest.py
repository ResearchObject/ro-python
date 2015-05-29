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
from datetime import datetime
import codecs
import uuid


try:
    from types import SimpleNamespace
except ImportError:
    from rolib.packages.simplenamespace import SimpleNamespace

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

#from namespaces import RO, OA, ORE, BUNDLE, PAV


log = logging.getLogger(__name__)


__author__ = "Matthew Gamble"
__copyright__ = "Copyright 2015 University of Manchester"
__license__ = "MIT (http://opensource.org/licenses/MIT)"


class ProvenancePropertiesMixin(object):


    def get_property(self, property):
        try:
            return self.__dict__[property]
        except KeyError:
            return None

    def set_property(self, property, value):
        self.__dict__[property] = value

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
        if hasattr(timestamp,'isoformat'):
            timestamp = timestamp.isoformat()
        self.set_property("createdOn",timestamp)

    @property
    def createdBy(self):
        return self.__dict__["createdBy"]

    @createdBy.setter
    def createdBy(self, creator):
        if isinstance(creator,Agent):
            self.__dict__["createdBy"] = creator
        else:
            self.__dict__["createdBy"] = Agent(creator)


class JSONLDObject(SimpleNamespace, object):
    """
    A class that provides attribute based access to an instances __dict__

    """
    def __init__(self, **kwargs):
        super(JSONLDObject, self).__init__(**kwargs)
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
            value = super(JSONLDObject, self).__getattribute__(attr)
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
            return super(JSONLDObject, self).__getattribute__(attr)


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
        super(ManifestEntry, self).__init__(**kwargs)
        #make a check to ensure that they each have a uri - if not then generate
        #one?

    @property
    def id(self):
        return self.uri

    @id.setter
    def id(self, id):
        self.uri = id

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, rhs):
        return self.id.__eq__(rhs.id)


class Agent(ManifestEntry):

    def __init__(self, name, uri=None, orcid=None, **kwargs):
        super(Agent, self).__init__(name=name,uri=uri,orcid=orcid,**kwargs)

    @property
    def id(self):
        id = self.uri or self.name
        return id

    @id.setter
    def id(self, id):
        self.uri = id


class Aggregate(ManifestEntry, ProvenancePropertiesMixin):

    def __init__(self, uri, createdBy=None, createdOn=None, mediatype=None, **kwargs):
        #do whatever initialization of properties we need to here
        super(Aggregate, self).__init__(uri=uri, createdBy=createdBy, mediatype=mediatype, **kwargs)


class Annotation(ManifestEntry, ProvenancePropertiesMixin):

    def __init__(self, uri=None, about=None, contents=None, **kwargs):
        if not uri:
            uri = uuid.uuid4().urn
        super().__init__(uri=uri, about=about, contents=contents, **kwargs)


class Manifest(ManifestEntry, ProvenancePropertiesMixin):

    def __init__(self, id="/", filename=None, file=None, contents=None, format="json-ld"):

        self.id = id
        self.aggregates = []
        self.annotations = []
        if filename is not None:
            with open(filename) as file:
                contents = json.load(file)
        elif file is not None:
            with file:
                data = file.read()
                if isinstance(data,bytes):
                    data = data.decode('UTF-8')
                contents = json.loads(data)
        if contents is not None:
            super(Manifest, self).__init__(**contents)


    def to_json(self):
        return json.dumps(self.__dict__, indent=4, cls=ManifestEncoder)


    def get_aggregate(self, uri):
        for a in self.aggregates:
            if(a.uri == uri):
                return a

    def get_annotation(self, uri):
        for a in self.annotations:
            if(a.uri == uri):
                return a


    def add_aggregate(self, aggregate_or_uri, createdBy=None, createdOn=None, mediatype=None):
        """
        Adds the aggregate to the list of Aggregates.
        If an aggregate with the same id already exists then the old aggregate
        is replaced.
        """

        if isinstance(aggregate_or_uri, Aggregate):
            aggregate = aggregate_or_uri
        else:
            aggregate = Aggregate(aggregate_or_uri)

        aggregate.createdBy = createdBy or aggregate.createdBy
        aggregate.createdOn = createdOn or aggregate.createdOn
        aggregate.mediatype = mediatype or aggregate.mediatype
        self.remove_aggregate(aggregate)
        self.aggregates.append(aggregate)



    def remove_aggregate(self, aggregate_or_uri, remove_annotations=False):
        if isinstance(aggregate_or_uri, str):
            aggregate = Aggregate(aggregate_or_uri)
        else:
            aggregate = aggregate_or_uri
        if aggregate in self.aggregates:
            self.aggregates.remove(aggregate)
        if remove_annotations:
            remove_annotations_for(aggregate)

    def add_annotation(self, annotation_or_uri=None, about=None, contents=None):

        if annotation_or_uri:
            if isinstance(annotation_or_uri,str):
                annotation = Annotation(uri=annotation_or_uri)
            else:
                annotation = annotation_or_uri
        else:
            annotation = Annotation()

        annotation.about = about or annotation.about
        annotation.contents = contents or annotation.contents

        if annotation not in self.annotations:
            self.annotations.append(annotation)

    def remove_annotation(self, annotation_or_uri):
        if isinstance(annotation_or_uri,str):
            annotation = Annotation(uri=annotation_or_uri)
        else:
            annotation = annotation_or_uri
            
        self.annotations.remove(annotation)

    def remove_annotations_for(self, manifest_entry):
        """
        Remove any annotations that have this manifest_entry as the about
        """
        for a in list(self.annotations):
            if a.about == manifest_entry.id:
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


#def notHidden(f):
#    return re.match("\.|.*/\.", f) == None


def main():

    with open("bundle.json") as fp:
        m = Manifest(file=fp)

        for a in m.aggregates:
            print(a)

        for a in m.annotations:
            print(a)

        for a in m.annotations:
            a.content = "test"

        for a in m.annotations:
            print(a)

        m.uri = "http://www.example.org/manifest"

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
