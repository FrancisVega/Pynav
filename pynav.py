#!/usr/bin/env python
# encoding: utf-8

# Copyright (C) 2014 Francis Vega
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


from __future__ import print_function
import os
import sys
import time
import shutil
import subprocess
import argparse
import math
import zipfile
import re
import imghdr
import struct
import json


SCRIPT_FILE_PATH = os.path.realpath(__file__)
SCRIPT_DIR_PATH = os.path.dirname(SCRIPT_FILE_PATH)
CONFIG_DIR_PATH = os.path.join(SCRIPT_DIR_PATH, "pynav-conf")
CONFIG_FILE_PATH = os.path.join(CONFIG_DIR_PATH, "pynav.conf")
DESKTOP_HTML_SHEET = os.path.join(CONFIG_DIR_PATH, "pynav-desktop.html")
MOBILE_HTML_SHEET = os.path.join(CONFIG_DIR_PATH, "pynav-mobile.html")
INDEX_PAGE_NAME = "index.html"


def timming(f):
    """Process timming decorator"""
    start = time.clock()
    def inner(*args, **kwargs):
        f(*args, **kwargs)
        print("Exe time for {0}(), {1:2f}".format(f.__name__, time.clock() - start))
    return inner

def errprint(msg):
    """Custom error printing."""
    print("\nERROR:", msg, end='\n', file=sys.stderr)

def load_settings(settingDic):
    """Loads into setting Dic the settings found in the config file."""
    try:
        configFile = open(CONFIG_FILE_PATH, 'r')
        jsonConfigFile = json.load(configFile)
        configFile.close()
        for key, value in jsonConfigFile["userSettings"].items():
            settingDic[key] = value
    except:
        errprint("El archivo {0} no existe o no puede abrirse".format(CONFIG_FILE_PATH))

def load_html_template(file_tpl):
    """Returns a string with the content of an valid pynav html template."""
    try:
        file_html = open(file_tpl, "r")
        content = file_html.read()
        file_html.close()
        if "[pynav-img]" not in content:
            return False
        return content
    except:
        errprint("El archivo {0} no existe o no puede abrirse".format(file_tpl))

def get_max_trail_number(baseName, dirList):
    """Returns the maximun copy number (string) of an folder list based on a name."""
    try:
        # There is folder(s) with trails (n)
        baseNameList = [d for d in dirList if d.startswith("{0}(".format(baseName))]
        trailsNumbers = []
        for d in baseNameList:
            trailsNumbers.append(int(d.split(baseName)[1].split("(")[1].split(")")[0]))
        newTrailNumber = max(trailsNumbers) + 1
        return str(newTrailNumber)
    except:
        # There is not folders with copy number, just the same folder name. Then max copy number = (1)
        return "1"

def resolve_conflict(myDir, dirPath):
    """Returns a new directory name with suffix (n) if original exists."""
    listDir = get_list_dir(dirPath)
    if myDir in listDir:
        return get_max_trail_number(myDir, listDir)
    else:
        return myDir

def get_files_from_folder(folder, image_format):
    """Gets file list with custom extension."""
    return [ os.path.join(folder, file) for file in os.listdir(folder)\
        if os.path.isfile(os.path.join(folder, file)) and file[-3:] == image_format]

def shift(seq, n):
    """Shifts list items by n."""
    n = n % len(seq)
    return seq[n:] + seq[:n]

def get_image_size(fname):
    """Determines the image type of fhandle and return its size."""
    fhandle = open(fname, 'rb')
    head = fhandle.read(24)

    if len(head) != 24:
        return
    if imghdr.what(fname) == 'png':
        check = struct.unpack('>i', head[4:8])[0]
        if check != 0x0d0a1a0a:
            return
        width, height = struct.unpack('>ii', head[16:24])
    elif imghdr.what(fname) == 'gif':
        width, height = struct.unpack('<HH', head[6:10])
    elif imghdr.what(fname) == 'jpeg':
        try:
            fhandle.seek(0) # Read 0xff next
            size = 2
            ftype = 0
            while not 0xc0 <= ftype <= 0xcf:
                fhandle.seek(size, 1)
                byte = fhandle.read(1)
                while ord(byte) == 0xff:
                    byte = fhandle.read(1)
                ftype = ord(byte)
                size = struct.unpack('>H', fhandle.read(2))[0] - 2
            # We are at a SOFn block
            fhandle.seek(1, 1)  # Skip `precision' byte.
            height, width = struct.unpack('>HH', fhandle.read(4))
        except Exception: #IGNORE:W0703
            return
    else:
        return

    return width, height

def get_psd_size(fname):
    """Determines size of fname (psd)."""
    error = ""
    fhandle = open(fname, 'rb')
    fhandle.read(14)
    (height, width) = struct.unpack("!LL", fhandle.read(8))
    if width == 0 and height == 0:
        error = "no error"

    fhandle.close()
    return width, height


def get_list_dir(path):
    """Returns List of folders."""
    return [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]

def get_file_list(path):
    """Returns List of files."""
    return [d for d in os.listdir(path) if not os.path.isdir(os.path.join(path, d))]

def zip(src, dst):
    """zip files in a src with dst name."""
    if os.path.isfile(dst):
        os.remove(dst)

    abs_src = os.path.abspath(src)
    files = get_file_list(abs_src)

    zf = zipfile.ZipFile(dst, "w")
    for f in files:
        zf.write(os.path.abspath("{0}/{1}".format(abs_src, f)), os.path.basename(f))
    zf.close()

def pynav(settings):
    """Get user and private settings, convert files and generate htmls."""

    # Dictionary items into vars.
    pynav_convert_app = settings["convert_app"]
    pynav_quality = str(settings["quality"])
    pynav_input_format = str(settings["inputFormat"])
    pynav_output_format = str(settings["outputFormat"])
    pynav_mobile = settings["mobile"]
    pynav_title = str(settings["title"])
    pynav_overwrite = settings["overwrite"]
    pynav_verbose = settings["verbose"]
    pynav_fullPath = settings["fullPath"]
    pynav_index = settings["index"]
    pynav_zip = settings["zip"]
    pynav_only_image = settings["onlyimage"]
    pynav_flush = settings["flush"]
    pynav_slice_size = float(settings["sliceSize"])
    pynav_css = str(settings["css"])
    pynav_mobl_tpl = str(settings["mobileSheet"])
    pynav_desk_tpl = str(settings["desktopSheet"])
    pynav_dest = os.path.abspath(settings["destinationPath"])
    pynav_src = os.path.abspath(settings["sourcePath"])
    pynav_file_name = settings["fileName"]

    # Timing!
    start = time.clock()

    # Get source files.
    sourceFiles = get_files_from_folder(pynav_src, pynav_input_format)
    if not sourceFiles:
        errprint("No existen archivos tipo {0} en el directorio {1}".format(pynav_input_format, pynav_src))
        sys.exit()

    # Directory creation.
    # If the destination directory exists and not --ovwerwrite args,
    # Pynav will createa a directory_name(n) directory.

    # Destination path exists and not --overwrite
    if os.path.exists(pynav_dest) == True and pynav_overwrite == False:
        trailNumber = resolve_conflict(os.path.basename(pynav_dest), pynav_dest.split(os.path.basename(pynav_dest))[0])
        pynav_dest = "{0}({1})".format(pynav_dest, trailNumber)
        os.makedirs(pynav_dest)

    # Destination path doesn't exists
    if not os.path.exists(pynav_dest):
        os.makedirs(pynav_dest)

    # Command user custon names
    if pynav_file_name != None:
        # dest\user_custom_file_name.jpg
        imgsFullPath = [os.path.abspath("{}/{}_{:02d}.{}".format(pynav_dest, pynav_file_name, n, pynav_output_format))\
            for n in range(len(sourceFiles))]

        # dest\user_custom_file_name.html
        htmlsFullPath = [os.path.abspath("{}/{}_{:02d}.html".format(pynav_dest, pynav_file_name, n))\
            for n in range(len(sourceFiles))]
    else:
        # dest\original_name.jpg
        imgsFullPath = [os.path.abspath("{0}/{1}.{2}".format(pynav_dest, f, pynav_output_format))\
            for f in [os.path.basename(f[:-4]) for f in sourceFiles]]

        # dest\original_name.html
        htmlsFullPath = [os.path.abspath("{0}/{1}.html".format(pynav_dest, f)) for f in [os.path.basename(f[:-4])\
            for f in sourceFiles]]

    # Pynav <a href> target htmls
    tarHtmlsFullPath = shift(htmlsFullPath, 1)

    index_anchor_tag = ""

    # Starts convert process
    print("\nPynav. Francis Vega 2014", end="\n")
    print("Simple Navigation html+image from image files", end="\n\n")

    # Verbose
    if pynav_verbose:
        print("Convert formats: {0} to {1}".format(pynav_input_format, pynav_output_format), end="\n")
        print("Source Path {0}".format(pynav_src), end="\n")
        print("Destination Path {0}".format(pynav_dest), end="\n\n")

    try:
        fileConverted = 0
        filesToConvert = len(sourceFiles)

        # --css-style
        customCss = ""
        if len(pynav_css) > 0:
            customCss = "/* CSS Style Command Inline*/\n{0}".format(pynav_css)

        # --flush
        if pynav_flush:
            for content in os.listdir(pynav_dest):
                content = os.path.join(pynav_dest, content)
                if os.path.isdir(content):
                    shutil.rmtree(content)
                else:
                    os.remove(content)

        # File by file
        for i in range(filesToConvert):

            inFile = sourceFiles[i]
            outFile = imgsFullPath[i]

            # If file exists and overwrite == False, skip
            fileExists = os.path.isfile(outFile)
            if fileExists and pynav_overwrite == False:
                path = os.path.basename(inFile)
                pct = int(100.0 / filesToConvert) * (i + 1)

                if pynav_fullPath:
                    path = inFile

                print ("{:03d}% ... {} (Skip)".format(pct, path), end="\n")

            else:
                # Select correct HTML Sheet
                if pynav_mobile == True:
                    Convert_HTML_template = pynav_mobl_tpl
                else:
                    Convert_HTML_template = pynav_desk_tpl

                # Get image or psd size
                if pynav_input_format == "psd":
                    size = get_psd_size(inFile)
                else:
                    size = get_image_size(inFile)

                width = str(size[0])
                height = str(size[1])

                nSlices = int(math.ceil(float(height) / pynav_slice_size))

                imgTag = []
                for slcs in range(nSlices):
                    newSliceSize = pynav_slice_size

                    if int(pynav_slice_size) > float(height) - (slcs * pynav_slice_size):
                        newSliceSize = float(height) - (slcs * pynav_slice_size)

                    # change the output file name adding number for slice
                    ofile = outFile

                    if slcs > 0:
                        ofile = "{0}_slice_{1}.{2}".format(outFile[:-4], str(slcs), pynav_output_format)

                    # generate output files
                    crop = '{0}x{1}+{2}+{3}'.format(int(width), int(newSliceSize), 0, int(slcs * pynav_slice_size))

                    # convert
                    if pynav_input_format == "psd":
                        convertFile = "{0}[0]".format(inFile)
                    else:
                        convertFile = inFile
                    subprocess.call(
                        [pynav_convert_app, '-quality', pynav_quality, convertFile, '-crop', crop, ofile],
                        shell=False
                    )

                    # Generate html img tag to include into html file
                    imgTag.append(os.path.basename(ofile))

                # Not --only-image
                if pynav_only_image == False:
                    # Creates html file
                    htmlFile = htmlsFullPath[i]
                    targetFile = tarHtmlsFullPath[i]
                    html = open(htmlFile, "w")

                    # Html params
                    nextHtmlFile = os.path.basename(targetFile)
                    webImageFile = os.path.basename(outFile)

                    # Replace custom tags
                    tags = Convert_HTML_template
                    tags = tags.replace("[pynav-title]", pynav_title)
                    tags = tags.replace("[pynav-css]", customCss)
                    tags = tags.replace("[pynav-img-width]", width)
                    tags = tags.replace("[pynav-img-height]", height)
                    tags = tags.replace("[pynav-next-html]", nextHtmlFile)
                    tags = tags.replace("[pynav-img]", imgTag[0])

                    if nSlices > 1:
                        for j in range(nSlices-1):
                            tags = tags.replace("[pynav-img-slice-{0}]".format(str(j + 1)), imgTag[j + 1])

                    html.write(tags)
                    html.close()

                    # Remove [pynav-img-slice-n] tags
                    temporalHTML = "{0}/tempo.html".format(pynav_dest)
                    shutil.copy(htmlFile, temporalHTML)
                    regex = re.compile('.*pynav-img-slice-.*')
                    f = open(htmlFile, "w")
                    map(lambda x: f.write(x), filter(lambda x: not regex.match(x), open(temporalHTML)))
                    f.close()

                    # Remove temporal file
                    os.remove(temporalHTML)

                if pynav_fullPath:
                    outFile = outFile
                else:
                    inFile = os.path.basename(inFile)
                    outFile = os.path.basename(outFile)

                # Print info into terminal
                print("{:03d}% ... {}".format(int((100.0 / filesToConvert) * (i + 1)), inFile))

                fileConverted = fileConverted + 1

            index_anchor_tag += "<li><a href='{0}'>{1}</a></li>\n".format(\
                os.path.basename(htmlsFullPath[i]), os.path.basename(outFile)[:-4]\
            )


        indexHTML = u"<!--\
\n\
\n    Pynav 2014\
\n    Francis Vega\
\n\
\n    hisco@inartx.com\
\n-->\
\n\
\n<!DOCTYPE html>\
\n<html>\
\n    <head>\
\n    <title>Index of {0}</title>\
\n    <style>\
\n        * {{ font-family: Arial; border: 0; margin: 0; padding: 0; }}\
\n        a {{ color: black; text-decoration: none; }}\
\n        a:visited {{ color: inherit; }}\
\n        a:hover {{ color: black; font-weight: bold; }}\
\n        h1 {{ margin: 20px 0 0 20px; }}\
\n        li {{ line-height: 1.6; }}\
\n        ul {{ list-style: none; margin: 20px 0 0 20px; }}\
\n        {1}\
\n    </style>\
\n    </head>\
\n    <body>\
\n    <h1>Index of {0}</h1>\
\n    <ul>\
\n        {2}\
\n    </ul>\
\n    </body>\
\n</html>".format(pynav_title, customCss, index_anchor_tag)

    except KeyboardInterrupt:
        print("", end="\n")
        print("\nInterrupted by a user", end="\n")

    elapsed = (time.clock() - start)
    print("", end="\n")
    print("{0} files converted in {1} seconds".format(str(fileConverted), str(round(elapsed,2))), end="\n\n")
    print("Mockup finished at {0}".format(os.path.abspath(pynav_dest)), end="\n\n")

    # Removes the temporal folder
    try:
        shutil.rmtree(tmp)
    except:
        pass

    # --index-of-pages
    if pynav_index:
        index = open(os.path.join(pynav_dest, INDEX_PAGE_NAME), "w")
        index.write(indexHTML)
        index.close()

    # --zip
    if pynav_zip:
        zip_file_name = "{0}.zip".format(os.path.basename(pynav_dest))
        zip_path_name = os.path.join(pynav_dest, zip_file_name)
        zip(pynav_dest, zip_path_name)
        print("Mockup zipped at {0}".format(zip_path_name), end="\n\n")


# Html templates

try:
    desktopSheet = load_html_template(DESKTOP_HTML_SHEET)
except:
    desktopSheet ="\
\n<!DOCTYPE html>\
\n<html>\
\n    <head>\
\n    <title>[pynav-title]</title>\
\n    <style>\
\n        /* Pynav default style */\
\n        * { padding: 0; margin: 0; }\
\n        div { margin: 0 auto; background: url('[pynav-img]') top center no-repeat; height: [pynav-img-height]px; width: [pynav-img-width]px; }\
\n        [pynav-css]\
\n    </style>\
\n    </head>\
\n    <body>\
\n        <a href='[pynav-next-html]'><div></div></a>\
\n    </body>\
\n</html>"

try:
    mobileSheet = load_html_template(MOBILE_HTML_SHEET)
except:
    mobileSheet = "\
\n<!DOCTYPE html>\
\n<html>\
\n    <head>\
\n    <title>[pynav-title]</title>\
\n    <style>\
\n        /* Pynav default style */\
\n        * { padding: 0; margin: 0; }\
\n        img { width: 100%; height: auto; display: block;}\
\n        [pynav-css]\
\n    </style>\
\n    </head>\
\n    <body>\
\n        <a href='[pynav-next-html]'>\
\n            <img src='[pynav-img]'>\
\n            <img src='[pynav-img-slice-1]'>\
\n            <img src='[pynav-img-slice-2]'>\
\n            <img src='[pynav-img-slice-3]'>\
\n            <img src='[pynav-img-slice-4]'>\
\n            <img src='[pynav-img-slice-5]'>\
\n        </a>\
\n    </body>\
\n</html>"

# Pynav internal defatul settings
userSettings = {
        "convert_app": "C:/Program Files/Adobe/Adobe Photoshop CC (64 Bit)/convert.exe",
        "default_title": "Pynav",
        "default_inputFormat": "psd",
        "default_outputFormat": "jpg",
        "default_outputDirName": "Pynav_",
        "default_quality": [100],
        "default_sliceSize": [1034]
}

# Load settings from pynav.conf
load_settings(userSettings)

# Checks if the convert app path is correct
# to do: En vez de mirar directamente el path, mirar que este en el sistema
# por ejemplo en la variable de entorno PATH
if not os.path.isfile(userSettings["convert_app"]):
    errprint("No se encuentra el archivo {0}".format(userSettings["convert_app"]))
    # Use imagemagick installed on osx / linux
    if os.name == "posix":
        userSettings["convert_app"] = "convert"
    # sys.exit()

# ARGSPARSER
PARSER = argparse.ArgumentParser( prog="pynav", description="Creates html navigations from image files", epilog="Example of use: pynav.py --title \"Previz\" --mobile /project/psd", formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=60) )
PARSER.add_argument( "sourcePath", metavar="Source", type=str, nargs=1, help="Source Path of Images" )
PARSER.add_argument( "destinationPath", metavar="Destination", type=str, nargs="?", help="Destination Path of Mokcup" )
PARSER.add_argument( "--in-format", "-if", nargs=1, dest="inFormat", default=userSettings["default_inputFormat"], type=str, help="Source file format" )
PARSER.add_argument( "--out-format", "-of", nargs=1, dest="outFormat", default=userSettings["default_outputFormat"], type=str, help="Output file format" )
PARSER.add_argument( "--title", "-t", nargs=1, dest="title", default=userSettings["default_title"], type=str, help="Set presentation title" )
PARSER.add_argument( "--file-name", "-fn", nargs=1, dest="filename", type=str, help="Set custon names to out images" )
PARSER.add_argument( "--quality", "-q", nargs=1, dest="quality", default=userSettings["default_quality"], type=int, help="Set jpg quality [1-100]" )
PARSER.add_argument( "--overwrite", "-ow", dest="overwrite", action="store_true", help="Overwrite output files" )
PARSER.add_argument( "--verbose", "-v", dest="verbose", action="store_true", help="Verbose mode" )
PARSER.add_argument( "--full-path", "-fp", dest="fullpath", action="store_true", help="Show full path of files" )
PARSER.add_argument( "--index-of-pages", "-index", dest="index", action="store_true", help="Create a index of pages" )
PARSER.add_argument( "--only-image", "-image", dest="onlyimage", action="store_true", help="Create just image files" )
PARSER.add_argument( "--mobile", "-m", dest="mobile", action="store_true", help="Mobile markup")
PARSER.add_argument( "--slice", "-slc", nargs=1, dest="slice", default=userSettings["default_sliceSize"], type=int, help="Set height slice for mobile" )
PARSER.add_argument( "--css-style", "-style", nargs=1, dest="css", default="", type=str, help="Add css style to all html files")
PARSER.add_argument( "--zip", "-z", dest="zip", action="store_true", help="Create a zip file with results files" )
PARSER.add_argument( "--flush", "-f", dest="flush", action="store_true", help="Delete all the content in the destination folder" )
PARSER.add_argument( "--html-template", "-html", nargs=1, dest="html", default="", type=str, help="Use a custom html file")
# PARSER.add_argument( "--log-file", "-l", dest="logfile", action="store_true", help="Create a log file" )
# PARSER.add_argument( "--list-html-tags", "-tags", nargs=1, dest="html", default="", type=str, help="Show a list of pynav html tags")

# Parse arguments
DEBUG = False
if DEBUG:
    # DEBUG
    pynav_args = ["--verbose", "--zip", "-m", "-slc", "1000", "--flush", "-q", "1", "-ow", "-index", ""]
    args = PARSER.parse_args(pynav_args)
else:
    args = PARSER.parse_args()

# Pynav internal settings
settings = {
    "convert_app": userSettings["convert_app"],
    "customDestPath":False,
    "onlyimage": False,
    "date": time.strftime("%Y_%m_%d"),
    "sourcePath": os.path.abspath("".join(args.sourcePath)),
    "destinationPath": args.destinationPath,
    "pynavDirName": "{0}{1}".format(userSettings["default_outputDirName"], time.strftime("%Y-%m-%d"))
}

# Source Path (the only mandatory param)
# Checks if the sourcePath exists (and is a directory) if not, Pynav stops
if os.path.isdir(settings["sourcePath"]) == False:
    print("El path origen {0} no existe o no es un directorio".format(settings["sourcePath"], end="\n"))
    sys.exit()

# Destination Path (optional)
# If destination path parameter doesnt exists pynav will create a custom directory
if settings["destinationPath"] == None:
    settings["destinationPath"] = "{0}/{1}".format(settings["sourcePath"], settings["pynavDirName"])
# If destination param exists, then pynav will use it to create the directory
else:
    settings["destinationPath"] = "".join(settings["destinationPath"])
    settings["customDestPath"] = True

# If sourcePath and destPath are the same, pynav yield a warning, just for information.
if settings["sourcePath"] == settings["destinationPath"]:
    print("El directorio Origen y Destino son el mismo\nConitunamos de todas formas? [y][n]", end="\n")
    while True:
        answer = raw_input()
        if answer[0].upper() == "Y":
            break
        if answer[0].upper() == "N":
            sys.exit()

# Grab the Argparse arguments into settnigs dic
settings["quality"] = args.quality[0]
settings["inputFormat"] = "".join(args.inFormat)
settings["outputFormat"] = "".join(args.outFormat)
settings["mobile"] = args.mobile
settings["title"] = "".join(args.title)
settings["overwrite"] = args.overwrite
settings["verbose"] = args.verbose
settings["fullPath"] = args.fullpath
settings["index"] = args.index
settings["zip"] = args.zip
settings["onlyimage"] = args.onlyimage
settings["flush"] = args.flush
settings["sliceSize"] = args.slice[0]
settings["css"] = "".join(args.css)
settings["html"] = "".join(args.html)
# settings["logfile"] = args.logfile

if args.filename == None:
    settings["fileName"] = None
else:
    settings["fileName"] = args.filename[0]

# Html template
settings["mobileSheet"] = mobileSheet
settings["desktopSheet"] = desktopSheet
#settings["index"] = indexSheet

if settings["html"]:
    settings["html"] = os.path.abspath(settings["html"])
    if os.path.isfile(settings["html"]):
        htmlSheet = load_html_template(settings["html"])
        if htmlSheet:
            settings["mobileSheet"] = htmlSheet
            settings["desktopSheet"] = htmlSheet
        else:
            errprint("El archivo {0} no tiene un formato de etiquetas adecuado".format(settings["html"]))
            sys.exit()
    else:
        errprint("No existe el archivo html {0}".format(settings["html"]))
        sys.exit()

# Go with the flow!!
pynav(settings)
