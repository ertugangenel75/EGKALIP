# -*- coding: utf-8 -*-
"""
EG_KALIP - Parametre Butonu
Projede kalip parametrelerini olusturur:
  - Formwork_Area       (NUMBER / Double)
  - TR_KalipAlani       (TEXT)
  - TR_KalipPozNo       (TEXT)
  - TR_KalipPozAdi      (TEXT)
  - TR_KalipBirimFiyat  (SAYI / Number)
  - TR_KalipToplamTutar (NUMBER / Number)

Hedef elementler: Duvar, Kat (Floors), Yapisal Kiris, Kolon
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from eg_kalip_core import ensure_kalip_params

from pyrevit import revit, forms

doc = revit.doc

try:
    created, skipped = ensure_kalip_params(doc)
    msg_lines = [
        u"Parametre islemi tamamlandi.",
        u"",
        u"Olusturulan : {0}".format(created),
        u"Zaten mevcut: {0}".format(skipped),
        u"",
        u"Parametreler asagidaki eleman turlerine baglandi:",
        u"  - Yapisal Kolonlar",
        u"  - Yapisal Kirisler",
        u"  - Duvarlar",
        u"  - Dosemeler",
        u"  - Yapisal Temeller",
    ]
    forms.alert(u"\n".join(msg_lines), title=u"EG_KALIP - Parametre")
except Exception as ex:
    forms.alert(
        u"Parametre olusturma hatasi:\n\n" + str(ex),
        title=u"EG_KALIP - Parametre Hatasi"
    )
