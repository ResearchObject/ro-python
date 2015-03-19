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
        del self.NameToInfo[zinfo.filename]
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
        self.NameToInfo[zinfo.filename] = zinfo
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
                    #Commit will create a new zipfile and swap it in - this will
                    #have its end record written upon close
                    self.commit()
                else:
                    #Don't need to commit any changes - just write the end record
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

    #TODO: Let clone take a filter for the files to include?
    @classmethod
    def clone(cls, zipf, file):
        with ZipFileExt(file,mode="w") as new_zip:
            for fileinfo in zipf.infolist():
                bytes = zipf.read(fileinfo.filename)
                new_zip.writestr(fileinfo.filename,bytes)
            badfile = new_zip.testzip()
        if(badfile):
            raise zipfile.BadZipFile("Error when cloning zipfile, failed zipfile CRC-32 check: file is corrupt")
        return new_zip


    def reset(self):
        #TODO instead of reusing __init__ it would be nicer to establish
        #what really needs doing to reset. This would however likely result
        #in code duplication from zipfile.ZipFile's init method.
        #Really we need a reset function in zipfile.
        self.fp.seek(0)
        self.__init__(file=self.fp,mode='a',compression=self.compression,allowZip64=self._allowZip64)

    def commit(self):
        #Do we need to try to create the temp files in the same directory initially?
        new_zip = self.clone(self,tempfile.NamedTemporaryFile(delete=False))
        old = tempfile.NamedTemporaryFile(delete=False)
        #Is this a File?
        if isinstance(self.filename,str) and self.filename is not None and os.path.exists(self.filename):
            #if things are filebased then we can used the OS to move files around.
            #mv self.filename to old, new to self.filename, and then remove old
            old.close()
            os.rename(self.filename,old.name)
            os.rename(new_zip.filename,self.filename)
            self.reset()
        #Is it a file-like stream?
        elif hasattr(self.fp,'write'):
            #Not a file but has write, looks like self.fp is a stream
            self.fp.seek(0)
            for b in self.fp:
                old.write(b)
            old.close()
            #Set up to write new bytes
            self.fp.seek(0)
            self.fp.truncate()
            with open(new_zip.filename,'rb') as fp:
                for b in fp:
                    self.fp.write(b)
            self.reset()

            #cleanup
            if os.path.exists(old.name):
                #TODO check valid zip again before we unlink the old?
                os.unlink(old.name)
