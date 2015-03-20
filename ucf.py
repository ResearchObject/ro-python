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
            #if we're in read mode then verify that the mimetype is there and
            #valid - if not then an exception will be raised
            self.mimetype = self.get_mimetype_from_file()
        #else we're in write or append mode
        elif mimetype:
            #See if the mimetype matches an existing valid mimetype file
            #If not because its missing or different then update
            try:
                if self.get_mimetype_from_file() != mimetype:
                    self.set_mimetype(mimetype)
            except MissingMimetypeFileException:
                self.set_mimetype(mimetype)
        else:
            #If mimetype is None then check if there is an existing one
            #If not then set the mimetype file to the default
            try:
                self.mimetype = self.get_mimetype_from_file()
            except MissingMimetypeFileException:
                self.mimetype = DEFAULT_MIMETYPE
                self.set_mimetype()

        self._reserved_files = DEFAULT_RESERVED_FILES
        self._reserved_dirs = DEFAULT_RESERVED_DIRECTORIES



    def set_mimetype(self, mimetype=None):
        self.mimetype = mimetype or self.mimetype
        #Remove any leading whitespace - prohibited by the UCF spec
        self.mimetype.lstrip()
        self._add_mimetype_file()

    def get_mimetype_from_file(self):
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
        compress_type = compress_type or zipfile.ZIP_STORED
        self._check_compression_type(compress_type)
        super().write(filename=filename,arcname=arcname,compress_type=compress_type)

    def writestr(self, zinfo_or_arcname, data, compress_type=None):
        if isinstance(zinfo_or_arcname, zipfile.ZipInfo):
            filename = zinfo_or_arname.filename
        else:
            filename = zinfo_or_arcname
        #Check that this is not a reserved filename or in a reserved directory
        #TODO check for reserved directory
        if filename in self._reserved_files:
            raise ReservedFileNameException()
        super().writestr(zinfo_or_arcname,data,compress_type=compress_type)

    def remove(self, zinfo_or_arcname):
        #Check that this is not a reserved filename or in a reserved directory
        #TODO check for reserved directory
        if isinstance(zinfo_or_arcname, zipfile.ZipInfo):
            filename = zinfo_or_arname.filename
        else:
            filename = zinfo_or_arcname

        if filename in self._reserved_files:
            raise ReservedFileNameException()
        super().remove(zinfo_or_arcname)

    def rename(self, zinfo_or_arcname, filename):
        #Check that this is not a reserved filename or in a reserved directory
        #TODO check for reserved directory
        if filename in self._reserved_files:
            raise ReservedFileNameException()
        super().rename(zinfo_or_arcname, filename)

    @classmethod
    def from_zipfile(cls,file, compression=zipfile.ZIP_STORED, allowZip64=True,mimetype=None):
        """
        Creates a new UCF file from an existing valid zipfile.
        """
        mimetype = mimetype or DEFAULT_MIMETYPE
        return UCF(file,compression=compression,allowZip64=allowZip64,mimetype=mimetype)

    @classmethod
    def _check_compression_type(cls,compress_type):
        if compress_type not in VALID_COMPRESSION:
            raise UnsupportedCompressionException("Unsupported Compression type: Compression must be zipfile.ZIP_STORED or zipfile.ZIP_DEFLATED")

    def _register_reserved_file(self, filename):
        if filename not in self._reserved_files:
            self._reserved_files.append(filename)


    def _register_reserved_directory(self, dirname):
        if dirname not in self._reserved_dirs:
            self._reserved_dirs.append(dirname)

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
            super().writestr('mimetype',ascii_value,compress_type=zipfile.ZIP_STORED)
            return
        else:
            #The archive isn't empty - but we need the mimetype file
            #to be the first entry in the archive. Updating zip archives
            #in place isn't really an option. We therefore need to
            #create a temporary new archive, copy everything over and
            #then switch it in when that has completed successfully.
            #This is how zip -u works?
            self.commit()

    #TODO: Let clone take a filter for the files to include?
    @classmethod
    def clone(cls, ucf_file, file):
        with UCF(file,mode="w",mimetype=ucf_file.mimetype) as new_zip:
            #Don't copy the mimetype file - it's already added by the init above
            infolist = (fileinfo for fileinfo in ucf_file.infolist() if fileinfo.filename != MIMETYPE_FILE)
            for fileinfo in infolist:
                bytes = ucf_file.read_compressed(fileinfo.filename)
                super(ZipFileExt,new_zip).write_compressed(fileinfo,bytes)
            badfile = new_zip.testzip()
        if(badfile):
            raise zipfile.BadZipFile("Error when cloning zipfile, failed zipfile CRC-32 check: file is corrupt")
        return new_zip

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

def main():
    filename = 'test.zip'
    mimetype = "application/vnd.wf4ever.robundle+zip"
    print(zipfile.is_zipfile(filename))
    with UCF(filename,mode='a',compression=zipfile.ZIP_DEFLATED) as container:

        if 'junk' not in container.namelist():
            container.writestr('junk','some junk text')

        for file in container.infolist():
            print(file.filename)

    #    b = container.get_mimetype_from_file()
    #    print(b)
    print("re-open and remove")
    with UCF(filename,mode='a') as container:
        print(container.read('junk'))
        container.remove("junk")

        for file in container.infolist():
            print(file.filename)

        container.writestr('junk','some new junk text')

        print(container.read('junk'))



        for file in container.infolist():
            print(file.filename)

    print("re-open and read")
    with UCF(filename,mode='r') as container:
        print(container.read('junk'))
        for file in container.infolist():
            print(file.filename)

        #container.rename("junk","junk2")

    with open("test.zip",'rb') as b:
        for bytes in b:
            print(bytes)


if __name__ == "__main__":
    main()
