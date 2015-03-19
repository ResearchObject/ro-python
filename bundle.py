import zipfile
import zipext
from tempfile import TemporaryFile, NamedTemporaryFile
from ucf import UCF
from manifest import Manifest, Aggregate, Annotation
import json
import codecs

MANIFEST_DIR = ".ro/"
MANIFEST_FILE = MANIFEST_DIR + "manifest.json"
MIMETYPE = "application/vnd.wf4ever.robundle+zip"

class Bundle(UCF):

    def __init__(self, file, mode="r", compression=zipfile.ZIP_STORED, allowZip64=True):
        self.manifest = Manifest()
        super().__init__(file,mode=mode,compression=compression,allowZip64=allowZip64,mimetype=MIMETYPE)
        self._register_reserved_file(MANIFEST_FILE)
        self._register_reserved_directory(MANIFEST_DIR)
        if MANIFEST_FILE in self.namelist():
                self.manifest = Manifest(file=self.open(MANIFEST_FILE))


    def write(self, filename, arcname=None, compress_type=None):
        super().write(filename,arcname=arcname,compress_type=compress_type)
        self.manifest.add_aggregate(Aggregate(filename))
        self.requires_commit = True

    def writestr(self, zinfo_or_arcname, data, compress_type=None):
        super().writestr(zinfo_or_arcname, data, compress_type=compress_type)
        if isinstance(zinfo_or_arcname, zipfile.ZipInfo):
            filename = zinfo_or_arcname.filename
        else:
            filename = zinfo_or_arcname
        self.manifest.add_aggregate(Aggregate(filename))
        #Every time we alter the manifest we will have to commit to update the
        #changes
        self.requires_commit = True

    def _update_manifest(self):
        if MANIFEST_FILE in self.namelist():
            zipext.ZipFileExt.remove(self,MANIFEST_FILE)
        manifest_json = self.manifest.to_json()
        zipfile.ZipFile.writestr(self,MANIFEST_FILE,manifest_json)

    def add(self, filename, arcname=None):
        self.write(filename, arcname=arcname)

    def remove(self,filename):
        super().remove(filename)
        self.manifest.remove_aggregate(filename)

    def commit(self):
        self._update_manifest()
        super().commit()



def main():
    with Bundle("test.zip",mode='a') as b:
        b.writestr("testfile","test_contents")
        b.writestr("testfile2","test_contents")
        print(b.manifest)

        b.fp.seek(0)
        for bytes in b.fp:
            print(bytes)

    with open("test.zip",'rb') as b:
        for bytes in b:
            print(bytes)

    with Bundle("test.zip",mode='r') as b:
        for n in b.namelist():
            print(n)


if __name__ == "__main__":
    main()
