import io
import os
import zipfile
import tempfile
import zipext

from packages.zipfile import ZipFile


class ZipFileExt(ZipFile):

    def __init__(self, file, mode="r", compression=zipfile.ZIP_STORED, allowZip64=True):
        super().__init__(file,mode=mode,compression=compression,allowZip64=allowZip64)
        self.requires_commit = False

    def remove(self, zinfo_or_arcname):
        if not self.fp:
            raise RuntimeError(
                "Attempt to modify to ZIP archive that was already closed")

        if isinstance(zinfo_or_arcname, zipfile.ZipInfo):
            zinfo = zinfo_or_arcname
        else:
            zinfo = self.getinfo(zinfo_or_arcname)

        self.filelist.remove(zinfo)
        self._didModify = True
        self.requires_commit = True

    def rename(self, zinfo_or_arcname, filename):
        if not self.fp:
            raise RuntimeError(
                "Attempt to modify to ZIP archive that was already closed")

        # Terminate the file name at the first null byte.  Null bytes in file
        # names are used as tricks by viruses in archives.
        null_byte = filename.find(chr(0))
        if null_byte >= 0:
            filename = filename[0:null_byte]
        # This is used to ensure paths in generated ZIP files always use
        # forward slashes as the directory separator, as required by the
        # ZIP format specification.
        if os.sep != "/" and os.sep in filename:
            filename = filename.replace(os.sep, "/")

        if isinstance(zinfo_or_arcname, zipfile.ZipInfo):
            zinfo = zinfo_or_arcname
        else:
            zinfo = self.getinfo(zinfo_or_arcname)

        zinfo.filename = filename
        self._didModify = True
        self.requires_commit = True


    def close(self):
        """Close the file, and for mode "w" and "a" write the ending
        records."""
        if self.fp is None:
            return

        try:
            if self.mode in ("w", "a") and self._didModify: # write ending records
                if self.requires_commit:
                    self.commit()

                with self._lock:
                    try:
                        self.fp.seek(self.start_dir)
                    except (AttributeError, io.UnsupportedOperation):
                        # Some file-like objects can provide tell() but not seek()
                        pass
                    self._write_end_record()
        finally:
            fp = self.fp
            self.fp = None
            self._fpclose(fp)

    def commit(self):

        with ZipFile(tempfile.NamedTemporaryFile(delete=False),mode="w") as new_zip:
            for name in self.namelist():
                bytes = self.read(name)
                new_zip.writestr(name,bytes)
            badfile = new_zip.testzip()
        if(badfile):
            raise zipfile.BadZipFile("Error when writing updated zipfile, failed zipfile CRC-32 check: file is corrupt")
        else:
            if self.filename is not None:
                #if things are filebased then we can used the OS to move files around.
                #mv self.filename to old, new to self.filename, and then remove old
                old = tempfile.NamedTemporaryFile(delete=False)
                old.close()
                print("filename is ", self.filename)
                os.rename(self.filename,old.name)
                os.rename(new_zip.filename,self.filename)
            else:
                #looks like our zipfile is an in memory stream
                pass
            #TODO instead of reusing __init__ it would be nicer to establish
            #what really needs doing to reset. This would however likely result
            #in code duplication from zipfile.ZipFile's init method.
            #Really we need a reset function in zipfile.
            self.__init__(file=self.filename,mode='a',compression=self.compression,allowZip64=self._allowZip64)
