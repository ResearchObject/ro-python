#from test import test_zipfile
import zipext
import zipfile
import unittest
from tempfile import TemporaryFile
from random import randint, random, getrandbits
from tempfile import NamedTemporaryFile
#from test.support import (TESTFN, unlink)
import io
import os

from tests.support import (TESTFN, TESTFN2, unlink, get_files)

class AbstractZipExtTestWithSourceFile:

    @classmethod
    def setUpClass(cls):
        cls.line_gen = [bytes("Zipfile test line %d. random float: %f\n" %
                              (i, random()), "ascii")
                        for i in range(10)]   #test_zipfile.FIXEDTEST_SIZE
        cls.data = b''.join(cls.line_gen)

    def setUp(self):
        # Make a source file with some lines
        with open(TESTFN, "wb") as fp:
            fp.write(self.data)

    def make_test_archive(self, f, compression):
        # Create the ZIP archive
        with zipext.ZipFileExt(f, "w", compression) as zipfp:
            zipfp.write(TESTFN, "another.name")
            zipfp.write(TESTFN, TESTFN)
            zipfp.writestr("strfile", self.data)


    def zip_remove_file_from_existing_test(self,f,compression):
        self.make_test_archive(f,compression)

        with zipext.ZipFileExt(f, "a", compression) as zipfp:

            self.assertEqual(zipfp.read(TESTFN), self.data)
            self.assertEqual(zipfp.read("another.name"), self.data)
            self.assertEqual(zipfp.read("strfile"), self.data)

            zipfp.remove(TESTFN)
            #Check remaining data
            self.assertEqual(zipfp.read("another.name"), self.data)
            self.assertEqual(zipfp.read("strfile"), self.data)
            # Check the namelist
            names = zipfp.namelist()
            self.assertEqual(len(names), 2)
            # Check present files
            self.assertIn("another.name", names)
            self.assertIn("strfile", names)
            # Check removed file
            self.assertNotIn(TESTFN, names)

            # Check infolist
            infos = zipfp.infolist()
            names = [i.filename for i in infos]
            self.assertEqual(len(names), 2)
            self.assertIn("another.name", names)
            self.assertIn("strfile", names)
            self.assertNotIn(TESTFN, names)
            for i in infos:
                self.assertEqual(i.file_size, len(self.data))

        with zipext.ZipFileExt(f, "r", compression) as zipfp:

            #Check remaining data
            self.assertEqual(zipfp.read("another.name"), self.data, "Error reading file: another.name")
            self.assertEqual(zipfp.read("strfile"), self.data,"Error reading file: strfile")

            # Check the namelist
            names = zipfp.namelist()
            self.assertEqual(len(names), 2, "Incorrect number of files in archive namelist - archive has {:d} entries, should be 2".format(len(names)))
            # Check present files
            self.assertIn("another.name", names, "File another.name is missing from archive namelist")
            self.assertIn("strfile", names,"File strfile is missing from archive namelist")
            # Check removed file
            self.assertNotIn(TESTFN, names,"File {:s} should not be present in namelist".format(TESTFN))

            # Check infolist
            infos = zipfp.infolist()
            names = [i.filename for i in infos]
            self.assertEqual(len(names),2,"Incorrect number of files in archive infolist - archive has {:d} entries, should be 2".format(len(names)))
            self.assertIn("another.name", names,"File another.name is missing from archive infolist")
            self.assertIn("strfile", names,"File strfile is missing from archive infolist")
            self.assertNotIn(TESTFN, names,"File {:s} should not be present in infolist".format(TESTFN))
            for i in infos:
                self.assertEqual(i.file_size, len(self.data), "Filesize {:d} is not equal to expected: {:d}".format(i.file_size,len(self.data)))

            # check getinfo
            for nm in ("another.name", "strfile"):
                info = zipfp.getinfo(nm)
                self.assertEqual(info.filename, nm,"Filename {:s} is not equal to expected name: {:s}".format(info.filename,nm))
                self.assertEqual(info.file_size, len(self.data),"Filesize {:d} is not equal to expected: {:d}".format(i.file_size,len(self.data)))

            # Check that testzip doesn't raise an exception
            zipfp.testzip()


    def test_remove_file_from_existing(self):
        for f in get_files(self):
            print("Remove from zipfile of FileType - ", f)
            self.zip_remove_file_from_existing_test(f,self.compression)

    def test_rename_file_in_existing(self):
        for f in get_files(self):
            print("Rename in zipfile of FileType - ", f)
            self.zip_rename_file_in_existing_test(f,self.compression)

    def zip_rename_file_in_existing_test(self, f, compression):
        self.make_test_archive(f,compression)

        with zipext.ZipFileExt(f, "a", compression) as zipfp:
            self.assertEqual(zipfp.read(TESTFN), self.data)
            self.assertEqual(zipfp.read("another.name"), self.data)
            self.assertEqual(zipfp.read("strfile"), self.data)
            TESTFN_NEW = ''.join(["new",TESTFN])
            zipfp.rename(TESTFN,TESTFN_NEW)

            # Check the namelist
            names = zipfp.namelist()
            self.assertEqual(len(names), 3)
            #Check renamed file
            self.assertIn(TESTFN_NEW, names)
            self.assertNotIn(TESTFN, names)
            # Check present files
            self.assertIn("another.name", names)
            self.assertIn("strfile", names)

            #Check remaining data
            self.assertEqual(zipfp.read("another.name"), self.data)
            self.assertEqual(zipfp.read("strfile"), self.data)
            self.assertEqual(zipfp.read(TESTFN_NEW), self.data)

            # Check infolist
            infos = zipfp.infolist()
            names = [i.filename for i in infos]
            self.assertEqual(len(names), 3)
            self.assertIn("another.name", names)
            self.assertIn("strfile", names)
            self.assertIn(TESTFN_NEW, names)

            for i in infos:
                self.assertEqual(i.file_size, len(self.data))

        with zipext.ZipFileExt(f, "r", compression) as zipfp:
            #Check remaining data
            self.assertEqual(zipfp.read("another.name"), self.data)
            self.assertEqual(zipfp.read("strfile"), self.data)
            self.assertEqual(zipfp.read(TESTFN_NEW), self.data)
            # Check the namelist
            names = zipfp.namelist()
            self.assertEqual(len(names), 3)
            #Check renamed file
            self.assertIn(TESTFN_NEW, names)
            self.assertNotIn(TESTFN, names)
            # Check present files
            self.assertIn("another.name", names)
            self.assertIn("strfile", names)

            # Check infolist
            infos = zipfp.infolist()
            names = [i.filename for i in infos]
            self.assertEqual(len(names), 3)
            self.assertIn("another.name", names)
            self.assertIn("strfile", names)
            self.assertIn(TESTFN_NEW, names)
            self.assertNotIn(TESTFN, names)

            for i in infos:
                self.assertEqual(i.file_size, len(self.data))


            # check getinfo
            for nm in ("another.name", "strfile", TESTFN_NEW):
                info = zipfp.getinfo(nm)
                self.assertEqual(info.filename, nm)
                self.assertEqual(info.file_size, len(self.data))

            # Check that testzip doesn't raise an exception
            zipfp.testzip()

    def test_remove_nonexistent_file(self):
        pass

    def tearDown(self):
        unlink(TESTFN)
        unlink(TESTFN2)


class StoredZipExtTestWithSourceFile(AbstractZipExtTestWithSourceFile,unittest.TestCase):

    compression = zipfile.ZIP_STORED