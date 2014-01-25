"""Pynav.

Usage:
  pynav.py <src> [<dst>] [-iwz] [--quality=QUALITY] [--output-format=FORMAT] [--input-format=FORMATe]
  pynav.py set (--quality=QUALITY|--mode=(img|back))
  pynav.py --version

Commands:
  set                           Write into the config file

Options:
  -h --help                     show this help message and exit
  --version                     show version and exit
  -i --index                    Create a index.html containing all pages
  -w --overwrite                Overwrite existings files
  --FLUSH                       Clean target directory (risky)
  -f --input-format=FORMATe     [default: psd]
  -o --output-format=FORMAT     [default: jpg]
  -q --quality=QUALITY          [default: 99]
  -m --mode=(img|back)          Modes [default: img]

"""
from docopt import docopt


args = docopt(__doc__, version='Naval Fate 2.0')
print(args)