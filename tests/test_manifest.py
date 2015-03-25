import unittest as unittest

from tests.support import (TESTFN, TESTFN2, unlink, get_files)

from manifest import Manifest, Aggregate

manifest = """
{
    "@context": [
        "https://w3id.org/bundle/context"
    ],
    "id": "/",
    "foaf:homepage": {
        "@id": "http://example.com/bob"
    },
    "foaf:title": "Dr",
    "manifest": "manifest.json",
    "createdOn": "2013-03-05T17:29:03Z",
    "createdBy": {
        "uri": "http://example.com/foaf#alice",
        "orcid": "http://orcid.org/0000-0002-1825-0097",
        "name": "Alice W. Land"
    },
    "history": "evolution.ttl",
    "aggregates": [{
        "uri": "/folder/soup.jpeg"
    }, {
        "uri": "http://example.com/blog/"
    }, {
        "uri": "/README.txt",
        "mediatype": "text/plain",
        "createdBy": {
            "uri": "http://example.com/foaf#bob",
            "name": "Bob Builder"
        },
        "createdOn": "2013-02-12T19:37:32.939Z"
    }, {
        "uri": "http://example.com/comments.txt",
        "bundledAs": {
            "uri": "urn:uuid:a0cf8616-bee4-4a71-b21e-c60e6499a644",
            "folder": "/folder/",
            "filename": "external.txt"
        }
    }],
    "annotations": [{
            "uri": "urn:uuid:d67466b4-3aeb-4855-8203-90febe71abdf",
            "about": "/folder/soup.jpeg",
            "content": "annotations/soup-properties.ttl"
        },

        {
            "about": "urn:uuid:a0cf8616-bee4-4a71-b21e-c60e6499a644",
            "content": "http://example.com/blog/they-aggregated-our-file"
        },

        {
            "about": ["/", "urn:uuid:d67466b4-3aeb-4855-8203-90febe71abdf"],
            "content": "annotations/a-meta-annotation-in-this-ro.txt"
        }
    ]
}
"""
class ManfiestTestCase(unittest.TestCase):

    def setUp(self):
        # Make a source file with some lines
        with open(TESTFN, "w") as fp:
            fp.write(manifest)

    def test_manifest_creation(self):
        m = Manifest()
        self.assertEquals(m.id,"/")
        pass

    def test_manifest_read_from_file_pointer(self):

        with open(TESTFN,'r') as fp:
            m = Manifest(file=fp)

            a = m.get_aggregate("/README.txt")
            self.assertIsNotNone(a)
            self.assertEquals(a, Aggregate("/README.txt"))
            self.assertEquals(m.createdBy.name, "Alice W. Land")
            self.assertEquals(m.createdBy.orcid,"http://orcid.org/0000-0002-1825-0097")
            self.assertEquals(m.createdBy.uri,"http://example.com/foaf#alice")
            m.add_aggregate(Aggregate("www.example.org/test"))
            m.add_aggregate(Aggregate("www.example.org/test",created_by="test"),update=True)


    def test_manifest_read_from_filename(self):
        m = Manifest(filename=TESTFN)

        a = m.get_aggregate("/README.txt")
        self.assertIsNotNone(a)
        self.assertEquals(a, Aggregate("/README.txt"))
        self.assertEquals(m.createdBy.name, "Alice W. Land")
        self.assertEquals(m.createdBy.orcid,"http://orcid.org/0000-0002-1825-0097")
        self.assertEquals(m.createdBy.uri,"http://example.com/foaf#alice")
        m.add_aggregate(Aggregate("www.example.org/test"))
        m.add_aggregate(Aggregate("www.example.org/test",created_by="test"),update=True)


    def test_manifest_add_aggregate(self):
        manifest = Manifest()
        manifest.add_aggregate("/test",createdBy="Alice W.Land", createdOn="2013-03-05T17:29:03Z", mediatype="text/plain")
        contains =  Aggregate("/test") in manifest.aggregates
        self.assertTrue(contains)
        pass

    def test_manifest_add_existing_aggregate(self):
        manifest = Manifest()
        manifest.add_aggregate("/test",createdBy="Alice W.Land", createdOn="2013-03-05T17:29:03Z", mediatype="text/plain")
        manifest.add_aggregate("/test",createdBy="Deckard", createdOn="2013-03-05T17:29:03Z", mediatype="text/plain")

        contains =  Aggregate("/test") in manifest.aggregates
        self.assertTrue(contains)
        a = manifest.get_aggregate("/test")
        self.assertEquals(a.createdBy.name,"Alice W.Land")


    def test_manifest_update_existing_aggregate(self):
        manifest = Manifest()
        manifest.add_aggregate("/test",createdBy="Alice W.Land", createdOn="2013-03-05T17:29:03Z", mediatype="text/plain")
        manifest.add_aggregate("/test",createdBy="Deckard", update=True)

        contains =  Aggregate("/test") in manifest.aggregates
        self.assertTrue(contains)
        a = manifest.get_aggregate("/test")
        self.assertEquals(a.createdBy.name,"Deckard")


    def test_manifest_remove_aggregate(self):
        manifest = Manifest()
        manifest.add_aggregate("/test1",createdBy="Alice W.Land", createdOn="2013-03-05T17:29:03Z", mediatype="text/plain")
        manifest.add_aggregate("/test2",createdBy="Deckard", createdOn="2013-04-03T14:12:55Z", mediatype="text/plain")


        self.assertIn(Aggregate("/test1"), manifest.aggregates)
        manifest.remove_aggregate("/test1")
        self.assertNotIn(Aggregate("/test1"), manifest.aggregates)
        self.assertIn(Aggregate("/test2"), manifest.aggregates)


    def test_manifest_add_annotation(self):
        pass

    def test_manifest_remove_annotation(self):
        pass
