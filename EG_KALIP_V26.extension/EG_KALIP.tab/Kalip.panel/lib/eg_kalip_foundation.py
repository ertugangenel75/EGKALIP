# -*- coding: utf-8 -*-
"""
eg_kalip_foundation.py  v23
Temel kalip alani hesabi.

FORMUL:
  Yan alan = 2 x (b1+b2) x H
  Net = Yan alan - perde/duvar birlesim dusumu
"""
from eg_kalip_utils import (
    get_bbox, bbox_dims, overlap_1d, bbox_overlaps_3d,
    get_double, get_element_id_int,
    is_structural_wall, to_m2,
)
from eg_kalip_wall import wall_thickness

def area_foundation(foot, walls, trace_log=None):
    """Doner: (net_ft2, method_str)"""
    do_trace = trace_log is not None

    dx, dy, dz = bbox_dims(foot)
    if dx is None: return 0.0, 'found_no_dims'

    H = get_double(foot, [
        'Foundation Depth','Depth','Height','Structural Foundation Height',
        'Overall Height','Thickness','Foundation Thickness',
        'Temel Derinligi','Derinlik','Yukseklik',
    ])
    raw = sorted([dx, dy, dz if dz else 0.0])
    b1, b2 = raw[2], raw[1]
    h_bbox = raw[0]

    if H and H > 1e-9:
        height = H; method_h = 'param'
    elif h_bbox > 1e-9:
        height = h_bbox; method_h = 'bbox_min'
    else:
        return 0.0, 'found_no_height'

    gross = 2.0 * (b1+b2) * height
    foot_bb = get_bbox(foot)

    if do_trace:
        trace_log.append(u'  b1={0:.3f}m b2={1:.3f}m H={2:.3f}m Brut={3:.4f}m2'.format(
            b1*0.3048, b2*0.3048, height*0.3048, to_m2(gross)))

    wall_d = 0.0
    for wall in walls:
        if not is_structural_wall(wall): continue
        wbb = get_bbox(wall)
        if wbb is None or foot_bb is None: continue
        if not bbox_overlaps_3d(foot_bb, wbb, tol=0.1): continue
        t = wall_thickness(wall)
        zov = overlap_1d(foot_bb.Min.Z, foot_bb.Max.Z, wbb.Min.Z, wbb.Max.Z)
        if t and zov > 1e-9:
            wall_d += t * zov

    net = max(0.0, gross - wall_d)
    if do_trace:
        trace_log.append(u'  wall_d={0:.4f} NET={1:.4f}m2'.format(
            to_m2(wall_d), to_m2(net)))

    return net, 'found_v23_' + method_h
