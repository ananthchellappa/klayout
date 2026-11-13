# Voice not installed (LAYOUT_XL_DATA points nowhere): a tap explains, nothing breaks.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # KLayout ignores PYTHONPATH
import pya
from common import spin, check, done
from layout_xl import voice

v = voice.install()
spin(1)
check("no helper started", v.proc, None)
check("installed() says why", voice.installed()[0], False)
v.tap(); spin(1)
check("tap without install: still no helper", v.proc, None)
done()
