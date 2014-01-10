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


# Globals

SCRIPT_FILE_PATH = os.path.realpath(__file__)
SCRIPT_DIR_PATH = os.path.dirname(SCRIPT_FILE_PATH)
CONFIG_DIR_PATH = os.path.abspath("{0}/pynav-conf".format(SCRIPT_DIR_PATH))
CONFIG_FILE_PATH = os.path.abspath("{0}/pynav.conf".format(CONFIG_DIR_PATH))
DESKTOP_HTML_SHEET = os.path.abspath("{0}/pynav-desktop.html".format(CONFIG_DIR_PATH))
MOBILE_HTML_SHEET =  os.path.abspath("{0}/pynav-mobile.html".format(CONFIG_DIR_PATH))
INDEX_PAGE_NAME = "index.html"


# Functions

def errprint(msg):
    print("\nERROR:", msg, end='\n', file=sys.stderr)


def load_settings(settingDic):
    """ Loads into settingDic the settings found in the config file """
    try:
        configFile = open(CONFIG_FILE_PATH, 'r')
        jsonConfigFile = json.load(configFile)
        configFile.close()
        for key, value in jsonConfigFile["userSettings"].items():
            settingDic[key] = value
    except:
        errprint("El archivo {0} no existe o no puede abrirse".format(CONFIG_FILE_PATH))


def load_html_sheet(sheetFile):
    """ Returns a string with the content o file """
    try:
        f = open(sheetFile, "r")
        content = f.read()
        f.close()               
        if "[pynav-img]" not in content:
            return False            
        return content
    except:
    	errprint("El archivo {0} no existe o no puede abrirse".format(sheetFile))


def get_max_trail_number(baseName, dirList):
    """ Returns the maximun copy number (string) of an folder list based on a name """
    try:
        # There is folder(s) with trails (n)
        baseNameList = [d for d in dirList if d.startswith(baseName+"(")]
        trailsNumbers = []
        for d in baseNameList:  
            trailsNumbers.append(int(d.split(baseName)[1].split("(")[1].split(")")[0]))
        newTrailNumber = max(trailsNumbers) + 1
        return str(newTrailNumber)
    except:
        # There is not folders with copy number, just the same folder name. Then max copy number = (1)
        return "1"


def resolve_conflict(myDir, dirPath):
    """     Returns a next copy directory name if name == name(1). if name(12) == name(13) """
    listDir = get_list_dir(dirPath)
    if myDir in listDir:
        return get_max_trail_number(myDir, listDir)
    else:
        return myDir


def get_files_from_folder(folder, ImageType):
    """ Gets file list with custom extension """
    from os import listdir
    from os.path import isfile, join        
    return [ "{0}/{1}".format(folder, f) for f in listdir(folder) if isfile(join(folder,f)) and f[-3:] == ImageType]


def shift(seq, n):
    """ Shifts list items by n """
    n = n % len(seq)
    return seq[n:] + seq[:n]


def get_image_size(fname):
    """ Determines the image type of fhandle and return its size """
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
    """ Determines size of fname (psd) """
    error = ""
    fhandle = open(fname, 'rb')
    fhandle.read(14)
    (height, width) = struct.unpack("!LL", fhandle.read(8))
    if width == 0 and height == 0:
        error = "no error"

    fhandle.close()
    return width, height


def get_list_dir(path):
    """ Returns List of folders """
    return [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]


def get_file_list(path):
    """ Returns List of files """
    return [d for d in os.listdir(path) if not os.path.isdir(os.path.join(path, d))]


def zip(src, dst):
    """ zip files in a src with dst name """
    if os.path.isfile(dst):
        os.remove(dst)

    abs_src = os.path.abspath(src)
    files = get_file_list(abs_src)

    zf = zipfile.ZipFile(dst, "w")
    for f in files:
        zf.write(os.path.abspath("{0}/{1}".format(abs_src, f)), os.path.basename(f))
    zf.close()


def pynav(settings, userSettings):
    """
            Main Function
    """
    # timing!
    start = time.clock()    

    # Gets source image files \Files\file.* [psd|png|jpg|gif]
    sourceFiles = get_files_from_folder(settings["sourcePath"], settings["inputFormat"])
    if len(sourceFiles) == 0:
        errprint("No existen archivos tipo {0} en el directorio {1}".format(settings["inputFormat"], settings["sourcePath"]))
        sys.exit()

    # If the destination directory doesnt exists, Pynav will create one
    if not os.path.exists(settings["destinationPath"]):
        os.makedirs(settings["destinationPath"])
    else:
        # If the destination directory exists, is the custom Pynav directory and the parameter --overwrite is false, Pynav will create a () trailed one Directory_Name(n)
        if settings["customDestPath"] == False and settings["overwrite"] == False:
            nextTrailNumber = resolve_conflict(os.path.basename(settings["destinationPath"]), settings["destinationPath"].split(os.path.basename(settings["destinationPath"]))[0])
            settings["destinationPath"] = "{0}({1})".format(settings["destinationPath"], nextTrailNumber)
            os.makedirs(settings["destinationPath"])                

    # User custon names
    if settings["fileName"] != None:
        # previz\user_custom_file_name.jpg
        imgsFullPath = ["{}/{}_{:02d}.{}".format(settings["destinationPath"], settings["fileName"], n, settings["outputFormat"]) for n in range(len(sourceFiles))]
        # previz\user_custom_file_name.html
        htmlsFullPath = ["{}/{}_{:02d}.html".format(settings["destinationPath"], settings["fileName"], n) for n in range(len(sourceFiles))]
    else:
        # previz\original_name.jpg
        imgsFullPath = [settings["destinationPath"] + "/" + "{0}{1}".format(f, "."+settings["outputFormat"]) for f in [os.path.basename(f[:-4]) for f in sourceFiles]]
        # previz\original_name.html
        htmlsFullPath = [settings["destinationPath"] + "/" + "{0}.html".format(f) for f in [os.path.basename(f[:-4]) for f in sourceFiles]]

    # previz <a href> target htmls
    tarHtmlsFullPath = shift(htmlsFullPath, 1)
    
    indexHTML = ""

    # Starts processing
    print("", end="\n")
    print("Pynav. Francis Vega 2014", end="\n")
    print("Simple Navigation html+image from image files", end="\n")
    print("", end="\n")

    # Verbose MODDE
    if settings["verbose"]:
        print("", end="\n")
        print("Convert formats: {0} to {1}".format(settings["inputFormat"], settings["outputFormat"]), end="\n")
        print("Source Path {0}".format(settings["sourcePath"]), end="\n")
        print("Destination Path {0}".format(settings["destinationPath"]), end="\n")
        print("", end="\n")

    try:
        fileConverted = 0
        filesToConvert = len(sourceFiles)

        # Custom css style command
        if len(settings["css"]) > 0:
            pattern = re.compile(r'\s+')
            customCss = settings["css"]
            # customCss = re.sub(pattern, '', settings["css"])
            customCss = customCss.split("}")[:-1]
            customCss = [((("\t\t{0}}".format(settings["css"])).replace("{", " {\n\t\t\t")).replace(";",";\n\t\t\t")).replace("\n\t\t\t}","\n\t\t}") for settings["css"] in customCss]
            customCss = "".join(customCss)
            customCss = "/* CSS Style Command Inline*/\n" + customCss
        else:
            customCss = ""

        # Flush
        if settings["flush"]:
            from os import listdir
            from os.path import isfile, join        
            for content in listdir(settings["destinationPath"]):
                content = os.path.abspath("{0}/{1}".format(settings["destinationPath"], content))
                if os.path.isdir(content):
                    shutil.rmtree(content)
                else:
                    os.remove(content)

        # File by file
        startConvertFile = time.clock()
        for i in range(filesToConvert):

            inFile = sourceFiles[i]+'[0]' # add [0] to flatten psds for convert app
            outFile = imgsFullPath[i]
            
            # If file exists and overwrite == False, skip.
            fileExists = os.path.isfile(outFile)
            if fileExists and settings["overwrite"] == False:
                cpath = os.path.basename(inFile)[:-3]
                cperc = int(100.0/filesToConvert) * (i+1)
                
                if settings["fullPath"]:
                    cpath = inFile[:-3]

                print ("{:03d}% ... {} (Skip)".format(cperc, cpath), end="\n")

            else:
                # Select correct HTML Sheet
                if settings["mobile"] == True:
                    Convert_HTML_sheet = settings["mobileSheet"]
                else:
                    Convert_HTML_sheet = settings["desktopSheet"]

                # Get image or psd size
                if settings["inputFormat"] == "psd":
                    size = get_psd_size(inFile[:-3])
                else:
                    size = get_image_size(inFile)

                width = str(size[0])
                height = str(size[1])

                import math
                nSlices = int(math.ceil(float(height)/float(settings["sliceSize"])))
                
                imgTag = []
                for slcs in range(nSlices):
                    newSliceSize = settings["sliceSize"]

                    if int(settings["sliceSize"]) > float(height)-(slcs*float(settings["sliceSize"])):
                        newSliceSize = float(height)-(slcs*float(settings["sliceSize"]))                        

                    # change the output file name adding number for slice
                    ofile = outFile

                    if slcs > 0:
                        ofile = "{0}_slice_{1}.{2}".format(outFile[:-4], str(slcs), settings["outputFormat"])

                    # generate output files
                    crop = '{0}x{1}+{2}+{3}'.format(int(width), int(newSliceSize), 0, int(slcs*settings["sliceSize"]))
                    
                    # convert
                    subprocess.call( [userSettings["convert_app"], '-quality', str(settings["quality"]), inFile, '-crop', crop, ofile], shell=False )

                    # generate html img tag to include into html file
                    imgTag.append(os.path.basename(ofile))

                # If only wants images == False
                if settings["onlyimage"] == False:
                    # Creates html file
                    htmlFile = htmlsFullPath[i]
                    targetFile = tarHtmlsFullPath[i]
                    html = open(htmlFile, "w")

                    # Html params
                    nextHtmlFile = os.path.basename(targetFile)
                    webImageFile = os.path.basename(outFile)

                    # replace custom tags
                    tags = Convert_HTML_sheet
                    tags = tags.replace("[pynav-title]", settings["title"])
                    tags = tags.replace("[pynav-css]", customCss)
                    tags = tags.replace("[pynav-img-width]", width)
                    tags = tags.replace("[pynav-img-height]", height)
                    tags = tags.replace("[pynav-next-html]", nextHtmlFile)                  

                    tags = tags.replace("[pynav-img]", imgTag[0])
                    
                    if nSlices > 1:
                        for j in range(nSlices-1):
                            tags = tags.replace("[pynav-img-slice-{0}]".format(str(j+1)), imgTag[j+1])
            
                    html.write(tags)
                    html.close()

                    # Remove [pynav-img-slice-n] tags
                    temporalHTML = "{0}/tempo.html".format(settings["destinationPath"])
                    shutil.copy(htmlFile, temporalHTML)
                    regex = re.compile('.*pynav-img-slice-.*')
                    f = open(htmlFile, "w")
                    map(lambda x: f.write(x), filter(lambda x: not regex.match(x), open(temporalHTML)))
                    f.close()

                    # Remove temporal file
                    os.remove(temporalHTML)

                if settings["fullPath"]:
                    inFile = inFile[:-3]
                    outFile = outFile
                else:
                    inFile = os.path.basename(inFile)[:-3]
                    outFile = os.path.basename(outFile)

                # Verbose MODDE
                if settings["verbose"]:
                    elapsedConvert = (time.clock() - startConvertFile)
                    print("{:03d} Converting {} to {} @ quality {} (OK) {} secs".format(int((100.0/filesToConvert)*(i+1)), inFile, outFile, str(settings["quality"]), round(elapsedConvert,2)), end="\n")                 
                else:
                    print("{:03d}% ... {} (OK)".format(int((100.0/filesToConvert)*(i+1)), inFile))

                fileConverted = fileConverted+1

            indexHTML += "<li><a href='{0}'>{1}</a></li>\n".format(os.path.basename(htmlsFullPath[i]), os.path.basename(outFile)[:-4])
    
    
        indexHTML = "\
\n<!--\
\n\
\n      Pynav 2014\
\n      Francis Vega\
\n\
\n      hisco@inartx.com\
\n-->\
\n\
\n<!DOCTYPE html>\
\n      <html>\
\n      <head>\
\n              <title>Index of "+ settings["title"] +"</title>\
\n              <style>\
\n                      a {\
\n                              color: black;\
\n                              text-decoration: none\
\n                      }\
\n                      a:visited {\
\n                              color: inherit;\
\n                      }\
\n                      a:hover {\
\n                              color: black;\
\n                              font-weight: bold;\
\n                      }\
\n\
\n                      h1 {\
\n                              margin: 20px 0 0 20px;\
\n                      }\
\n\
\n                      li {\
\n                              line-height: 1.6;\
\n                      }\
\n\
\n                      ul {\
\n                              list-style: none;\
\n                              margin: 20px 0 0 20px;\
\n                      }\
\n\
\n                      *{\
\n                              font-family: Arial;\
\n                              border: 0;\
\n                              margin: 0;\
\n                              padding: 0;\
\n                      }\
\n                      " + customCss + "\
\n              </style>\
\n      </head>\
\n      <h1>Index of "+ settings["title"] + "</h1>\
\n      <ul>\
\n      {0}\
\n      </ul>\
\n      </body>\
\n      </html>".format(indexHTML)

    except KeyboardInterrupt:
        print("", end="\n")
        print("\nInterrupted by a user", end="\n") 

    import math
    elapsed = (time.clock() - start)
    print("", end="\n")    
    print("{0} files converted in {1} seconds".format(str(fileConverted), str(round(elapsed,2))), end="\n")
    print("Mockup finished at {0}".format(os.path.abspath(settings["destinationPath"])), end="\n\n")

    # Removes the temporal folder
    try:
        shutil.rmtree(tmp)
    except:
        pass

    # POST PROCESS
    if settings["index"]:
        idx = open("{0}/{1}".format(settings["destinationPath"], INDEX_PAGE_NAME), "w")
        idx.write(indexHTML)
        idx.close()

    if settings["zip"]:
        zip(settings["destinationPath"], "{0}/{1}.zip".format(settings["destinationPath"], os.path.basename(settings["destinationPath"])))
        print("Mockup zipped at {0}".format(os.path.abspath(("{0}/{1}.zip".format(settings["destinationPath"], os.path.basename(settings["destinationPath"]))))), end="\n\n")

#
# html sheets
#

try:
    desktopSheet = load_html_sheet(DESKTOP_HTML_SHEET)
except:
    desktopSheet ="\
\n<!DOCTYPE html>\
\n<html>\
\n      <head>\
\n      <title>[pynav-title]</title>\
\n      <style>\
\n              /* Pynav default style */\
\n              * {\
\n                      padding:0;\
\n                      margin:0;\
\n              }\
\n              div {\
\n                      margin:0 auto;\
\n                      background:url('[pynav-img]') top center no-repeat;\
\n                      height:[pynav-img-height]px;\
\n                      width:[pynav-img-width]px;\
\n              }\
\n              [pynav-css]\
\n      </style>\
\n      </head>\
\n      <body>\
\n              <a href='[pynav-next-html]'><div></div></a>\
\n      </body>\
\n</html>"

try:
    mobileSheet = load_html_sheet(MOBILE_HTML_SHEET)
except:
    mobileSheet = "\
\n<!DOCTYPE html>\
\n<html>\
\n      <head>\
\n      <title>[pynav-title]</title>\
\n      <style>\
\n              /* Pynav default style */\
\n              * {\
\n                      padding:0;\
\n                      margin:0;\
\n              }\
\n              img {\
\n                      width:100%;\
\n                      height:auto;\
\n                      display:block;\
\n              }\
\n              [pynav-css]\
\n      </style>\
\n      </head>\
\n      <body>\
\n              <a href='[pynav-next-html]'>\
\n                      <img src='[pynav-img]'>\
\n                      <img src='[pynav-img-slice-1]'>\
\n                      <img src='[pynav-img-slice-2]'>\
\n                      <img src='[pynav-img-slice-3]'>\
\n                      <img src='[pynav-img-slice-4]'>\
\n                      <img src='[pynav-img-slice-5]'>\
\n              </a>\
\n      </body>\
\n</html>"

#
#       Start the dance!
#

# Users Settings
userSettings = {
        "convert_app": "C:/Program Files/Adobe/Adobe Photoshop CC (64 Bit)/convert.exe",
        "default_title": "Previz",
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
PARSER = argparse.ArgumentParser( prog="pynav", description="Creates html navigations from image files", epilog="Example of use: pynav.py --title \"Previz\" --log-file /project/psd", formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=60) )
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
PARSER.add_argument( "--html-sheet", "-html", nargs=1, dest="html", default="", type=str, help="Use a custom html file")
# PARSER.add_argument( "--log-file", "-l", dest="logfile", action="store_true", help="Create a log file" )
# PARSER.add_argument( "--list-html-tags", "-tags", nargs=1, dest="html", default="", type=str, help="Show a list of pynav html tags")

# Gets parse arguments
args = PARSER.parse_args()

# Pynav internal settings
settings = {
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

# html sheet
settings["mobileSheet"] = mobileSheet
settings["desktopSheet"] = desktopSheet
#settings["index"] = indexSheet

if settings["html"]:
    if os.path.isfile("{0}/{1}".format(os.getcwd(), settings["html"])):
        htmlSheet = load_html_sheet(settings["html"])
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
pynav(settings, userSettings)

# :)
