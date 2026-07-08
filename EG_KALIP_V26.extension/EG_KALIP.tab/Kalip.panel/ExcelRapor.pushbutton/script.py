# -*- coding: utf-8 -*-
"""
EG_KALIP FINAL - Excel XML Raporu  v22
Detay sayfasi:
  No | Tip/Aile | Poz No | Poz Aciklama | Seviye | Kalip Alani (m2) | Element Id
  Doseme Kenar ayri baslik + satirlar olarak gosterilir.
Ozet: poz bazli 6 sutun.
"""
import sys, os, codecs
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from eg_kalip_core import calculate, KALIP_POZLAR, _DEFAULT_POZ
def esc(s):
    if s is None: return u''
    return (u'{0}'.format(s).replace(u'&',u'&amp;').replace(u'<',u'&lt;').replace(u'>',u'&gt;').replace(u'"',u'&quot;'))

from pyrevit import revit, forms

doc = revit.doc
try:
    project_name = doc.ProjectInformation.Name or u"Proje"
except Exception:
    project_name = u"Proje"

SECENEKLER = [u"Doseme kenar kalibini dahil et"]
try:
    secimler = forms.SelectFromList.show(
        SECENEKLER,
        title=u"EG_KALIP - Excel Raporu Secenekleri",
        button_name=u"Rapor Olustur",
        multiselect=True,
        checked_only=False,
    )
    if secimler is None:
        raise SystemExit
    include_edges = SECENEKLER[0] in secimler
except Exception:
    include_edges = False

rows, totals, grand, debug, _trace = calculate(doc, include_edges)

if not rows:
    forms.alert(u"Raporlanacak eleman bulunamadi.\n\n" + u"\n".join(debug), title=u"EG_KALIP")
    raise SystemExit

save_path = forms.save_file(file_ext='xml', default_name='EG_KALIP_Raporu')
if not save_path:
    raise SystemExit
if not save_path.lower().endswith('.xml'):
    save_path += '.xml'

# ============================================================
# Yardimcilar
# ============================================================
CAT_TR = {
    u"Structural Columns":     u"Kolon",
    u"Structural Framing":     u"Kiris",
    u"Walls":                  u"Duvar",
    u"Floors":                 u"Doseme",
    u"Structural Foundations": u"Temel",
    u"Floors_Edge":            u"Doseme Kenar",
}
def tr(cat): return CAT_TR.get(cat, cat)

date_str  = datetime.now().strftime(u"%d.%m.%Y %H:%M")
edge_text = u"Doseme kenar dahil" if include_edges else u"Sadece doseme alti"

# Detay icin: "Floors_Edge" metodlu satirlari ayri kategori olarak goster
# method == "floor_net_edge" veya "floor_stage_logic_union_edge" → Doseme Kenar
# Kat x kategori capraz — Floors_Edge otomatik ayri sutun olarak gelir
# (calculate() artik Floors ve Floors_Edge ayri satirlar uretir)
all_cats = sorted(totals.keys())
cross = {}
for r in rows:
    lv = r['level'] or u'(Seviyesiz)'
    cross.setdefault(lv, {})
    cross[lv][r['category']] = cross[lv].get(r['category'], 0.0) + r['area_m2']

# Detay gruplama — category direkt kullanilir
# Floors_Edge: area_m2 < 0.005 (2 basamakta 0.00 gozukur) satirlari filtrele
cat_lv_rows = {}
for r in rows:
    cat = r['category']
    if cat == 'Floors_Edge' and r['area_m2'] < 0.005:
        continue
    lv  = r['level'] or u'(Seviyesiz)'
    cat_lv_rows.setdefault(cat, {}).setdefault(lv, []).append(r)

# Sirala: gercek kategoriler once, _Edge sona
det_cats_real  = sorted([c for c in cat_lv_rows if not c.endswith('_Edge')])
det_cats_edge  = sorted([c for c in cat_lv_rows if c.endswith('_Edge')])
det_cats_order = det_cats_real + det_cats_edge

# Poz ozet
poz_ozet = {}
for r in rows:
    poz_no   = r.get('poz_no', _DEFAULT_POZ.get(r['category'], '15.180.1002'))
    poz_info = KALIP_POZLAR.get(poz_no, {})
    if poz_no not in poz_ozet:
        poz_ozet[poz_no] = {
            'tanim': poz_info.get('tanim', poz_no),
            'fiyat': poz_info.get('fiyat', 0.0),
            'alan':  0.0,
        }
    poz_ozet[poz_no]['alan'] += r['area_m2']

# ============================================================
# Stil blogu
# ============================================================
STYLES = u"""<Styles>
  <Style ss:ID="s_title">
    <Font ss:Bold="1" ss:Size="13" ss:Color="#FFFFFF"/>
    <Interior ss:Color="#1F4E79" ss:Pattern="Solid"/>
    <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>
  </Style>
  <Style ss:ID="s_meta">
    <Font ss:Italic="1" ss:Size="9" ss:Color="#FFFFFF"/>
    <Interior ss:Color="#2E75B6" ss:Pattern="Solid"/>
    <Alignment ss:Horizontal="Left" ss:Vertical="Center"/>
  </Style>
  <Style ss:ID="s_hdr">
    <Font ss:Bold="1" ss:Color="#FFFFFF"/>
    <Interior ss:Color="#2E75B6" ss:Pattern="Solid"/>
    <Alignment ss:Horizontal="Center" ss:Vertical="Center" ss:WrapText="1"/>
    <Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFBFBF"/>
    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFBFBF"/></Borders>
  </Style>
  <Style ss:ID="s_hdr_r">
    <Font ss:Bold="1" ss:Color="#FFFFFF"/>
    <Interior ss:Color="#2E75B6" ss:Pattern="Solid"/>
    <Alignment ss:Horizontal="Right" ss:Vertical="Center" ss:WrapText="1"/>
    <Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFBFBF"/>
    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFBFBF"/></Borders>
  </Style>
  <Style ss:ID="s_cat">
    <Font ss:Bold="1" ss:Color="#FFFFFF"/>
    <Interior ss:Color="#2E75B6" ss:Pattern="Solid"/>
    <Alignment ss:Horizontal="Left" ss:Vertical="Center"/>
  </Style>
  <Style ss:ID="s_cat_edge">
    <Font ss:Bold="1" ss:Color="#FFFFFF"/>
    <Interior ss:Color="#1A6B3C" ss:Pattern="Solid"/>
    <Alignment ss:Horizontal="Left" ss:Vertical="Center"/>
  </Style>
  <Style ss:ID="s_lv">
    <Font ss:Bold="1" ss:Color="#1F4E79" ss:Size="10"/>
    <Interior ss:Color="#D6E4F0" ss:Pattern="Solid"/>
    <Alignment ss:Horizontal="Left" ss:Vertical="Center"/>
    <Borders><Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#2E75B6"/>
    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#2E75B6"/></Borders>
  </Style>
  <Style ss:ID="s_even">
    <Interior ss:Color="#EBF5FB" ss:Pattern="Solid"/>
    <Alignment ss:Horizontal="Left" ss:Vertical="Center"/>
    <Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFBFBF"/>
    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFBFBF"/></Borders>
  </Style>
  <Style ss:ID="s_even_num">
    <Interior ss:Color="#EBF5FB" ss:Pattern="Solid"/>
    <Alignment ss:Horizontal="Right" ss:Vertical="Center"/>
    <NumberFormat ss:Format="#,##0.00"/>
    <Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFBFBF"/>
    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFBFBF"/></Borders>
  </Style>
  <Style ss:ID="s_odd">
    <Alignment ss:Horizontal="Left" ss:Vertical="Center"/>
    <Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFBFBF"/>
    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFBFBF"/></Borders>
  </Style>
  <Style ss:ID="s_odd_num">
    <Alignment ss:Horizontal="Right" ss:Vertical="Center"/>
    <NumberFormat ss:Format="#,##0.00"/>
    <Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFBFBF"/>
    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFBFBF"/></Borders>
  </Style>
  <Style ss:ID="s_subtotal">
    <Font ss:Bold="1" ss:Color="#1F4E79"/>
    <Interior ss:Color="#AED6F1" ss:Pattern="Solid"/>
    <Alignment ss:Horizontal="Right" ss:Vertical="Center"/>
    <NumberFormat ss:Format="#,##0.00"/>
    <Borders><Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="2" ss:Color="#2E75B6"/>
    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="2" ss:Color="#2E75B6"/></Borders>
  </Style>
  <Style ss:ID="s_subtotal_lbl">
    <Font ss:Bold="1" ss:Color="#1F4E79"/>
    <Interior ss:Color="#AED6F1" ss:Pattern="Solid"/>
    <Alignment ss:Horizontal="Right" ss:Vertical="Center"/>
    <Borders><Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="2" ss:Color="#2E75B6"/>
    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="2" ss:Color="#2E75B6"/></Borders>
  </Style>
  <Style ss:ID="s_total">
    <Font ss:Bold="1" ss:Size="11" ss:Color="#C0392B"/>
    <Interior ss:Color="#FAD7A0" ss:Pattern="Solid"/>
    <Alignment ss:Horizontal="Right" ss:Vertical="Center"/>
    <NumberFormat ss:Format="#,##0.00"/>
    <Borders><Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="2" ss:Color="#C0392B"/>
    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="2" ss:Color="#C0392B"/></Borders>
  </Style>
  <Style ss:ID="s_total_lbl">
    <Font ss:Bold="1" ss:Size="11" ss:Color="#C0392B"/>
    <Interior ss:Color="#FAD7A0" ss:Pattern="Solid"/>
    <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>
    <Borders><Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="2" ss:Color="#C0392B"/>
    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="2" ss:Color="#C0392B"/></Borders>
  </Style>
  <Style ss:ID="s_cross_hdr">
    <Font ss:Bold="1" ss:Color="#FFFFFF" ss:Size="9"/>
    <Interior ss:Color="#1F4E79" ss:Pattern="Solid"/>
    <Alignment ss:Horizontal="Center" ss:Vertical="Center" ss:WrapText="1"/>
    <Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFBFBF"/>
    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFBFBF"/></Borders>
  </Style>
  <Style ss:ID="s_cross_lv">
    <Font ss:Bold="1" ss:Color="#1F4E79" ss:Size="9"/>
    <Interior ss:Color="#D6E4F0" ss:Pattern="Solid"/>
    <Alignment ss:Horizontal="Left" ss:Vertical="Center"/>
    <Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFBFBF"/>
    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFBFBF"/></Borders>
  </Style>
  <Style ss:ID="s_cross_num">
    <Font ss:Size="9"/>
    <Alignment ss:Horizontal="Right" ss:Vertical="Center"/>
    <NumberFormat ss:Format="#,##0.00"/>
    <Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFBFBF"/>
    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFBFBF"/></Borders>
  </Style>
  <Style ss:ID="s_cross_num_even">
    <Font ss:Size="9"/>
    <Interior ss:Color="#EBF5FB" ss:Pattern="Solid"/>
    <Alignment ss:Horizontal="Right" ss:Vertical="Center"/>
    <NumberFormat ss:Format="#,##0.00"/>
    <Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFBFBF"/>
    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFBFBF"/></Borders>
  </Style>
  <Style ss:ID="s_cross_zero">
    <Font ss:Size="9" ss:Color="#CCCCCC"/>
    <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>
    <Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFBFBF"/>
    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFBFBF"/></Borders>
  </Style>
  <Style ss:ID="s_cross_zero_even">
    <Font ss:Size="9" ss:Color="#CCCCCC"/>
    <Interior ss:Color="#EBF5FB" ss:Pattern="Solid"/>
    <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>
    <Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFBFBF"/>
    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFBFBF"/></Borders>
  </Style>
  <Style ss:ID="s_cross_total">
    <Font ss:Bold="1" ss:Color="#C0392B" ss:Size="9"/>
    <Interior ss:Color="#FAD7A0" ss:Pattern="Solid"/>
    <Alignment ss:Horizontal="Right" ss:Vertical="Center"/>
    <NumberFormat ss:Format="#,##0.00"/>
    <Borders><Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="2" ss:Color="#C0392B"/>
    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="2" ss:Color="#C0392B"/></Borders>
  </Style>
  <Style ss:ID="s_note">
    <Font ss:Italic="1" ss:Size="9" ss:Color="#555555"/>
    <Alignment ss:Horizontal="Left" ss:Vertical="Center"/>
  </Style>
  <Style ss:ID="s_id">
    <Font ss:Size="9" ss:Color="#888888"/>
    <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>
    <Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFBFBF"/>
    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFBFBF"/></Borders>
  </Style>
  <Style ss:ID="s_id_even">
    <Font ss:Size="9" ss:Color="#888888"/>
    <Interior ss:Color="#EBF5FB" ss:Pattern="Solid"/>
    <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>
    <Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFBFBF"/>
    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFBFBF"/></Borders>
  </Style>
</Styles>"""

def S(st, tp, val):
    v = esc(u'{0}'.format(val)) if not isinstance(val, float) else u'{0}'.format(val)
    return u'<Cell ss:StyleID="{0}"><Data ss:Type="{1}">{2}</Data></Cell>'.format(st, tp, v)
def SN(st, val):
    return u'<Cell ss:StyleID="{0}"><Data ss:Type="Number">{1}</Data></Cell>'.format(st, round(val, 2))
def MERGE(st, tp, val, span):
    v = esc(u'{0}'.format(val))
    return u'<Cell ss:StyleID="{0}" ss:MergeAcross="{1}"><Data ss:Type="{2}">{3}</Data></Cell>'.format(st, span-1, tp, v)
def ROW(cells, h=None):
    hattr = u' ss:Height="{0}"'.format(h) if h else u''
    return u'<Row{0}>{1}</Row>'.format(hattr, u''.join(cells))
def EROW(h=4):
    return u'<Row ss:Height="{0}"/>'.format(h)

# ============================================================
# 1. OZET — poz bazli 6 sutun
# ============================================================
OZET_COLS = 6
ozet = []
ozet.append(ROW([MERGE('s_title','String', u'EG_KALIP FINAL \u2014 Kal\u0131p Metraj \xd6zeti', OZET_COLS)], h=30))
ozet.append(ROW([MERGE('s_meta','String',
    u'Proje: {0}    |    Tarih: {1}    |    {2}'.format(project_name, date_str, edge_text),
    OZET_COLS)], h=16))
ozet.append(EROW(6))
ozet.append(ROW([
    S('s_hdr',   'String', u'TR Poz No'),
    S('s_hdr',   'String', u'TR Poz A\xe7\u0131klamas\u0131'),
    S('s_hdr_r', 'String', u'Kal\u0131p Alan\u0131 (m\xb2)'),
    S('s_hdr',   'String', u'Birim'),
    S('s_hdr_r', 'String', u'Birim Fiyat (TL/m\xb2)'),
    S('s_hdr_r', 'String', u'Toplam (TL)'),
], h=22))

poz_grand_alan = poz_grand_toplam = 0.0
for i, poz_no in enumerate(sorted(poz_ozet.keys())):
    pd     = poz_ozet[poz_no]
    alan   = pd['alan']
    fiyat  = pd['fiyat']
    toplam = alan * fiyat
    poz_grand_alan   += alan
    poz_grand_toplam += toplam
    ev = (i % 2 == 0)
    ts = 's_even' if ev else 's_odd'
    tn = 's_even_num' if ev else 's_odd_num'
    ozet.append(ROW([
        S(ts,  'String', esc(poz_no)),
        S(ts,  'String', esc(pd['tanim'])),
        SN(tn, alan),
        S(ts,  'String', u'm\xb2'),
        SN(tn, fiyat),
        SN(tn, toplam),
    ], h=18))

ozet.append(EROW(4))
ozet.append(ROW([
    MERGE('s_total_lbl','String', u'GENEL TOPLAM', 2),
    SN('s_total', poz_grand_alan),
    S('s_total_lbl','String', u'm\xb2'),
    S('s_total_lbl','String', u''),
    SN('s_total', poz_grand_toplam),
], h=24))
ozet.append(EROW(6))
ozet.append(ROW([MERGE('s_note','String',
    u'Toplam hesaplanan eleman: {0}    |    {1}'.format(len(rows), edge_text),
    OZET_COLS)], h=14))

ws_ozet = (
    u'<Worksheet ss:Name="Ozet"><Table ss:DefaultRowHeight="16">'
    u'<Column ss:Width="110"/><Column ss:Width="280"/>'
    u'<Column ss:Width="110"/><Column ss:Width="50"/>'
    u'<Column ss:Width="120"/><Column ss:Width="120"/>\n'
    + u'\n'.join(ozet)
    + u'\n</Table></Worksheet>'
)

# ============================================================
# 2. KAT x KATEGORI
# ============================================================
n_cats     = len(all_cats)
total_span = 1 + n_cats + 1
cross_rows = []
cross_rows.append(ROW([MERGE('s_title','String', u'Kat \xd7 Kategori \u2014 \xc7apraz Tablo', total_span)], h=28))
cross_rows.append(ROW([MERGE('s_meta','String',
    u'Proje: {0}    |    Tarih: {1}'.format(project_name, date_str), total_span)], h=14))
cross_rows.append(EROW(5))
hdr = [S('s_cross_hdr','String', u'Seviye / Kat')]
for cat in all_cats:
    hdr.append(S('s_cross_hdr','String', tr(cat)))
hdr.append(S('s_cross_hdr','String', u'Sat\u0131r Toplam\u0131'))
cross_rows.append(ROW(hdr, h=22))

col_sums = {cat: 0.0 for cat in all_cats}
for ri, lv in enumerate(sorted(cross.keys())):
    ev    = (ri % 2 == 0)
    cells = [S('s_cross_lv','String', lv)]
    row_sum = 0.0
    for cat in all_cats:
        val = cross[lv].get(cat, 0.0)
        col_sums[cat] += val
        row_sum += val
        if val > 0:
            cells.append(SN('s_cross_num_even' if ev else 's_cross_num', val))
        else:
            cells.append(S('s_cross_zero_even' if ev else 's_cross_zero','String', u'\u2014'))
    cells.append(SN('s_cross_num_even' if ev else 's_cross_num', row_sum))
    cross_rows.append(ROW(cells, h=16))

tot_cells = [S('s_cross_hdr','String', u'TOPLAM')]
row_grand = 0.0
for cat in all_cats:
    tot_cells.append(SN('s_cross_total', col_sums[cat]))
    row_grand += col_sums[cat]
tot_cells.append(SN('s_cross_total', row_grand))
cross_rows.append(ROW(tot_cells, h=22))

cross_col_defs = (
    u'<Column ss:Width="120"/>'
    + u'<Column ss:Width="90"/>' * n_cats
    + u'<Column ss:Width="110"/>'
)
ws_cross = (
    u'<Worksheet ss:Name="Kat x Kategori"><Table ss:DefaultRowHeight="16">'
    + cross_col_defs + u'\n'
    + u'\n'.join(cross_rows)
    + u'\n</Table></Worksheet>'
)

# ============================================================
# 3. DETAY — 7 sutun
# No | Tip/Aile | Poz No | Poz Aciklama | Seviye | Kalip Alani (m2) | Element Id
# Doseme Kenar ayri baslik + satirlar
# ============================================================
DET_COLS = 7
DET_HDRS = [
    u'No', u'Tip / Aile',
    u'Poz No', u'Poz A\xe7\u0131klama',
    u'Seviye', u'Kal\u0131p Alan\u0131 (m\xb2)', u'Element Id'
]

det = []
det.append(ROW([MERGE('s_title','String', u'EG_KALIP FINAL \u2014 Detay Raporu', DET_COLS)], h=28))
det.append(ROW([MERGE('s_meta','String',
    u'Proje: {0}    |    Tarih: {1}    |    {2}'.format(project_name, date_str, edge_text),
    DET_COLS)], h=14))
det.append(EROW(5))

seq = 0
for dc in det_cats_order:
    lv_map = cat_lv_rows[dc]

    # Kategori alan toplami (display cat icin)
    dc_total = sum(
        r['area_m2']
        for lv_rows in lv_map.values()
        for r in lv_rows
    )

    is_edge = dc.endswith('_Edge')
    cat_style = 's_cat_edge' if is_edge else 's_cat'

    det.append(ROW([MERGE(cat_style,'String',
        u'{0}  \u2014  {1:.2f} m\xb2'.format(tr(dc), round(dc_total, 2)),
        DET_COLS)], h=22))
    det.append(ROW([S('s_hdr','String', h) for h in DET_HDRS], h=20))

    for lv in sorted(lv_map.keys()):
        lv_data = sorted(lv_map[lv], key=lambda x: (x['type_name'], x['element_id']))
        det.append(ROW([MERGE('s_lv','String', u'\u25b8  ' + lv, DET_COLS)], h=18))
        for r in lv_data:
            seq += 1
            ev  = (seq % 2 == 0)
            ts  = 's_even'     if ev else 's_odd'
            tn  = 's_even_num' if ev else 's_odd_num'
            tid = 's_id_even'  if ev else 's_id'
            det.append(ROW([
                S(ts,  'Number', seq),
                S(ts,  'String', r['type_name']),
                S(ts,  'String', r.get('poz_no',   u'')),
                S(ts,  'String', r.get('poz_tanim', u'')),
                S(ts,  'String', lv),
                SN(tn, r['area_m2']),
                S(tid, 'Number', int(r['element_id'])),
            ], h=15))

    det.append(ROW([
        MERGE('s_subtotal_lbl','String', u'Ara Toplam \u2014 ' + tr(dc), DET_COLS - 2),
        SN('s_subtotal', dc_total),
        S('s_subtotal_lbl','String', u''),
    ], h=20))
    det.append(EROW(5))

det.append(ROW([
    MERGE('s_total_lbl','String', u'GENEL TOPLAM', DET_COLS - 2),
    SN('s_total', grand),
    S('s_total_lbl','String', u''),
], h=24))

ws_detay = (
    u'<Worksheet ss:Name="Detay"><Table ss:DefaultRowHeight="15">'
    u'<Column ss:Width="36"/>'   # No
    u'<Column ss:Width="180"/>'  # Tip/Aile
    u'<Column ss:Width="100"/>'  # Poz No
    u'<Column ss:Width="220"/>'  # Poz Aciklama
    u'<Column ss:Width="90"/>'   # Seviye
    u'<Column ss:Width="110"/>'  # Alan
    u'<Column ss:Width="82"/>\n' # Element Id
    + u'\n'.join(det)
    + u'\n</Table></Worksheet>'
)

# ============================================================
# Birlestir & kaydet
# ============================================================
parts = [
    u'<?xml version="1.0" encoding="UTF-8"?>',
    u'<?mso-application progid="Excel.Sheet"?>',
    u'<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"',
    u'  xmlns:o="urn:schemas-microsoft-com:office:office"',
    u'  xmlns:x="urn:schemas-microsoft-com:office:excel"',
    u'  xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">',
    STYLES, ws_ozet, ws_cross, ws_detay,
    u'</Workbook>',
]

try:
    with codecs.open(save_path, 'w', 'utf-8-sig') as f:
        f.write(u'\n'.join(parts))
except IOError as ex:
    msg = str(ex)
    if 'Errno 32' in msg or 'being used by another process' in msg:
        forms.alert(
            u'Excel dosyasini kapatin ve tekrar deneyin.\n\nAcik dosya:\n' + save_path,
            title=u'EG_KALIP'
        )
        raise SystemExit
    raise

forms.alert(
    u'Excel raporu olusturuldu!\n\n'
    u'Dosya: ' + save_path +
    u'\n\nToplam Alan : {0:.2f} m\xb2\n'
    u'Toplam Eleman: {1}\n'
    u'Kat Sayisi  : {2}\n'
    u'Poz Sayisi  : {3}'.format(grand, len(rows), len(cross), len(poz_ozet)),
    title=u'EG_KALIP'
)
