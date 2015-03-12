import io
import os
import zipfile
import datetime
import tempfile

from zipfile import ZipFile

META_INF = "META-INF"
MIMETYPE_FILE = "mimetype"
_RESERVED = [META_INF,MIMETYPE_FILE]
DEFAULT_MIMETYPE = "application/epub+zip"


class UCF(ZipFile):
    def __init__(self, file, mode="r", compression=zipfile.ZIP_STORED, allowZip64=True,mimetype=None):
        if compression not in [zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED]:
            raise UCFExcection("Unsupported Compression type")
        super().__init__(file,mode=mode,compression=compression,allowZip64=allowZip64)
        self.mimetype = mimetype or DEFAULT_MIMETYPE
        pass

    def set_mimetype(self, mimetype=None):
        if mimetype is None:
            mimetype = DEFAULT_MIMETYPE
        self._add_mimetype_file(mimetype)

    def _add_mimetype_file(self, mimetype):
        """
        The UCF specification requires a mimetype file to included as an
        uncompressed, unencrypted file as the *first entry* in the Zip archive.
        The contents of this file are the media type of the file as an ASCII
        string, with no preceeding space.
        """
        ascii_value = mimetype.encode('ascii')
        if not self.namelist():
            #If the archive is empty then we're in luck - we can just
            #write the file at the top :)
            self.writestr('mimetype',ascii_value,compress_type=None)
            return
        else:
            #The archive isn't empty - but we need the mimetype file
            #to be the first entry in the archive. Updating zip archives
            #in place isn't really an option. We therefore need to
            #create a temporary new archive, copy everything over and
            #then switch it in when that has completed successfully.
            #This is how zip -u works
            new_temp = tempfile.NamedTemporaryFile(delete=False)
            print(new_temp.name)
            with UCF(new_temp,mode="w") as temp_ucf:
                temp_ucf._add_mimetype_file(mimetype)
                for name in self.namelist():
                    bytes = self.read(name)
                    temp_ucf.writestr(name,bytes)
            badfile = temp_ucf.testzip()
            if(badfile):    #retry?
                raise BadUCFFile("Error when creating mimetype file Bad UCF file generated (failed zipfile.test_zip()): file %s is corrupt")
            else:
                #mv old to old_temp, new to old, and then remove old_temp
                #TODO check: The filenames here should always be absolute?
                old_temp = tempfile.NamedTemporaryFile()
                os.rename(self.filename,old_temp.name)
                os.rename(new_temp.name,self.filename)
                #TODO instead of reusing __init__ it would be nicer to establish
                #what really needs using to reset. This would result in code duplication
                #really I need a reset function in zipfile
                self.__init__(file=self.filename,mode='r',compression=self.compression,allowZip64=self._allowZip64,mimetype=self.mimetype)

class UCFException(Exception):
    pass

class BadUCFFile(UCFException):
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
        print()

def main():
    filename = '/tmp/test.zip'
    mimetype = "application/vnd.wf4ever.robundle+zip"
    print(zipfile.is_zipfile(filename))
    with UCF(filename,mode='a') as container:

        if 'junk' not in container.namelist():
            container.writestr('junk','some junk text')

        if 'mimetype' not in container.namelist():
            container._add_mimetype_file(mimetype)
            print("added mimetype")

        for name in container.namelist():
            print(name)

if __name__ == "__main__":
    main()
