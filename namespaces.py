# ro_namespaces.py

"""
Research Object manifest read, write, decode functions
"""

__author__      = "Graham Klyne (GK@ACM.ORG)"
__copyright__   = "Copyright 2011-2013, University of Oxford"
__license__     = "MIT (http://opensource.org/licenses/MIT)"

#import sys
#import os
#import os.path
#import re
#import urlparse
#import logging

import rdflib
from rdflib.namespace import Namespace, ClosedNamespace


oa      = rdflib.URIRef("http://www.w3.org/ns/oa#")
ore     = rdflib.URIRef("http://www.openarchives.org/ore/terms/")
foaf    = rdflib.URIRef("http://xmlns.com/foaf/0.1/")
ro      = rdflib.URIRef("http://purl.org/wf4ever/ro#")
roevo   = rdflib.URIRef("http://purl.org/wf4ever/roevo#")
roterms = rdflib.URIRef("http://purl.org/wf4ever/roterms#")
wfprov  = rdflib.URIRef("http://purl.org/wf4ever/wfprov#")
wfdesc  = rdflib.URIRef("http://purl.org/wf4ever/wfdesc#")
wf4ever = rdflib.URIRef("http://purl.org/wf4ever/wf4ever#")
bundle  = rdflib.URIRef("http://purl.org/wf4ever/bundle#")
dcterms = rdflib.URIRef("http://purl.org/dc/terms/")
pav     = rdflib.URIRef("http://purl.org/pav/")

BUNDLE  = Namespace(bundle)

OA = Namespace(oa)

PAV = Namespace(pav)

RO = ClosedNamespace(ro,
            [ "ResearchObject", "AggregatedAnnotation"
            , "annotatesAggregatedResource"
            ])
ROEVO = ClosedNamespace(roevo,
            [ "LiveRO","SnapshotRO","ArchivedRO","isFinalized"
            ])
ORE = ClosedNamespace(ore,
            [ "Aggregation", "AggregatedResource", "Proxy"
            , "aggregates", "proxyFor", "proxyIn"
            , "isDescribedBy"
            ])

DCTERMS = ClosedNamespace(dcterms,
            [ "identifier", "description", "title", "creator", "created"
            , "subject", "format", "type"
            ])
ROTERMS = ClosedNamespace(roterms,
            [ "note", "resource", "defaultBase"
            ])

# End.
