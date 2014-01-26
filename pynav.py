"""Pynav.

Usage:
  pynav create <src> [<dst>] [-iwz] [--quality=QUALITY] [--output=FORMAT] [--input=FORMAT]
               [--mobile] [--html=FILE] [--css=STYLE] [--title=TITLE] [--slice=SIZE] [--naming=PREFIX]
  pynav set [--quality=QUALITY]

Commands:
  create                        Main command to create navigation
  set                           Command to write default values into config file

Arguments:
  <src>                         Source directory with image files
  <dst>                         Destination directory to write output files
  QUALITY                       Integer between (1-100)
  FILE                          Valid file name
  STYLE                         Valid css style
  FORMAT                        Image format (jpg|png)

Options:
  -h --help                     show this help message and exit
  --version                     show version and exit
  -i --index                    Create a index.html containing all pages
  -w --overwrite                Overwrite existings files
  -z --zip                      Archive output files
  -f --input=FORMAT             [default: psd]
  -o --output=FORMAT            [default: jpg]
  -q --quality=QUALITY          [default: 99]
  -m --mobile                   Modes [default: img]
  --html=FILE                   Use FILE (html) template
  --css=STYLE                   Add custom css styles
  --slice=SIZE                  [default: 1024]

Examples:
  pynav create d:/Dropbox/Secuoyas/web/visual/ -iwz
  pynav set --quality=20 --css=body { background: #000000; }

"""

from __future__ import print_function
from docopt import docopt
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

def load_template(file_tpl):
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
    ext = os.path.splitext(fname)[1]

    if ext == ".psd":
        fhandle.read(14)
        height, width = struct.unpack("!LL", fhandle.read(8))
        fhandle.close()
    else:
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
        zf.write(os.path.join(abs_src, f), os.path.basename(f))
    zf.close()





def pynav(src, dst, quality, input, output, mobile, title, overwrite, index, zip, slice, css, naming, desktopSheet, mobileSheet):

    # Dictionary items into vars.
    # pynav_convert_app = settings["convert_app"]
    # pynav_quality = str(settings["quality"])
    # pynav_input_format = str(settings["inputFormat"])
    # pynav_output_format = str(settings["outputFormat"])
    # pynav_mobile = settings["mobile"]
    # pynav_title = str(settings["title"])
    # pynav_overwrite = settings["overwrite"]
    # pynav_verbose = settings["verbose"]
    # pynav_fullPath = settings["fullPath"]
    # pynav_index = settings["index"]
    # pynav_zip = settings["zip"]
    # pynav_only_image = settings["onlyimage"]
    # pynav_flush = settings["flush"]
    # pynav_slice_size = float(settings["sliceSize"])
    # pynav_css = str(settings["css"])
    # pynav_mobl_tpl = str(settings["mobileSheet"])
    # pynav_desk_tpl = str(settings["desktopSheet"])
    # pynav_dest = os.path.abspath(settings["destinationPath"])
    # pynav_src = os.path.abspath(settings["sourcePath"])
    # pynav_file_name = settings["fileName"]

    # Timing!
    start = time.clock()

    # Setup paths
    if src: src = os.path.abspath(src)
    if dst: dst = os.path.abspath(dst)

    # Set default dst if dst doesn't exists
    if not dst: dst = os.path.join(src, "Pynav_{0}".format(time.strftime("%Y-%m-%d")))

    # Get source files with input format.
    source_files = get_files_from_folder(src, input)
    if not source_files:
        errprint("No existen archivos tipo {0} en el directorio {1}".format(input, src))
        sys.exit()

    # <dst> dir creation.
    if not os.path.exists(dst):
        os.makedirs(dst)

    # --naming
    if naming:
        imgs_full_path = [os.path.abspath("{}/{}_{:02d}.{}".format(dst, naming, n, output)) for n in range(len(source_files))]
        html_full_path = [os.path.abspath("{}/{}_{:02d}.html".format(dst, naming, n)) for n in range(len(source_files))]
    else:        
        imgs_full_path = [os.path.abspath("{0}/{1}.{2}".format(dst, f, output)) for f in [os.path.basename(f[:-4]) for f in source_files]]
        html_full_path = [os.path.abspath("{0}/{1}.html".format(dst, f)) for f in [os.path.basename(f[:-4]) for f in source_files]]

    # Pynav <a href> target htmls
    target_html_full_path = shift(html_full_path, 1)

    index_anchor_tag = ""
    
    # Start
    print("\nPynav. Francis Vega 2014", end="\n")
    print("Simple Navigation html+image from image files", end="\n\n")
    # Verbose
    if True:
        print("Convert formats: {0} to {1}".format(input, output), end="\n")
        print("Source Path {0}".format(src), end="\n")
        print("Destination Path {0}".format(dst), end="\n\n")

    try:
        file_converted = 0
        files_to_convert = len(source_files)

        # --css-style
        customCss = ""
        if css:
            customCss = "/* CSS Style Command Inline*/\n{0}".format(css)

        # File by file
        for i in range(files_to_convert):

            inFile = source_files[i]
            outFile = imgs_full_path[i]

            # If file exists and overwrite == False, skip
            fileExists = os.path.isfile(outFile)
            if fileExists and overwrite == False:
                path = os.path.basename(inFile)
                pct = int(100.0 / files_to_convert) * (i + 1)
                print ("{:03d}% ... {} (Skip)".format(pct, path), end="\n")

            else:
                # Select correct HTML Sheet
                if mobile:
                    Convert_HTML_template = mobileSheet
                else:
                    Convert_HTML_template = desktopSheet

                size = get_image_size(inFile)

                width = str(size[0])
                height = str(size[1])

                nSlices = int(math.ceil(float(height) / slice))

                slice_images = []
                for slcs in range(nSlices):
                    newSliceSize = slice

                    if int(slice) > float(height) - (slcs * slice):
                        newSliceSize = float(height) - (slcs * slice)

                    # change the output file name adding number for slice
                    ofile = outFile

                    if slcs > 0:
                        ofile = "{0}_slice_{1}.{2}".format(outFile[:-4], str(slcs), output)

                    # generate output files
                    crop = '{0}x{1}+{2}+{3}'.format(int(width), int(newSliceSize), 0, int(slcs * slice))

                    # convert
                    # hack adding [0] suffix to flat psd when call to convert app
                    if input == "psd":
                        convertFile = "{0}[0]".format(inFile)
                    else:
                        convertFile = inFile

                    # call to convert app
                    subprocess.call(
                        [settings["convert_app"], '-quality', quality, convertFile, '-crop', crop, ofile],
                        shell=False
                    )

                    # Generate html img tag to include into html file
                    slice_images.append(os.path.basename(ofile))

                # Creates html file
                htmlFile = html_full_path[i]
                targetFile = target_html_full_path[i]
                
                html = open(htmlFile, "w")

                # Html params
                nextHtmlFile = os.path.basename(targetFile)
                webImageFile = os.path.basename(outFile)

                # Replace custom tags
                tags = Convert_HTML_template
                tags = tags.replace("[pynav-title]", title)
                tags = tags.replace("[pynav-css]", "CSS")
                tags = tags.replace("[pynav-img-width]", width)
                tags = tags.replace("[pynav-img-height]", height)
                tags = tags.replace("[pynav-next-html]", nextHtmlFile)

                
                if mobile:
                    # Replace [pynav-img] with multiples img tags in case of slicing
                    # first, grab the whole <img> tag
                    img_tag = re.search("<[^>]+\[pynav-img\][^>]+>", tags).group()
                    
                    multiple_slice_images_with_img_tag = ""
                    for img in slice_images:
                        multiple_slice_images_with_img_tag += img_tag.replace("[pynav-img]", img)

                    # Add <img> tags to final data to write html file
                    tags = tags.replace(img_tag, multiple_slice_images_with_img_tag)
                else:
                    tags = tags.replace("[pynav-img]", slice_images[0])

                # Write html
                html.write(tags)
                html.close()

                # --full-path
                inFile = os.path.basename(inFile)
                outFile = os.path.basename(outFile)

                # Print info into terminal
                print("{:03d}% ... {}".format(int((100.0 / files_to_convert) * (i + 1)), inFile))

                file_converted = file_converted + 1

            index_anchor_tag += "<li><a href='{0}'>{1}</a></li>\n".format(\
                os.path.basename(html_full_path[i]), os.path.basename(outFile)[:-4]\
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
\n</html>".format(title, customCss, index_anchor_tag)

    except KeyboardInterrupt:
        print("", end="\n")
        print("\nInterrupted by a user", end="\n")

    elapsed = (time.clock() - start)
    print("", end="\n")
    print("{0} files converted in {1} seconds".format(str(file_converted), str(round(elapsed,2))), end="\n\n")
    print("Mockup finished at {0}".format(os.path.abspath(dst)), end="\n\n")

    # Removes the temporal folder
    try:
        shutil.rmtree(tmp)
    except:
        pass

    # --index-of-pages
    if index:
        index = open(os.path.join(dst, INDEX_PAGE_NAME), "w")
        index.write(indexHTML)
        index.close()

    # --zip
    if zip:
        zip_file_name = "{0}.zip".format(os.path.basename(dst))
        zip_path_name = os.path.join(dst, zip_file_name)
        zip(dst, zip_path_name)
        print("Mockup zipped at {0}".format(zip_path_name), end="\n\n")


# Html templates

try:
    desktopSheet = load_template(DESKTOP_HTML_SHEET)
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
    mobileSheet = load_template(MOBILE_HTML_SHEET)
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
\n        </a>\
\n    </body>\
\n</html>"

# Fill user settings with some default
settings = {
        "convert_app": "C:/Program Files/Adobe/Adobe Photoshop CC (64 Bit)/convert.exe",
        "dir_name": "Pynav_"
}

# settings = docopt(__doc__, version='Pynav 0.1')
args = docopt(__doc__, argv="create E:/Dropbox/github/pynav/psd-project -iwm -q80", version='Pynav 0.1')

# set defaults
if not args["--title"]:
    args["--title"] = "custom_title"

pynav(
    args["<src>"],
    args["<dst>"],
    args["--quality"],
    args["--input"],
    args["--output"],
    args["--mobile"],
    args["--title"],
    args["--overwrite"],
    args["--index"],
    args["--zip"],
    float(args["--slice"]),
    args["--css"],
    args["--naming"],
    desktopSheet,
    mobileSheet
)