import os
import sys
from pathlib import Path
import shutil


class OneZipToRuleThemAll:

    def __init__(self):
        self.path = sys.argv[1]
        self.destination = sys.argv[2]
        os.mkdir(self.destination)

    def get_folders(self):
        file_i = 0

        for subdir, dirs, files in os.walk(self.path):
            if len(dirs) > 0:
                for folder in dirs:
                    for path in Path(str(os.path.join(os.getcwd(), self.path, folder))).rglob('*.jpg'):
                        file_i += 1
#                        shutil.copy(path, os.path.join(os.getcwd(), self.destination, folder+'_'+path.stem+path.suffix))
                        shutil.copy(path, os.path.join(os.getcwd(), self.destination, folder+'_'+path.stem.replace(".","_")+path.suffix))

        shutil.make_archive(self.destination, 'zip', self.destination)
        print("The new folder contains {} images".format(file_i))


if __name__ == '__main__':
    objectZipper = OneZipToRuleThemAll()
    objectZipper.get_folders()