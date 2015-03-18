import zipfile
import zipext
from tempfile import TemporaryFile, NamedTemporaryFile
from ucf import UCF
from manifest import Manifest, Aggregate, Annotation

MANIFEST_DIR = ".ro/"
MANIFEST_FILE = MANIFEST_DIR + "manifest.json"
MIMETYPE = "application/vnd.wf4ever.robundle+zip"

class Bundle(UCF):

    def __init__(self, file, mode="r", compression=zipfile.ZIP_STORED):
        super().__init__(file,mode=mode,compression=compression,allowZip64=True,mimetype=MIMETYPE)
        self._register_reserved_file(MANIFEST_FILE)
        self._register_reserved_directory(MANIFEST_DIR)
        if MANIFEST_FILE in self.namelist():
            self.manifest = Manifest(self.read(MANIFEST_FILE))
        else:
            self.manifest = Manifest()

    def write(self, filename, arcname=None, compress_type=None):
        super().write(filename,arcname=arcname,compress_type=compress_type)
        self.manifest.add_aggregate(Aggregate(filename))

    def writestr(self, zinfo_or_arcname, data, compress_type=None):
        super().writestr(zinfo_or_arcname, data, compress_type=compress_type)
        if isinstance(zinfo_or_arcname, zipfile.ZipInfo):
            filename = zinfo_or_arcname.filename
        else:
            filename = zinfo_or_arcname
        self.manifest.add_aggregate(Aggregate(filename))

    def _update_manifest(self):
        super(zipext.ZipFileExt).remove(MANIFEST_FILE)
        manifest_json = self.manifest.to_json()
        super(zipfile.ZipFile).writestr(MANIFEST_FILE,manifest_json)

    def add(self, filename, arcname=None):
        self.write(filename, arcname=arcname)

    def remove(self,filename):
        super().remove(filename)
        self.manifest.remove_aggregate(filename)

    def _pre_commit(self, bundle):
        #make sure we call UCFs _pre_commit first to add the mimetype file first
        print("_pre_commit_bundle")
        super()._pre_commit(bundle)
        self._update_manifest()


def main():
    with Bundle("test.zip",mode='w') as b:
        b.writestr("testfile","test_contents")
        b.writestr("testfile2","test_contents")
        print(b.manifest)

if __name__ == "__main__":
    main()
