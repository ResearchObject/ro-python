import io
import os
import zipfile
import datetime
import tempfile
import binascii

from zipext import ZipFileExt

META_INF_DIR = "META-INF"
MIMETYPE_FILE = "mimetype"
MIMETYPE_FILE_OFFSET = 0
DEFAULT_MIMETYPE = "application/epub+zip"
VALID_COMPRESSION = [zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED]

DEFAULT_RESERVED_FILES = [ MIMETYPE_FILE,
                     META_INF_DIR+"/container.xml",
                     META_INF_DIR+"/manifest.xml",
                     META_INF_DIR+"/metadata.xml",
                     META_INF_DIR+"/signatures.xml",
                     META_INF_DIR+"/encryption.xml",
                     META_INF_DIR+"/rights.xml",
                   ]

DEFAULT_RESERVED_DIRECTORIES = [ META_INF_DIR ]


class UCF(ZipFileExt):

    def __init__(self, file, mode="r", compression=zipfile.ZIP_STORED, allowZip64=True,mimetype=None):
        """
        Class with methods to open, read, write, close, and list Universal Container Format (UCF) files.

        u = UCF(file,mode="r", compression=ZIP_STORED, allowZip64=True, mimetype="application/epub+zip")

        The UCF specifiaction is an extension of the Zipfile format. The UCF module therefore
        extends and provides the same interface as Python's standard zipfile.ZipFile
        module. A UCF file can therefore be treated as a ZipFile like object.

        file: Either the path to the file, or a file-like object.
              If it is a path, the file will be opened and closed by UCF.

        mode: The mode can be either read "r", write "w" or append "a".

        compression: The compression type to be used for this archive.
                     The UCF specification supports two compression types defined
                     in the zipfile module as - zipfile.ZIP_STORED (no compression),
                     zipfile.ZIP_DEFLATED (requires zlib).


        allowZip64: if True ZipFile will create files with ZIP64 extensions when
                    needed, otherwise it will raise an exception when this would
                    be necessary.

        mimetype:   Defines the mimetype for the UCF container.
                    If the mimetype parameter is not defined, the mimetype will
                    be read from the archive.
                    If the mode parameter is 'r' the mimetype parameter will be
                    ignored and read from the archive.
        """
        self._check_compression_type(compression)
        super().__init__(file,mode=mode,compression=compression,allowZip64=allowZip64)
        if mode == 'r':
            self.mimetype = self.verify_mimetype()
        elif mimetype:
            self.mimetype = mimetype
        else:
            try:
                self.mimetype = self.verify_mimetype()
            except MissingMimetypeFileException:
                self.mimetype = DEFAULT_MIMETYPE

        self._reserved_files = DEFAULT_RESERVED_FILES
        self._reserved_dirs = DEFAULT_RESERVED_DIRECTORIES

        print(self._allowZip64)

    def set_mimetype(self, mimetype=None):
        self.mimetype = mimtype or self.mimetype
        #Remove any leading whitespace - prohibited by the UCF spec
        self.mimetype.lstrip()
        self._add_mimetype_file()

    def verify_mimetype(self):
        if 'mimetype' not in self.namelist():
            raise MissingMimetypeFileException("Mimetype file is missing.")
        fileinfo = self.getinfo('mimetype')
        if fileinfo.header_offset != MIMETYPE_FILE_OFFSET:
            raise BadUCFFileException("Mimetype file must be the first file in the archive")
        if fileinfo.compress_type != zipfile.ZIP_STORED:
            raise BadUCFFileException("Mimetype is compressed. Mimetype file must be stored uncompressed.")
        mimetype = self.read('mimetype')
        mimetype = mimetype.decode(encoding='ascii')
        return mimetype

    def write(self, filename, arcname=None, compress_type=None):
        if arcname is None:
            arcname = filename
        _check_compression_type(compress_type)
        super().write(filename=filename,arcname=arcname,compress_type=compress_type)

    def writestr(self, zinfo_or_arcname, data, compress_type=None):
        if isinstance(zinfo_or_arcname, zipfile.ZipInfo):
            filename = zinfo_or_arname.filename
        else:
            filename = zinfo_or_arcname
        #Check that this is not a reserved filename or in a reserved directory
        if filename in self._reserved_files:
            raise ReservedFileNameException()

        super().writestr(zinfo_or_arcname,data,compress_type=compress_type)

    @classmethod
    def from_zipfile(cls,file, compression=zipfile.ZIP_STORED, allowZip64=True,mimetype=None):
        """
        Creates a new UCF file from an existing valid zipfile.
        """
        pass

    @classmethod
    def _check_compression_type(cls,compress_type):
        if compress_type not in VALID_COMPRESSION:
            raise UnsupportedCompressionException("Unsupported Compression type: Compression must be Zip_STORED or ZIP_DEFLATED")

    def _register_reserved_file(filename):
        pass

    def _register_reserved_directory(dirname):
        pass

    def _add_mimetype_file(self):
        """
        The UCF specification requires a mimetype file to included as an
        uncompressed, unencrypted file as the *first entry* in the Zip archive.
        The contents of this file are the media type of the file as an ASCII
        string, with no preceeding space.
        """
        ascii_value = self.mimetype.encode('ascii')
        if not self.namelist():
            #If the archive is empty then we're in luck - we can just
            #write the file at the top
            super().writestr('mimetype',ascii_value,compress_type=None)
            return
        else:
            #The archive isn't empty - but we need the mimetype file
            #to be the first entry in the archive. Updating zip archives
            #in place isn't really an option. We therefore need to
            #create a temporary new archive, copy everything over and
            #then switch it in when that has completed successfully.
            #This is how zip -u works?
            self.commit()

    def commit(self):

        with UCF(tempfile.NamedTemporaryFile(delete=False),mode="w") as temp_ucf:
            temp_ucf._add_mimetype_file()
            for name in self.namelist():
                bytes = self.read(name)
                temp_ucf.writestr(name,bytes)
            badfile = temp_ucf.testzip()
        if(badfile):    #retry?
            raise BadUCFFile("Error when creating mimetype file Bad UCF file generated (failed zipfile.test_zip()): file is corrupt")
        else:
            #mv self.filename to old_temp, new to self.filename, and then remove old_temp
            #TODO check: The filenames here should always be absolute?
            old_temp = tempfile.NamedTemporaryFile(delete=False)
            os.rename(self.filename,old_temp.name)
            os.rename(temp_ucf.filename,self.filename)
            #TODO instead of reusing __init__ it would be nicer to establish
            #what really needs doing to reset. This would however likely result
            #in code duplication from zipfile.ZipFile's init method.
            #Really we need a reset function in zipfile.
            self.__init__(file=self.filename,mode='r',compression=self.compression,allowZip64=self._allowZip64,mimetype=self.mimetype)



    def namelist(self,ignore_reserved=False):
        """
        Return a list of file names in the archive.
        Reserved files can be omitted from the list by setting ingore_reserved
        to True.
        """
        namelist = [data.filename for data in self.filelist]
        if ignore_reserved:
            namelist = [filename for filename in namelist if filename not in self._reserved_files]
        return namelist

    def infolist(self,ignore_reserved=False):
        """Return a list of class ZipInfo instances for files in the
        archive.
        Reserved files can be omitted from the list by setting ingore_reserved
        to True.
        """
        filelist = self.filelist
        if ignore_reserved:
            filelist = [file for file in filelist if file.filename not in self._reserved_files]
        return filelist

class UCFException(Exception):
    pass

class BadUCFFileException(UCFException):
    pass

class MissingMimetypeFileException(BadUCFFileException):
    pass

class ReservedFileNameException(UCFException):
    pass

class UnsupportedCompressionException(UCFException):
    pass


def print_info(archive_name):
    zf = zipfile.ZipFile(archive_name)
    for info in zf.infolist():
        print(info.filename)
        print( '\tComment:\t', info.comment)
        print( '\tModified:\t', datetime.datetime(*info.date_time))
        print( '\tSystem:\t\t', info.create_system, '(0 = Windows, 3 = Unix)')
        print( '\tZIP version:\t', info.create_version)
        print( '\tCompressed:\t', info.compress_size, 'bytes')
        print( '\tUncompressed:\t', info.file_size, 'bytes')
        print( '\tCompression Type\t', info.compress_type)
        print( '\tHeader offset\t', info.header_offset)

        print()


import unittest as unittest

class UCFTestCase(unittest.TestCase):

    empty_file = "test/data/empty"
    zip_file = "test/data/zipfile.zip"
    ucf_file = "test/data/ucffile.ucf"


    def test_open_existing_zip_default_mimetype():
        with UCF(zip_file):
            pass
        pass

    def test_open_existing_zip_custom_mimetype():
        pass

    def test_open_existing_ucf():
        pass

    def test_open_nonexistent_file():
        pass

    def test_create_new_ucf():
        pass

    def test_add_mimetype_to_existing_zip():
        pass

    def test_set_mimetype_for_existing_ucf():
        pass

    def test_add_file():
        pass

    def test_invalid_compression_type():
        pass

    def test_filelist_listing():
        for file in container.infolist():
            pass
        pass

    def test_namelist_listing():
        for name in container.namelist(ignore_reserved=True):
            pass
        pass

def main():
    filename = '/tmp/test.zip'
    mimetype = "application/vnd.wf4ever.robundle+zip"
    print(zipfile.is_zipfile(filename))
    with UCF(filename,mode='a') as container:

        if 'junk' not in container.namelist():
            container.writestr('junk','some junk text')

        if 'mimetype' not in container.namelist():
            container._add_mimetype_file()
            print("added mimetype")

        for file in container.infolist():
            print(file.filename)

    #    b = container.verify_mimetype()
    #    print(b)



if __name__ == "__main__":
    main()
