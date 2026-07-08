# -*- coding: utf-8 -*-
"""
eg_kalip_wall.py  v23
Tasiyici duvar kalip alani hesabi.

FORMUL:
  Brut = 2 x L x H
  Net  = Brut - kiris birlesimleri - kolon birlesimleri
"""
from eg_kalip_utils import (
    get_bbox, bbox_dims, bbox_overlaps_3d,
    get_double, get_string, get_element_id_int,
    is_structural_wall, to_m2,
)
from eg_kalip_beam import beam_section
from eg_kalip_column import column_section

def wall_length(wall):
    try:
        return wall.Location.Curve.Length
    except Exception:
        dx, dy, dz = bbox_dims(wall)
        if dx and dy: return max(dx, dy)
    return None

def wall_thickness(wall):
    t = get_double(wall, ["Width","Thickness","Wall Thickness","Kalinlik"])
    if t and t > 1e-9: return t
    dx, dy, dz = bbox_dims(wall)
    if dx and dy: return min(dx, dy)
    return None

def area_wall(wall, beams, columns, trace_log=None):
    """Doner: (net_ft2, method_str)"""
    do_trace = trace_log is not None

    if not is_structural_wall(wall):
        return 0.0, 'wall_skip_nonstructural'

    L = wall_length(wall)
    dx, dy, dz = bbox_dims(wall)
    if L is None or dz is None or L < 1e-9 or dz < 1e-9:
        return 0.0, 'wall_no_dims'

    gross = 2.0 * L * dz
    wbb = get_bbox(wall)

    if do_trace:
        trace_log.append(u'  L={0:.3f}m H={1:.3f}m Brut={2:.4f}m2'.format(
            L*0.3048, dz*0.3048, to_m2(gross)))

    beam_d = 0.0
    for beam in beams:
        bbb = get_bbox(beam)
        if bbb is None or wbb is None: continue
        if not bbox_overlaps_3d(wbb, bbb, tol=0.1): continue
        b, h = beam_section(beam)
        if b and h:
            beam_d += b * h
            if do_trace:
                trace_log.append(u'  KirisD: id={0} d={1:.4f}m2'.format(
                    get_element_id_int(beam), to_m2(b*h)))

    col_d = 0.0
    for col in columns:
        cbb = get_bbox(col)
        if cbb is None or wbb is None: continue
        if not bbox_overlaps_3d(wbb, cbb, tol=0.1): continue
        cb, ch, _ = column_section(col)
        if cb and ch:
            col_d += min(cb,ch)*max(cb,ch)

    net = max(0.0, gross - beam_d - col_d)
    if do_trace:
        trace_log.append(u'  beam_d={0:.4f} col_d={1:.4f} NET={2:.4f}m2'.format(
            to_m2(beam_d), to_m2(col_d), to_m2(net)))

    return net, 'wall_v23'
