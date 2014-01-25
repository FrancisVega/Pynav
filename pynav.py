"""Pynav.

Usage:
  pynav create <src> [<dst>] [-iwz] [--quality=QUALITY] [--output=FORMAT] [--input=FORMAT]
               [--mode=(img|back)] [--html=FILE] [--css=STYLE]
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
  --mode=(img|back)             Modes [default: img]
  --html=FILE                   Use FILE (html) template
  --css=STYLE                   Add custom css styles

Examples:
  pynav create d:/Dropbox/Secuoyas/web/visual/ -iwz
  pynav set --quality=20 --css=body { background: #000000; }

"""
from docopt import docopt


args = docopt(__doc__, version='Pynav 0.1')
# args = docopt(__doc__, argv="create d:/Dropbox/Secuoyas/web/visual/ d:/jps/ -iwz -q80", version='Pynav 0.1')
print (args)