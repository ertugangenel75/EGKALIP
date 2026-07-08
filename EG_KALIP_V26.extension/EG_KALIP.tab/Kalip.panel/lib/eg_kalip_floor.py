# -*- coding: utf-8 -*-
"""
eg_kalip_floor.py  v23
Doseme kalip alani hesabi.

FORMUL:
  Net alt yuz = Revit.Area (gercek plan alani, arc dahil)
                - kolon izdüşümleri (union)
                - kiriş izdüşümleri (union)
                - tasiyici duvar izdüşümleri (union)

  Kenar kalibi = acik cevre uzunlugu x doseme kalinligi
    Acik cevre = kolon ve kirisler tarafindan kapanmayan kenarlar

NOT: Revit.Area arc/egri dosemede gercek alani verir — bbox fallback KULLANILMAZ.
"""
from eg_kalip_utils import (
    get_bbox, bbox_dims, overlap_1d,
    rect_intersection_xy, union_rectangles_area,
    xy_contact_or_overlap, point_in_bbox_xy,
    get_double, get_element_id_int, is_structural_wall, to_m2,
    curve_polyline_points, polyline_length_inside_bbox_xy,
    segment_midpoint, _union_intervals,
)
from eg_kalip_beam import beam_is_arc, beam_section, beam_curve_length

# ---------------------------------------------------------------------------
# Kenar kalıbı
# ---------------------------------------------------------------------------
def _floor_open_edge_length(floor, floor_bb, columns, beams, tol=0.15):
    """Dosemenin kolon/kiris tarafindan kapanmayan acik cevre uzunlugu (ft)."""
    if floor_bb is None: return 0.0

    x0,x1 = floor_bb.Min.X, floor_bb.Max.X
    y0,y1 = floor_bb.Min.Y, floor_bb.Max.Y
    z0,z1 = floor_bb.Min.Z, floor_bb.Max.Z

    edges = [
        ('S','Y', y0, x0, x1),
        ('N','Y', y1, x0, x1),
        ('W','X', x0, y0, y1),
        ('E','X', x1, y0, y1),
    ]
    total_open = 0.0

    for _en, fixed_ax, fixed_val, var_min, var_max in edges:
        edge_len = var_max - var_min
        if edge_len <= 1e-9: continue
        covered = []

        for group in (columns, beams):
            for el in group:
                bb = get_bbox(el)
                if bb is None: continue
                if bb.Max.Z < z0-tol or bb.Min.Z > z1+tol: continue

                _is_arc = False
                try: _is_arc = beam_is_arc(el)
                except Exception: pass

                if _is_arc:
                    b_el,_ = beam_section(el)
                    if b_el is None: b_el=0.3
                    cx=(bb.Min.X+bb.Max.X)/2.0; cy=(bb.Min.Y+bb.Max.Y)/2.0
                    hb=b_el/2.0
                    if fixed_ax=='Y':
                        if not (cy-hb<=fixed_val+tol and cy+hb>=fixed_val-tol): continue
                        iv0=max(cx-hb,var_min); iv1=min(cx+hb,var_max)
                    else:
                        if not (cx-hb<=fixed_val+tol and cx+hb>=fixed_val-tol): continue
                        iv0=max(cy-hb,var_min); iv1=min(cy+hb,var_max)
                else:
                    if fixed_ax=='Y':
                        if not (bb.Min.Y<=fixed_val+tol and bb.Max.Y>=fixed_val-tol): continue
                        iv0=max(bb.Min.X,var_min); iv1=min(bb.Max.X,var_max)
                    else:
                        if not (bb.Min.X<=fixed_val+tol and bb.Max.X>=fixed_val-tol): continue
                        iv0=max(bb.Min.Y,var_min); iv1=min(bb.Max.Y,var_max)

                if iv1 > iv0+1e-9:
                    covered.append((iv0,iv1))

        cov_len = _union_intervals(covered)
        total_open += max(0.0, edge_len - cov_len)

    # İc bosluk cevreleri (shaft vb.)
    try:
        total_perim = get_double(floor, ['Perimeter'])
        if total_perim and total_perim > 1e-9:
            dx=abs(x1-x0); dy=abs(y1-y0)
            outer = 2.0*(dx+dy)
            inner_void = max(0.0, total_perim - outer)
            total_open += inner_void
    except Exception:
        pass

    return total_open

# ---------------------------------------------------------------------------
# ANA HESAP: area_floor
# ---------------------------------------------------------------------------
def area_floor(floor, include_edges, columns, beams, walls, trace_log=None):
    """
    Doseme kalip alani.
    Doner: (net_ft2, method_str, a_alt_ft2, a_kenar_ft2)
    Her zaman 4 deger dondurur.
    """
    do_trace = trace_log is not None

    # Brüt alan — SADECE Revit.Area, bbox fallback YOK
    A_brut = get_double(floor, ['Area'])
    if A_brut is None or A_brut < 1e-9:
        return 0.0, 'floor_no_area', 0.0, 0.0

    floor_bb = get_bbox(floor)
    if floor_bb is None:
        return 0.0, 'floor_no_bbox', 0.0, 0.0

    if do_trace:
        trace_log.append(u'  A_brut={0:.4f}ft2={1:.4f}m2'.format(A_brut, to_m2(A_brut)))

    # ── Düşüm dikdörtgenleri (union) ─────────────────────────────
    deduct_rects = []
    _z_tol = 0.033  # ~10mm

    for col in columns:
        cbb = get_bbox(col)
        if cbb is None: continue
        # H4 FIX v24: Kolon ustu doseme altina (Min.Z) degmeli +-20mm
        if abs(cbb.Max.Z - floor_bb.Min.Z) > 0.066:
            continue
        rect = rect_intersection_xy(cbb, floor_bb)
        if rect:
            deduct_rects.append(rect)
            if do_trace:
                trace_log.append(u'  Kolon id={0} d={1:.4f}m2'.format(
                    get_element_id_int(col),
                    to_m2((rect[1]-rect[0])*(rect[3]-rect[2]))))

    for bm in beams:
        bbb = get_bbox(bm)
        if bbb is None: continue
        # H3 FIX v24: Z kontrolu - kirisin ustu doseme ustuyle esit olmali
        # +-20mm tolerans (0.066ft). Boylece alt katta kalan kirisler
        # ust kattaki dosemelere yanlis dusulmez.
        if abs(bbb.Max.Z - floor_bb.Max.Z) > 0.066:
            continue
        if beam_is_arc(bm):
            b_arc,_ = beam_section(bm)
            if b_arc and b_arc > 1e-9:
                # H5 FIX v24: ov_len kirisin gercek uzunlugundan buyuk olamaz
                pts = curve_polyline_points(bm)
                ov_len = polyline_length_inside_bbox_xy(pts, floor_bb)
                beam_L = beam_curve_length(bm) or 0.0
                if ov_len <= 1e-9:
                    ov_len = beam_L
                # Gercek uzunlukla sinirla - double counting onle
                ov_len = min(ov_len, beam_L)
                if ov_len > 1e-9:
                    d = b_arc * ov_len
                    deduct_rects.append(('arc_area', d))
                    if do_trace:
                        trace_log.append(u'  ArcKiris id={0} b={1:.3f}ft L={2:.3f}ft d={3:.4f}m2'.format(
                            get_element_id_int(bm), b_arc, ov_len, to_m2(d)))
        else:
            rect = rect_intersection_xy(bbb, floor_bb)
            if rect:
                deduct_rects.append(rect)
                if do_trace:
                    trace_log.append(u'  Kiris id={0} d={1:.4f}m2'.format(
                        get_element_id_int(bm),
                        to_m2((rect[1]-rect[0])*(rect[3]-rect[2]))))

    for wall in walls:
        if not is_structural_wall(wall): continue
        wbb = get_bbox(wall)
        if wbb is None: continue
        if not (wbb.Max.Z >= floor_bb.Min.Z - _z_tol and
                wbb.Min.Z < floor_bb.Max.Z + _z_tol): continue
        rect = rect_intersection_xy(wbb, floor_bb)
        if rect:
            deduct_rects.append(rect)
            if do_trace:
                trace_log.append(u'  Duvar id={0} d={1:.4f}m2'.format(
                    get_element_id_int(wall),
                    to_m2((rect[1]-rect[0])*(rect[3]-rect[2]))))

    deduct_total = union_rectangles_area(deduct_rects)
    # Güvenlik: kesintilerin toplamı brüt alanı geçemez
    deduct_total = min(deduct_total, A_brut * 0.95)
    a_alt = max(0.0, A_brut - deduct_total)

    if do_trace:
        trace_log.append(u'  deduct_total={0:.4f}ft2={1:.4f}m2'.format(
            deduct_total, to_m2(deduct_total)))
        trace_log.append(u'  a_alt={0:.4f}ft2={1:.4f}m2'.format(a_alt, to_m2(a_alt)))

    # ── Kenar kalıbı ─────────────────────────────────────────────
    a_kenar = 0.0
    if include_edges:
        T = get_double(floor, ['Thickness', 'Default Thickness'])
        if T and T > 1e-9:
            open_L = _floor_open_edge_length(floor, floor_bb, columns, beams)
            a_kenar = max(0.0, open_L * T)
            if a_kenar < 0.001: a_kenar = 0.0
            if do_trace:
                trace_log.append(u'  AcikKenar={0:.4f}ft T={1:.4f}ft kenar={2:.4f}ft2={3:.4f}m2'.format(
                    open_L, T, a_kenar, to_m2(a_kenar)))

    method = 'floor_v23_edge' if a_kenar > 1e-9 else 'floor_v23'
    return a_alt + a_kenar, method, a_alt, a_kenar
