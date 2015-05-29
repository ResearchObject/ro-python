from rolib.packages.zipextended.packages import zipfile
import rolib.packages.zipextended
from tempfile import TemporaryFile, NamedTemporaryFile
from rolib.ucf import UCF
from .manifest import Manifest, Aggregate, Annotation
import json
import codecs
import os

MANIFEST_DIR = ".ro/"
MANIFEST_FILE = MANIFEST_DIR + "manifest.json"
MIMETYPE = "application/vnd.wf4ever.robundle+zip"

class Bundle(UCF, object):

    def __init__(self, file, mode="r", compression=zipfile.ZIP_STORED, allowZip64=True):
        self.manifest = Manifest()
        super(Bundle, self).__init__(file,mode=mode,compression=compression,allowZip64=allowZip64,mimetype=MIMETYPE)
        self._register_reserved_file(MANIFEST_FILE)
        self._register_reserved_directory(MANIFEST_DIR)
        if MANIFEST_FILE in self.namelist():
                self.manifest = Manifest(file=self.open(MANIFEST_FILE))

    @classmethod
    def create_from_manifest(cls, file, manifest_or_manifestfilename, compression=zipfile.ZIP_STORED, allowZip64=True):
        with Bundle(file, mode="w", compression=compression, allowZip64=allowZip64) as bundle:
            if manifest_or_manifestfilename:
                if isinstance(manifest_or_manifestfilename, str):
                    bundle.manifest = Manifest(filename=manifest_or_manifestfilename)
                else:
                    bundle.manifest = manifest_or_manifestfilename
            for aggreate in bundle.manifest.aggregates:
                uri = aggreate.uri
                if uri[0] == '/':
                    uri = uri[1:]
                if os.path.isfile(uri):
                    super(Bundle, bundle).write(uri)

            for annotation in bundle.manifest.annotations:
                uri = annotation.contents
                if uri[0] == '/':
                    uri = uri[1:]
                if os.path.isfile(uri):
                    super(Bundle, bundle).write(uri)

            bundle.requires_commit = True
            return bundle

    def write(self, filename, arcname=None, compress_type=None):
        super(Bundle, self).write(filename,arcname=arcname,compress_type=compress_type)
        self.manifest.add_aggregate(Aggregate(filename))
        self.requires_commit = True

    def writestr(self, zinfo_or_arcname, data, compress_type=None):
        super(Bundle, self).writestr(zinfo_or_arcname, data, compress_type=compress_type)
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
        super(Bundle, self).remove(filename)
        self.manifest.remove_aggregate(filename)

    def commit(self):
        self._update_manifest()
        super(Bundle, self).commit()

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
