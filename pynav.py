#!/usr/bin/env python
# encoding: utf-8

# Copyright (C) 2013-2014 Francis Vega
# All rights reserved.
#
# The coded instructions, statements, computer programs, and/or related
# material (collectively the "Data") in these files contain unpublished
# information proprietary to Francis Vega
#
# The Data is provided for use exclusively by You. You have the right to use,
# modify, and incorporate this Data into other products for purposes authorized 
# by Francis Vega without fee.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND. FRANCIS VEGA
# DOES NOT MAKE AND HEREBY DISCLAIMS ANY EXPRESS OR IMPLIED WARRANTIES
# INCLUDING, BUT NOT LIMITED TO, THE WARRANTIES OF NON-INFRINGEMENT,
# MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE, OR ARISING FROM A COURSE 
# OF DEALING, USAGE, OR TRADE PRACTICE. IN NO EVENT WILL FRANCIS VEGA BE LIABLE
# FOR ANY LOST REVENUES, DATA, OR PROFITS, OR SPECIAL,
# DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES, EVEN IF FRANCIS VEGA HAS BEEN
# ADVISED OF THE POSSIBILITY OR PROBABILITY OF SUCH DAMAGES.

#
#	Some modules
#

import os
import sys
import subprocess
import argparse
import math
import zipfile
import re
import shutil
import time
import imghdr
import struct
import json

#
#	Functions
#

# Loads into settingDic the settings found in the config file
def loadSettings(settingDic):
	pynavConfigFile = "pynav.json"
	if os.path.isfile(pynavConfigFile):
		confFile = open(pynavConfigFile, 'r')
		jsonConfFile = json.load(confFile)
		confFile.close()
		for key in jsonConfFile["userSettings"].keys():
			settingDic[key] = jsonConfFile["userSettings"][key]

# Returns the maximun copy number (string) of an folder list based on a name
def getMaxTrailNumber(baseName, dirList):
	# There is folder(s) with trails (n)
	try:
		baseNameList = [d for d in dirList if d.startswith(baseName+"(")]
		trailsNumbers = []
		for d in baseNameList:	
			trailsNumbers.append(int(d.split(baseName)[1].split("(")[1].split(")")[0]))
		newTrailNumber = max(trailsNumbers) + 1
		return str(newTrailNumber)
	except:
		# There is not folders with copy number, just the same folder name. Then max copy number = (1)
		return "1"

# Returns a next copy directory name if name == name(1). if name(12) == name(13)
def resolveConflict(myDir, dirPath):
	listDir = getListDir(dirPath)
	if myDir in listDir:
		return getMaxTrailNumber(myDir, listDir)
	else:
		return myDir

# Gets file list with custom extension
def getTypeFromFolder(folder, ImageType):
	from os import listdir
	from os.path import isfile, join	
	return [ "%s/%s" % (folder, f) for f in listdir(folder) if isfile(join(folder,f)) and f[-3:] == ImageType]

# Shifts list items by n
def shift(seq, n):
    n = n % len(seq)
    return seq[n:] + seq[:n]

# Determines the image type of fhandle and return its size
def get_image_size(fname):
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

# Returns List of folders
def getListDir(path):

	return [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]

# Returns List of files
def getFileList(path):

	return [d for d in os.listdir(path) if not os.path.isdir(os.path.join(path, d))]

# zip files in a src with dst name
def zip(src, dst):
	if os.path.isfile(dst):
		os.remove(dst)

	abs_src = os.path.abspath(src)
	files = getFileList(abs_src)

	zf = zipfile.ZipFile(dst, "w")
	for f in files:
		zf.write(os.path.abspath("%s/%s" % (abs_src, f)), os.path.basename(f))
	zf.close()

# PREVIZ!
def makePrevizNav(settings, userSettings):
	# timing!
	start = time.clock()	

	# Gets source image files \Files\file.* [psd|png|jpg|gif]
	sourceImagesFullPath = getTypeFromFolder(settings["sourcePath"], settings["inputFormat"])
	if len(sourceImagesFullPath) == 0:
		print "\nERROR! No existen archivos tipo [%s] en el directorio [%s]" % (settings["inputFormat"], settings["sourcePath"])
		sys.exit()

	#
	# MAKING THE DESTINATION DIRECTORY
	#
	# There is two differents behaviours:
	#
	# 1 - Pynav custom directory
	#
	# 	If the user don't specify a custom directory, pynav create one with a special name
	#	If already exists a directory with the same name and the user has not specified the parameter --overwrite
	#	Pynav will add a (n) number after directory name: directory(1)
	#
	# 2 - User custom directory
	#
	#	If the user specify a custom directory, Pynav will create one with the user name
	#	If already exists, pynav will skip files that find with the same name
	#	If the user specify the parameter --overwrite Pynav will overwrite all files with de same name

	# If the destination directory doesnt exists, Pynav will create one
	if not os.path.exists(settings["destinationPath"]):
	    os.makedirs(settings["destinationPath"])
	else:
		# If the destination directory exists, is the custom Pynav directory and the parameter --overwrite is false, Pynav will create a () trailed one Directory_Name(n)
		if settings["customDestPath"] == False and settings["overwrite"] == False:
			nextTrailNumber = resolveConflict(os.path.basename(settings["destinationPath"]), settings["destinationPath"].split(os.path.basename(settings["destinationPath"]))[0])
			settings["destinationPath"] = "%s(%s)" % (settings["destinationPath"], nextTrailNumber)
			os.makedirs(settings["destinationPath"])		

	
	# User custon names
	if settings["fileName"] != None:
		# previz\user_custom_file_name.jpg
		imgsFullPath = [ "%s\\%s_%02d.%s" % (settings["destinationPath"], settings["fileName"], n, settings["outputFormat"]) for n in range(len(sourceImagesFullPath)) ]
		# previz\user_custom_file_name.html
		htmlsFullPath = [ "%s\\%s_%02d.html" % (settings["destinationPath"], settings["fileName"], n) for n in range(len(sourceImagesFullPath)) ]		
	else:
		# previz\original_name.jpg
		imgsFullPath = [settings["destinationPath"] + "/" + "%s%s" % (f, "."+settings["outputFormat"]) for f in [os.path.basename(f[:-4]) for f in sourceImagesFullPath]]
		# previz\original_name.html
		htmlsFullPath = [settings["destinationPath"] + "/" + "%s.html" % f for f in [os.path.basename(f[:-4]) for f in sourceImagesFullPath]]

	# previz <a href> target htmls
	tarHtmlsFullPath = shift(htmlsFullPath, 1)
	
	# Logs text vars for log file
	logText_a, logText_b, logText_c, logText_d, logText_e, logText_f = "", "", "", "", "", ""
	indexHTML = ""

	# Starts processing
	logText_a += "\n"
	logText_a += "Pynav. Francis Vega 2014\n"
	logText_a += "Simple Navigation html+image from image files\n"
	logText_a += "\n"
	print logText_a
	
	# Verbose MODDE
	if settings["verbose"]:
		logText_b += "Convert formats: %s to %s\n" % (settings["inputFormat"], settings["outputFormat"])
		logText_b += "Source Path [%s]\n" % (settings["sourcePath"])
		logText_b += "Destination Path [%s]\n" % (settings["destinationPath"])
		logText_b += "\n"
		print logText_b

	try:
		fileConverted = 0
		filesToConvert = len(sourceImagesFullPath)

		# Custom css style command
		if len(settings["css"]) > 0:
			pattern = re.compile(r'\s+')
			customCss = re.sub(pattern, '', settings["css"])
			customCss = customCss.split("}")[:-1]
			customCss = [((("\t\t%s}\n"%settings["css"]).replace("{", " {\n\t\t\t")).replace(";",";\n\t\t\t")).replace("\n\t\t\t}","\n\t\t}\n") for settings["css"] in customCss]
			customCss = "".join(customCss)
			customCss = "\t\t/* CSS Style Command Inline*/\n" + customCss
		else:
			customCss = ""

		# Flush
		if settings["flush"]:
			from os import listdir
			from os.path import isfile, join	
			for content in listdir(settings["destinationPath"]):
				content = os.path.abspath("%s/%s" % (settings["destinationPath"], content))
				if os.path.isdir(content):
					shutil.rmtree(content)
				else:
					os.remove(content)


		for i in range(filesToConvert):
			# psd > img
			inFile = sourceImagesFullPath[i]+'[0]'
			outFile = imgsFullPath[i]
			
			fileExists = os.path.isfile(outFile)
			if fileExists and settings["overwrite"] == False:
				# msg = "Skip %s already exists" % os.path.basename(outFile)
				if settings["fullPath"]:
					msg = "%03d%% ... %s (Skip)" % ((float((100.0/filesToConvert))*(i+1)), inFile[:-3])
				else:
					msg = "%03d%% ... %s (Skip)" % ((float((100.0/filesToConvert))*(i+1)), os.path.basename(inFile)[:-3])					
				print msg
				logText_c += msg+"\n"
			else:												
				# desktop
				if settings["mobile"] == False:
					startConvertFile = time.clock()
					subprocess.call( [userSettings["convert_app"], '-quality', str(settings["quality"]), inFile, outFile], shell=False )
					height = str(get_image_size(outFile)[1])
				# mobile
				else:
					startConvertFile = time.clock()
					# Create a temp directory
					tmp = "%s/previz_temp" % settings["destinationPath"]
					if not os.path.exists(tmp):
						os.makedirs(tmp)

					# creamos un jpg low qualy para ver el alto
					subprocess.call( [userSettings["convert_app"], '-quality', '1', inFile, "%s/.__temp_previz.jpg" % tmp ], shell=False )
					width = str(get_image_size("%s/.__temp_previz.jpg" % tmp)[0])
					height = str(get_image_size("%s/.__temp_previz.jpg" % tmp)[1])

					# import math
					import math
					nSlices = int(math.ceil(float(height)/float(settings["sliceSize"])))
					
					imgTag = ""
					for slcs in range(nSlices):						
						if int(settings["sliceSize"]) > float(height)-(slcs*float(settings["sliceSize"])):
							newSliceSize = float(height)-(slcs*float(settings["sliceSize"]))
						else:
							newSliceSize = settings["sliceSize"]

						# change the output file name adding number for slice
						if slcs == 0:
							ofile = outFile
						else:
							ofile = "%s_slice_%s.%s" % (outFile[:-4], str(slcs), settings["outputFormat"])

						# generate output files
						crop = '%sx%s+%s+%s' % (int(width), int(newSliceSize), 0, int(slcs*settings["sliceSize"]))
						
						subprocess.call(
							[userSettings["convert_app"],
							'-quality', str(settings["quality"]),
							inFile,
							'-crop', crop,
							ofile],
							shell=False
						)

						# generate html img tag to includo into html file
						imgTag += "\t\t\t<img src=\"%s\">\n" % os.path.basename(ofile)
						#subprocess.call( [userSettings["convert_app"], '-quality', str(settings["quality"]), inFile, outFile], shell=False )			

				# If only wants images
				if settings["onlyimage"] == False:
					# Creates html file
					htmlFile = htmlsFullPath[i]
					targetFile = tarHtmlsFullPath[i]
					html = open(htmlFile, "w")

					# Html params
					height = height
					webImageFile = os.path.basename(outFile)
					nextHtmlFile = os.path.basename(targetFile)

					# Html markup desktop
					if settings["mobile"] == False:
						html.write('\
\n<!--\
\n\
\n\tPynav 2014\
\n\tFrancis Vega\
\n\
\n\thisco@inartx.com\
\n\
\n-->\
\n\
\n<!DOCTYPE html>\
\n<html>\
\n\t<head>\
\n\t<title>' + settings["title"] + '</title>\
\n\
\n\t<style>\
\n\n\t\t/* Pynav default style*/\
\n\t\t* {\
\n\t\t\tpadding:0;\
\n\t\t\tmargin:0;\
\n\t\t}\
\n\t\t\
\n\t\tdiv {\
\n\t\t\theight:' + height + 'px;\
\n\t\t\tmargin:0 auto;\
\n\t\t\tbackground:url("' + webImageFile + '") top center no-repeat;\
\n\t\t}\
\n\
\n' + customCss + '\
\n\t</style>\
\n\t</head>\
\n\t<body>\
\n\t\t<a href="' + nextHtmlFile + '"><div></div></a>\
\n\t</body>\
\n</html>')
					else:
						html.write('\
\n<!--\
\n\
\n\tPynav 2014\
\n\tFrancis Vega\
\n\
\n\thisco@inartx.com\
\n\
\n-->\
\n\
\n<!DOCTYPE html>\
\n<html>\
\n\t<head>\
\n\t<title>' + settings["title"] + '</title>\
\n\
\n\t<style>\
\n\n\t\t/* Pynav default style*/\
\n\t\t* {\
\n\t\t\tpadding:0;\
\n\t\t\tmargin:0;\
\n\t\t}\
\n\
\n\t\t\
\n\t\timg {\
\n\t\t\twidth:100%;\
\n\t\t\theight:auto;\
\n\t\t\tdisplay:block;\
\n\t\t}\
\n\
\n\
\n' + customCss + '\
\n\t</style>\
\n\t</head>\
\n\t<body>\
\n\t\t<a href="' + nextHtmlFile + '">\n'+ imgTag +'\t\t</a>\
\n\t</body>\
\n</html>')

					html.close()

				if settings["fullPath"]:
					inFile = inFile[:-3]
					outFile = outFile
				else:
					inFile = os.path.basename(inFile)[:-3]
					outFile = os.path.basename(outFile)

				# Verbose MODDE
				if settings["verbose"]:
					elapsedConvert = (time.clock() - startConvertFile)
					msg = "%03d%% Converting %s to %s @ quality %s (OK) %s secs" % ((float((100.0/filesToConvert))*(i+1)), inFile, outFile, str(settings["quality"]), round(elapsedConvert,2))
					print msg
					logText_d += msg+"\n"
				else:
					msg = "%03d%% ... %s (OK)" % ((float((100.0/filesToConvert))*(i+1)), inFile)
					print msg
					logText_d += msg+"\n"

				fileConverted = fileConverted+1

			indexHTML += "\t<li><a href='%s'>%s</a></li>\n" % (os.path.basename(htmlsFullPath[i]), os.path.basename(outFile)[:-4])
		
		
		indexHTML = "\n<!--\n\n\tPynav 2014\n\tFrancis Vega\n\n\thisco@inartx.com\n\n-->\n\n<!DOCTYPE html>\n<html>\n<head>\n<title>Index of "+ settings["title"] +"</title>\n<style>\n\ta:visited{color: inherit;}\n\ta{color: black; text-decoration: none}\n\ta:hover{color: black; font-weight: bold;}\n\th1{margin: 20px 0 0 20px;}\n\tli{line-height: 1.6; }\n\tul{list-style: none; margin: 20px 0 0 20px;}\n\t*{font-family: Arial; border: 0; margin: 0; padding:0;}\n" + customCss + "</style>\n</head>\n<h1>Index of "+ settings["title"] +"</h1>\n<ul>\n%s</ul>\n</body>\n</html>" % indexHTML

	except KeyboardInterrupt:
		logText_e += "\n"
		logText_e += "Interrupted by a Motherfucker ;)\n"
		print logText_e

	import math
	elapsed = (time.clock() - start)
	logText_f += "\n"
	logText_f += "%s files converted in %s seconds\n" % (str(fileConverted), str(round(elapsed,2)))
	logText_f += "Mockup finished at [%s]\n" % settings["destinationPath"]
	print logText_f

	# Removes the temporal folder
	try:
		shutil.rmtree(tmp)
	except:
		pass

	# POST PROCESS

	if settings["logfile"]:
		# print "Created logfile at %s/pynavlog.txt" % settings["destinationPath"]
		log = open("%s/pynavlog.txt" % settings["destinationPath"], "w")
		log.write(logText_a + logText_b + logText_c + logText_d + logText_e + logText_f + "\n" + settings["date"].replace("_", "/"))
		log.close()

	if settings["index"]:
		idx = open("%s/index.html" % settings["destinationPath"], "w")
		idx.write(indexHTML)
		idx.close()

	if settings["zip"]:
		zip(settings["destinationPath"], "%s/%s.zip" % (settings["destinationPath"], os.path.basename(settings["destinationPath"])))

#
#	Start the dance!
#

# Users Settings
userSettings = {
	"convert_app": "C:/Program Files/Adobe/Adobe Photoshop CC (64 Bit)/convert.exe",
	"default_title": "Previz",
	"default_inputFormat": "psd",
	"default_outputFormat": "jpg",
	"default_outputDirName": "Pynav_",
	"default_quality": [100],
	"default_sliceSize": [1024]
}

# Load settings from pynav.conf
loadSettings(userSettings)

# Checks if the convert app path is correct
if not os.path.isfile(userSettings["convert_app"]):
	print "Error!"
	print "No se encuentra el archivo [%s]" % userSettings["convert_app"]
	print "Edita el path en pynav.conf correctamente"
	sys.exit()

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
PARSER.add_argument( "--log-file", "-l", dest="logfile", action="store_true", help="Create a log file" )
PARSER.add_argument( "--index-of-pages", "-index", dest="index", action="store_true", help="Create a index of pages" )
PARSER.add_argument( "--only-image", "-image", dest="onlyimage", action="store_true", help="Create just image files" )
PARSER.add_argument( "--mobile", "-m", dest="mobile", action="store_true", help="Mobile markup")
PARSER.add_argument( "--slice", "-slc", nargs=1, dest="slice", default=userSettings["default_sliceSize"], type=int, help="Set height slice for mobile" )
PARSER.add_argument( "--css-style", "-style", nargs=1, dest="css", default="", type=str, help="Add css style to all html files")
PARSER.add_argument( "--zip", "-z", dest="zip", action="store_true", help="Create a zip file with results files" )
PARSER.add_argument( "--flush", "-f", dest="flush", action="store_true", help="Delete all the content in the destination folder" )

# Gets parse arguments
args = PARSER.parse_args()

# Pynav internal settings
settings = {
	"customDestPath":False,
	"onlyimage": False,
	"date": time.strftime("%Y_%m_%d"),
	"sourcePath": os.path.abspath("".join(args.sourcePath)),
	"destinationPath": args.destinationPath,
	"pynavDirName": "%s%s" % (userSettings["default_outputDirName"], time.strftime("%Y-%m-%d"))
}

# Source Path (the only mandatory param)
# Checks if the sourcePath exists (and is a directory) if not, Pynav stops
if os.path.isdir(settings["sourcePath"]) == False:
	print ""
	print "El path origen [%s] no existe o no es un directorio" % settings["sourcePath"]
	sys.exit()

# Destination Path (optional)
# If destination path parameter doesnt exists pynav will create a custom directory
if settings["destinationPath"] == None:
	settings["destinationPath"] = "%s/%s" % (settings["sourcePath"], settings["pynavDirName"])
# If destination param exists, then pynav will use it to create the directory
else:
	settings["destinationPath"] = "".join(settings["destinationPath"])	
	settings["customDestPath"] = True

# If sourcePath and destPath are the same, pynav yield a warning, just for information.
if settings["sourcePath"] == settings["destinationPath"]:
	print "No es aconsejable que el directorio Origen y Destino sean el mismo\nConitunamos de todas formas? [y][n]"
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
settings["logfile"] = args.logfile
settings["index"] = args.index
settings["zip"] = args.zip
settings["onlyimage"] = args.onlyimage
settings["flush"] = args.flush
settings["sliceSize"] = args.slice[0]
settings["css"] = "".join(args.css)
if args.filename == None:
	settings["fileName"] = None
else:
	settings["fileName"] = args.filename[0]	

# Go with the flow!!
makePrevizNav(settings, userSettings)

# :)