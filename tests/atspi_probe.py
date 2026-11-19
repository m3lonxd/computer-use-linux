#!/usr/bin/env python3
"""Küçük GTK3 penceresi: adlı bir düğme; basılınca log'a {"type":"activate"} yazar.
AT-SPI ile isimle bulma/tıklama testleri için.   atspi_probe.py <log.jsonl>"""
import json
import sys

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

log = open(sys.argv[1], "a", buffering=1)
win = Gtk.Window(title="nexr-atspi-probe")
win.set_default_size(300, 120)
btn = Gtk.Button(label="NexProbeButton")
btn.connect("clicked", lambda _b: log.write(json.dumps({"type": "activate"}) + "\n"))
win.add(btn)
win.connect("destroy", Gtk.main_quit)
win.show_all()
log.write(json.dumps({"type": "atspi-ready"}) + "\n")
Gtk.main()
