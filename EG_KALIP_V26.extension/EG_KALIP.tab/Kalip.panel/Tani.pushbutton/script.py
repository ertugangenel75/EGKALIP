# -*- coding: utf-8 -*-
"""
EG_KALIP FINAL - Tani
Eleman sayimi ve hesap yontemi kontrolu icin tani ekrani.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from eg_kalip_core import calculate

from pyrevit import revit, forms

doc = revit.doc

rows, totals, grand, debug = calculate(doc, True)

msg_lines = debug[:]
if rows:
    msg_lines.append(u'')
    msg_lines.append(u'--- OZET ---')
    for k, v in sorted(totals.items()):
        msg_lines.append(u'{0}: {1:.2f} m\xb2'.format(k, v))
    msg_lines.append(u'TOPLAM: {0:.2f} m\xb2'.format(grand))

forms.alert(u'\n'.join(msg_lines), title=u'EG_KALIP Tani')
