# -*- coding: utf-8 -*-
"""EG_KALIP v25 - Metraj + HTML Rapor"""
import sys, os, webbrowser, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from eg_kalip_core   import calculate, write_back_all, ensure_kalip_params
from eg_kalip_report import save_report
from pyrevit import revit, forms

doc = revit.doc

try:
    project_name = doc.ProjectInformation.Name or u'Proje'
except Exception:
    project_name = u'Proje'

# ── Seçenekler ─────────────────────────────────────────────
SECENEKLER = [
    u'Doseme kenar kalibini dahil et',
    u'Hesaplanan degerleri Revit parametrelerine yaz',
    u'HTML Rapor olustur ve ac',
]

secimler = forms.SelectFromList.show(
    SECENEKLER,
    title=u'EG_KALIP v25',
    button_name=u'Hesapla',
    multiselect=True,
    checked_only=False,
)
if secimler is None:
    raise SystemExit

include_edges = SECENEKLER[0] in secimler
do_write      = SECENEKLER[1] in secimler
do_report     = SECENEKLER[2] in secimler

# ── Hesapla ────────────────────────────────────────────────
rows, totals, grand, debug, trace_dict = calculate(doc, include_edges)

if not rows:
    forms.alert(
        u'Hesaplanacak eleman bulunamadi.\n\n' + u'\n'.join(debug),
        title=u'EG_KALIP v25')
    raise SystemExit

# ── Parametrelere yaz ──────────────────────────────────────
if do_write:
    try:
        fw, poz, skip = write_back_all(doc, rows)
        forms.alert(
            u'Parametre yazma tamamlandi.\n'
            u'Formwork_Area : {0}\n'
            u'PozNo atanan  : {1}\n'
            u'PozNo korunan : {2}'.format(fw, poz, skip),
            title=u'EG_KALIP v25')
    except Exception as ex:
        forms.alert(u'Parametre hatasi:\n' + str(ex), title=u'EG_KALIP v25')

# ── HTML Rapor ─────────────────────────────────────────────
if do_report:
    try:
        out_dir = tempfile.gettempdir()
        path = save_report(rows, totals, grand, trace_dict,
                           project_name=project_name, out_dir=out_dir)
        webbrowser.open(u'file:///' + path.replace('\\', '/'))
    except Exception as ex:
        forms.alert(u'Rapor hatasi:\n' + str(ex), title=u'EG_KALIP v25')

# ── Özet alert ─────────────────────────────────────────────
CAT_TR = {
    u'Structural Columns':     u'Kolon',
    u'Structural Framing':     u'Kiris',
    u'Walls':                  u'Duvar',
    u'Floors':                 u'Doseme',
    u'Floors_Edge':            u'Doseme Kenar',
    u'Structural Foundations': u'Temel',
}
lines = []
for k, v in sorted(totals.items()):
    lines.append(u'{0} : {1:.2f} m2'.format(CAT_TR.get(k, k), v))
lines.append(u'-----------------------------------')
lines.append(u'TOPLAM : {0:.2f} m2'.format(grand))
lines.append(u'Eleman : {0}'.format(len(rows)))
lines.append(u'Kenar  : {0}'.format(u'Dahil' if include_edges else u'Haric'))
if do_report:
    lines.append(u'')
    lines.append(u'Rapor tarayicide acildi.')

forms.alert(u'\n'.join(lines), title=u'EG_KALIP v25 Sonuc')
