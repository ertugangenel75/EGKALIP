# -*- coding: utf-8 -*-
"""
eg_kalip_report.py  v25
HTML rapor uretici.
A: Kullanici ozet tablosu
B: Teknik detay (her eleman icin tam iz)
"""
import os, io, datetime

CAT_TR = {
    'Structural Columns':     u'Kolon',
    'Structural Framing':     u'Kiris',
    'Walls':                  u'Duvar',
    'Floors':                 u'Doseme',
    'Floors_Edge':            u'Doseme Kenar',
    'Structural Foundations': u'Temel',
}

def _esc(s):
    if s is None: return u''
    return (u'{0}'.format(s)
            .replace(u'&', u'&amp;')
            .replace(u'<', u'&lt;')
            .replace(u'>', u'&gt;')
            .replace(u'"', u'&quot;'))

def build_html(rows, totals, grand, debug_traces, project_name=u''):
    """
    rows: calculate() ciktisi
    debug_traces: dict {element_id: [trace_line, ...]}
    Doner: HTML string (unicode)
    """
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

    # Toplam satiri
    summary_rows = u''
    for cat, val in sorted(totals.items()):
        summary_rows += u'<tr><td>{0}</td><td class="num">{1:.2f}</td></tr>\n'.format(
            _esc(CAT_TR.get(cat, cat)), val)
    summary_rows += u'<tr class="grand"><td>TOPLAM</td><td class="num">{0:.2f}</td></tr>\n'.format(grand)

    # Detay satirlari
    detail_rows = u''
    for r in rows:
        eid   = _esc(r.get('element_id', ''))
        cat   = _esc(CAT_TR.get(r.get('category',''), r.get('category','')))
        typ   = _esc(r.get('type_name', ''))
        lvl   = _esc(r.get('level', ''))
        am2   = r.get('area_m2', 0.0)
        meth  = _esc(r.get('method', ''))
        pno   = _esc(r.get('poz_no', ''))
        ptanim= _esc(r.get('poz_tanim', ''))
        pfiyat= r.get('poz_fiyat', 0.0)
        tutar = am2 * pfiyat

        # Teknik trace
        trace_lines = debug_traces.get(r.get('element_id',''), [])
        trace_html = u''
        if trace_lines:
            trace_html = u'<div class="trace"><pre>{0}</pre></div>'.format(
                u'\n'.join(_esc(t) for t in trace_lines))

        detail_rows += u'''
<tr>
  <td class="eid">{eid}</td>
  <td>{cat}</td>
  <td>{typ}</td>
  <td>{lvl}</td>
  <td class="num">{am2:.4f}</td>
  <td class="num">{tutar:.2f}</td>
  <td class="meth">{meth}</td>
  <td>{pno}</td>
  <td class="btn-col">
    <button onclick="tog('{eid}')">Detay</button>
  </td>
</tr>
<tr id="tr_{eid}" style="display:none">
  <td colspan="9">{trace}</td>
</tr>
'''.format(eid=eid, cat=cat, typ=typ, lvl=lvl,
           am2=am2, tutar=tutar, meth=meth,
           pno=pno, trace=trace_html)

    html = u'''<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8">
<title>EG_KALIP v25 Raporu</title>
<style>
  body {{ font-family: Segoe UI, Arial, sans-serif; font-size: 13px;
          background:#f5f5f5; margin:0; padding:16px; }}
  h1   {{ font-size:18px; color:#1a3a5c; margin-bottom:4px; }}
  .meta{{ color:#666; font-size:11px; margin-bottom:16px; }}
  /* OZET */
  .summary {{ display:inline-block; background:#fff; border:1px solid #ddd;
               border-radius:6px; padding:12px 20px; margin-bottom:20px; }}
  .summary table {{ border-collapse:collapse; }}
  .summary td {{ padding:3px 12px; }}
  .summary .num {{ text-align:right; font-weight:600; }}
  .summary .grand {{ background:#1a3a5c; color:#fff; }}
  /* DETAY */
  table.detail {{ width:100%; border-collapse:collapse; background:#fff;
                  border:1px solid #ddd; border-radius:6px; overflow:hidden; }}
  table.detail th {{ background:#1a3a5c; color:#fff; padding:6px 8px;
                     text-align:left; font-size:12px; }}
  table.detail td {{ padding:5px 8px; border-bottom:1px solid #eee;
                     vertical-align:top; }}
  table.detail tr:hover > td {{ background:#f0f6ff; }}
  .num  {{ text-align:right; font-family:monospace; }}
  .meth {{ font-size:10px; color:#888; font-family:monospace; }}
  .eid  {{ font-size:11px; color:#aaa; font-family:monospace; }}
  .btn-col button {{ font-size:11px; padding:2px 8px; cursor:pointer;
                     border:1px solid #1a3a5c; border-radius:3px;
                     background:#fff; color:#1a3a5c; }}
  .btn-col button:hover {{ background:#1a3a5c; color:#fff; }}
  .trace {{ background:#1e1e1e; border-radius:4px; padding:10px; margin:4px 0; }}
  .trace pre {{ color:#d4d4d4; font-size:11px; margin:0; white-space:pre-wrap; }}
</style>
<script>
function tog(id) {{
  var r = document.getElementById('tr_' + id);
  r.style.display = (r.style.display === 'none') ? 'table-row' : 'none';
}}
function togAll(show) {{
  var rows = document.querySelectorAll('tr[id^="tr_"]');
  for(var i=0;i<rows.length;i++) rows[i].style.display = show?'table-row':'none';
}}
</script>
</head>
<body>
<h1>EG_KALIP v25 &mdash; Kalip Metraj Raporu</h1>
<div class="meta">Proje: {prj} &nbsp;|&nbsp; Tarih: {now}</div>

<div class="summary">
  <table>{summary}</table>
</div>
<br>
<p style="margin-bottom:6px">
  <button onclick="togAll(true)">Tum Detaylari Ac</button>
  <button onclick="togAll(false)">Tum Detaylari Kapat</button>
</p>
<table class="detail">
<thead>
<tr>
  <th>ID</th><th>Kategori</th><th>Tip</th><th>Kat</th>
  <th>Alan (m²)</th><th>Tutar (TL)</th><th>Yontem</th><th>Poz</th><th></th>
</tr>
</thead>
<tbody>
{detail}
</tbody>
</table>
</body>
</html>'''.format(
        prj=_esc(project_name),
        now=now,
        summary=summary_rows,
        detail=detail_rows,
    )
    return html


def save_report(rows, totals, grand, debug_traces, project_name=u'', out_dir=None):
    """HTML dosyasini yaz, path dondur."""
    import tempfile
    if out_dir is None:
        out_dir = tempfile.gettempdir()
    fname = u'egkalip_rapor_{0}.html'.format(
        datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    path = os.path.join(out_dir, fname)
    html = build_html(rows, totals, grand, debug_traces, project_name)
    with io.open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    return path
