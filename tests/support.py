import os
import io
from tempfile import NamedTemporaryFile, TemporaryFile
import unittest

TESTFN = '@test'
TESTFN = "{}_{}_tmp".format(TESTFN, os.getpid())

TESTFN2 = TESTFN + "2"

def unlink(filename):
    try:
        os.unlink(filename)
    except (FileNotFoundError, NotADirectoryError):
        pass

def get_files(test):
    yield TESTFN2
    with TemporaryFile() as f:
        yield f
        test.assertFalse(f.closed)
    with io.BytesIO() as f:
        yield f
        test.assertFalse(f.closed)
