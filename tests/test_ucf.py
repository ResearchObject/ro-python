import unittest as unittest
import rolib.ucf
from tests.support import TESTFN, unlink

def get_files(test):
    yield TESTFN2
    with TemporaryFile() as f:
        yield f
        test.assertFalse(f.closed)
    with io.BytesIO() as f:
        yield f
        test.assertFalse(f.closed)

class UCFTestCase(unittest.TestCase):

    empty_file = "test/data/empty"
    zip_file = "test/data/zipfile.zip"
    ucf_file = "test/data/ucffile.ucf"


    def test_open_existing_zip_default_mimetype(self):
    #    with ucf.UCF(zip_file):
    #        pass
        pass

    def test_open_existing_zip_custom_mimetype(self):
        pass

    def test_open_existing_ucf(self):
        pass

    def test_open_nonexistent_file(self):
        pass

    def test_create_new_ucf(self  ):
        pass

    def test_add_mimetype_to_existing_zip(self):
        pass

    def test_set_mimetype_for_existing_ucf(sel):
        pass

    def test_add_file(self):
        pass

    def test_invalid_compression_type(self):
        pass

    def test_filelist_listing(self):
    #    for file in container.infolist():
    #        pass
        pass

    def test_namelist_listing(self):
    #    for name in container.namelist(ignore_reserved=True):
    #        pass
        pass
