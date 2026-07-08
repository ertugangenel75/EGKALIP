# -*- coding: utf-8 -*-
"""
eg_kalip_beam.py  v26
Kiriş kalıp alanı hesabı.

FORMUL:
  Düz kiriş:
    gross = L × b  (alt yüz)
            + L × h_sol  (sol yan yüz)
            + L × h_sag  (sağ yan yüz)

    h_sol = h - slab_t  → iç yüz (sol tarafta döşeme var)
    h_sol = h + slab_t  → dış yüz (sol tarafta döşeme YOK)
    (aynı kural sağ yüz için)

  Arc kiriş:
    Alt yüz + yan yüzler → Face.Area (Revit API, gerçek curved alan)
    Yan yüz düşüm/ekleme: slab_t bazlı, embed_len oranında

DÜŞÜM KURALLARI:
  1. Alt destek (kolon/duvar): xy_overlap_area düşülür
  2. Kiriş-kiriş:
     - SADECE ANA kiriş (uzun yüz, sekonder saplanan) kesinti uygular
     - Düşüm = b_sekonder × (h_sekonder - slab_t)
"""
from Autodesk.Revit.DB import Options, Solid, UV
try:
    from Autodesk.Revit.DB import ViewDetailLevel as _VDL
    _VDL_FINE = _VDL.Fine
except Exception:
    _VDL_FINE = None

from eg_kalip_utils import (
    get_bbox, bbox_dims, overlap_1d, xy_overlap_area,
    xy_contact_or_overlap, bbox_overlaps_3d,
    get_double, get_string, get_element_id_int,
    is_structural_wall, is_wall, to_m2,
    curve_polyline_points, polyline_length_inside_bbox_xy,
    segment_midpoint, segment_length_3d, point_segment_distance_xy,
)

# ---------------------------------------------------------------------------
# Kiriş geometri yardımcıları
# ---------------------------------------------------------------------------
def beam_is_arc(el):
    try:
        from Autodesk.Revit.DB import Arc, NurbSpline, HermiteSpline
        c = el.Location.Curve
        return isinstance(c, (Arc, NurbSpline, HermiteSpline))
    except Exception:
        return False

def beam_curve_length(el):
    try:
        return el.Location.Curve.Length
    except Exception:
        pass
    pts = curve_polyline_points(el)
    if pts and len(pts) >= 2:
        return sum(segment_length_3d(pts[i], pts[i+1]) for i in range(len(pts)-1))
    dx, dy, dz = bbox_dims(el)
    return max(dx, dy) if dx is not None else None

def beam_axis_is_x(el):
    try:
        c = el.Location.Curve
        p0, p1 = c.GetEndPoint(0), c.GetEndPoint(1)
        return abs(p1.X - p0.X) >= abs(p1.Y - p0.Y)
    except Exception:
        dx, dy, _ = bbox_dims(el)
        if dx is None: return True
        return dx >= dy

def beam_section(el):
    """(b, h): kesit genislik ve yukseklik ic birim (ft)."""
    dx, dy, dz = bbox_dims(el)
    if dx is None: return (None, None)
    h = dz
    if h is None or h <= 1e-9: return (None, None)
    if beam_is_arc(el):
        L = beam_curve_length(el)
        vol = get_double(el, ['Volume', 'Hacim'])
        if vol is None or vol <= 1e-9:
            try:
                from Autodesk.Revit.DB import BuiltInParameter
                p = el.get_Parameter(BuiltInParameter.HOST_VOLUME_COMPUTED)
                if p and p.HasValue: vol = p.AsDouble()
            except Exception: pass
        if vol and L and L > 1e-9:
            b = vol / (L * h)
            if b > 1e-4: return (b, h)
        b = min(dx, dy)
        if b > 4.0 * h: b = h
        return (b, h)
    if beam_axis_is_x(el):
        return (dy, h)
    else:
        return (dx, h)

def beam_net_length(el):
    cl = beam_curve_length(el)
    if cl and cl > 1e-9: return cl
    dx, dy, dz = bbox_dims(el)
    if dx is None: return None
    return max(dx, dy)

# ---------------------------------------------------------------------------
# v26: Arc kiriş gercek yuzey alani (Face.Area)
# ---------------------------------------------------------------------------
def _get_arc_beam_face_areas(beam):
    """
    Arc kirisin gercek yuzey alanlarini Face.Area ile hesapla.
    Doner: (bottom_ft2, sides_ft2) veya (None, None).
    """
    try:
        opt = Options()
        opt.ComputeReferences = False
        if _VDL_FINE is not None:
            opt.DetailLevel = _VDL_FINE
        else:
            opt.DetailLevel = 3
        geom = beam.get_Geometry(opt)
        if not geom:
            return None, None
        bottom = 0.0
        sides  = 0.0
        for obj in geom:
            if not isinstance(obj, Solid): continue
            if obj.Volume <= 1e-9: continue
            for face in obj.Faces:
                try:
                    fbb = face.GetBoundingBox()
                    mu  = (fbb.Min.U + fbb.Max.U) * 0.5
                    mv  = (fbb.Min.V + fbb.Max.V) * 0.5
                    nrm = face.ComputeNormal(UV(mu, mv))
                    if abs(nrm.Z) > 0.7:
                        if nrm.Z < 0: bottom += face.Area
                    else:
                        sides += face.Area
                except Exception:
                    continue
        if bottom <= 1e-9 and sides <= 1e-9:
            return None, None
        return bottom, sides
    except Exception:
        return None, None

# ---------------------------------------------------------------------------
# v26: Yan yuz doseme tespiti
# ---------------------------------------------------------------------------
def _floor_side_count(beam_bb, floor_bb, axis_is_x, tol=0.05):
    """Kacta bir yan yuz doseme icinde/sinirinda."""
    if beam_bb is None or floor_bb is None: return 0
    if axis_is_x:
        s = 1 if (floor_bb.Min.Y < beam_bb.Min.Y - tol or
                  abs(floor_bb.Min.Y - beam_bb.Min.Y) <= tol) else 0
        n = 1 if (floor_bb.Max.Y > beam_bb.Max.Y + tol or
                  abs(floor_bb.Max.Y - beam_bb.Max.Y) <= tol) else 0
        return s + n
    else:
        w = 1 if (floor_bb.Min.X < beam_bb.Min.X - tol or
                  abs(floor_bb.Min.X - beam_bb.Min.X) <= tol) else 0
        e = 1 if (floor_bb.Max.X > beam_bb.Max.X + tol or
                  abs(floor_bb.Max.X - beam_bb.Max.X) <= tol) else 0
        return w + e

def _floor_side_flags(beam_bb, floor_bb, axis_is_x, tol=0.08):
    """
    (left_covered, right_covered)
    X-kiris: left=guney(MinY), right=kuzey(MaxY)
    Y-kiris: left=bati(MinX),  right=dogu(MaxX)
    """
    if beam_bb is None or floor_bb is None: return False, False
    if axis_is_x:
        left  = (floor_bb.Min.Y <= beam_bb.Min.Y + tol)
        right = (floor_bb.Max.Y >= beam_bb.Max.Y - tol)
    else:
        left  = (floor_bb.Min.X <= beam_bb.Min.X + tol)
        right = (floor_bb.Max.X >= beam_bb.Max.X - tol)
    return left, right

def _beam_embed_len_in_floor(beam, floor_bb):
    """Kirisin doseme icinde kalan eksen uzunlugu."""
    beam_bb = get_bbox(beam)
    if beam_bb is None or floor_bb is None: return 0.0
    dx = abs(beam_bb.Max.X - beam_bb.Min.X)
    dy = abs(beam_bb.Max.Y - beam_bb.Min.Y)
    if beam_is_arc(beam):
        pts = curve_polyline_points(beam)
        inside = polyline_length_inside_bbox_xy(pts, floor_bb)
        if inside > 1e-9: return inside
        cl = beam_curve_length(beam)
        return (cl or max(dx, dy)) if xy_contact_or_overlap(beam_bb, floor_bb) else 0.0
    if dx >= dy:
        return max(0.0, overlap_1d(beam_bb.Min.X, beam_bb.Max.X,
                                    floor_bb.Min.X, floor_bb.Max.X))
    else:
        return max(0.0, overlap_1d(beam_bb.Min.Y, beam_bb.Max.Y,
                                    floor_bb.Min.Y, floor_bb.Max.Y))

# ---------------------------------------------------------------------------
# v26: Dis yuz tespiti ve slab_t ekleme
# ---------------------------------------------------------------------------
def _external_face_addition(beam, floors, axis_is_x):
    """
    Kirisin dis yan yuzleri icin slab_t eklemesi.
    Her dis yuz (karsisinda doseme olmayan) icin: L x slab_t EKLENIR.
    Doner: (addition_ft2, ext_left, ext_right, slab_t_used)
    """
    beam_bb = get_bbox(beam)
    if beam_bb is None: return 0.0, False, False, 0.0

    left_covered  = False
    right_covered = False
    slab_t        = 0.0

    for floor in floors:
        fbb = get_bbox(floor)
        if fbb is None: continue
        z_ov = overlap_1d(beam_bb.Min.Z, beam_bb.Max.Z, fbb.Min.Z, fbb.Max.Z)
        if z_ov <= 1e-9: continue
        if not xy_contact_or_overlap(beam_bb, fbb, tol=0.15): continue
        ft = get_double(floor, ['Thickness', 'Default Thickness']) or 0.0
        if ft > slab_t: slab_t = ft
        lc, rc = _floor_side_flags(beam_bb, fbb, axis_is_x)
        if lc: left_covered  = True
        if rc: right_covered = True

    ext_left  = not left_covered
    ext_right = not right_covered
    if slab_t <= 1e-9: return 0.0, ext_left, ext_right, 0.0
    L = beam_net_length(beam)
    if not L or L <= 1e-9: return 0.0, ext_left, ext_right, 0.0
    addition = 0.0
    if ext_left:  addition += L * slab_t
    if ext_right: addition += L * slab_t
    return addition, ext_left, ext_right, slab_t

# ---------------------------------------------------------------------------
# Kiriş eksenine yakın nokta
# ---------------------------------------------------------------------------
def point_near_beam_xy(pt, beam, own_b=None, tol=0.03):
    pts = curve_polyline_points(beam, dense=True)
    if not pts or len(pts) < 2:
        bb = get_bbox(beam)
        if bb is None: return False
        from eg_kalip_utils import point_in_bbox_xy
        return point_in_bbox_xy(pt, bb, tol=max(tol, (own_b or 0.0) * 0.5))
    if own_b is None or own_b <= 1e-9:
        own_b, _ = beam_section(beam)
        if own_b is None: own_b = 0.0
    limit = own_b * 0.5 + tol
    for i in range(len(pts) - 1):
        if point_segment_distance_xy(pt, pts[i], pts[i+1]) <= limit:
            return True
    return False

# ---------------------------------------------------------------------------
# v26: Kiris-kiris dusumu — duzeltilmis formul
# ---------------------------------------------------------------------------
def _beam_beam_deduct(beam, all_beams, floors):
    """
    Kiris-kiris birlesimdusumu v26.

    KURAL:
      - Sadece ANA kiris kesinti uygular.
      - Sekonder tespit: other'in endpoint'i self eksenine yakin
        ama self'in kendi endpoint'lerine uzak (T-junction).
      - Dusumu formullu: b_sekonder x (h_sekonder - slab_t).
    """
    beam_bb = get_bbox(beam)
    if beam_bb is None: return 0.0, []
    b_self, h_self = beam_section(beam)
    if b_self is None or h_self is None: return 0.0, []
    self_pts = curve_polyline_points(beam, dense=True)
    if not self_pts or len(self_pts) < 2: return 0.0, []

    slab_t = 0.0
    for fl in floors:
        ft = get_double(fl, ['Thickness', 'Default Thickness']) or 0.0
        if ft > slab_t: slab_t = ft

    self_id = get_element_id_int(beam)
    self_p0 = self_pts[0]
    self_pN = self_pts[-1]
    total   = 0.0
    trace   = []

    for other in all_beams:
        other_id = get_element_id_int(other)
        if other_id == self_id: continue
        obb = get_bbox(other)
        if obb is None: continue

        z_ov = overlap_1d(beam_bb.Min.Z, beam_bb.Max.Z, obb.Min.Z, obb.Max.Z)
        if z_ov <= 0.05: continue
        if not xy_contact_or_overlap(beam_bb, obb, tol=0.15): continue

        b_other, h_other = beam_section(other)
        if b_other is None or b_other <= 1e-9: continue

        other_pts = curve_polyline_points(other, dense=False)
        if not other_pts or len(other_pts) < 2: continue

        # T-junction: other endpoint'i self eksenine yakin ama self uclarindan uzak
        is_ana = False
        for ep in [other_pts[0], other_pts[-1]]:
            if not point_near_beam_xy(ep, beam, own_b=b_self,
                                      tol=b_self * 0.5 + 0.05):
                continue
            d0 = segment_length_3d(ep, self_p0)
            dN = segment_length_3d(ep, self_pN)
            if d0 > b_self * 0.5 + 0.05 and dN > b_self * 0.5 + 0.05:
                # Ek kontrol: self endpoint de other eksenine yakinsa
                # self de sekonder demektir (L-junction) -> skip
                self_near_other = (
                    point_near_beam_xy(self_p0, other, own_b=b_other,
                                       tol=b_other * 0.5 + 0.05) or
                    point_near_beam_xy(self_pN, other, own_b=b_other,
                                       tol=b_other * 0.5 + 0.05)
                )
                if not self_near_other:
                    is_ana = True
                break

        if not is_ana: continue

        h_net  = max(0.0, h_other - slab_t)
        deduct = b_other * h_net
        if deduct <= 1e-9: continue

        total += deduct
        trace.append(
            u'sekonder_id={0} b={1:.3f}ft h_net={2:.3f}ft '
            u'slab_t={3:.3f}ft deduct={4:.4f}ft2={5:.4f}m2'.format(
                other_id, b_other, h_net, slab_t, deduct, to_m2(deduct)))

    return total, trace

# ---------------------------------------------------------------------------
# ANA HESAP: area_beam  v26
# ---------------------------------------------------------------------------
def area_beam(beam, floors, walls, columns, all_beams, trace_log=None):
    """
    Kiris kalip alani.
    Doner: (net_ft2, method_str)
    """
    do_trace = trace_log is not None
    is_arc   = beam_is_arc(beam)
    L        = beam_net_length(beam)
    b, h     = beam_section(beam)

    if L is None or b is None or h is None or L < 1e-9 or b < 1e-9 or h < 1e-9:
        return 0.0, 'beam_no_dims'

    beam_bb   = get_bbox(beam)
    axis_is_x = beam_axis_is_x(beam)

    # BRUT ALAN
    if is_arc:
        bottom_face, sides_face = _get_arc_beam_face_areas(beam)
        if bottom_face is not None and sides_face is not None:
            gross       = bottom_face + sides_face
            method_base = 'arc_face_area'
        else:
            gross       = L * (b + 2.0 * h)
            method_base = 'arc_bbox_fallback'
    else:
        gross       = L * (b + 2.0 * h)
        method_base = 'beam_v26'

    if do_trace:
        trace_log.append(u'  is_arc={0} method={1}'.format(is_arc, method_base))
        trace_log.append(u'  L={0:.3f}m b={1:.3f}m h={2:.3f}m'.format(
            L*0.3048, b*0.3048, h*0.3048))
        trace_log.append(u'  Brut={0:.4f}m2'.format(to_m2(gross)))

    # 1. DOSEME YAN DUSUMU (ic yuzler)
    yan_deduct = 0.0
    for floor in floors:
        floor_bb = get_bbox(floor)
        if floor_bb is None or beam_bb is None: continue
        if not xy_contact_or_overlap(beam_bb, floor_bb, tol=0.05): continue
        floor_t = get_double(floor, ['Thickness', 'Default Thickness'])
        if not floor_t or floor_t <= 1e-9: continue
        z_ov = overlap_1d(beam_bb.Min.Z, beam_bb.Max.Z, floor_bb.Min.Z, floor_bb.Max.Z)
        if abs(beam_bb.Max.Z - floor_bb.Max.Z) <= 0.20:
            z_ov = min(z_ov if z_ov > 1e-9 else floor_t, floor_t)
        if z_ov <= 1e-9: continue
        side_cnt  = _floor_side_count(beam_bb, floor_bb, axis_is_x)
        if side_cnt <= 0: continue
        embed_len = _beam_embed_len_in_floor(beam, floor_bb)
        if embed_len <= 1e-9: continue
        d = side_cnt * embed_len * z_ov
        yan_deduct += d
        if do_trace:
            trace_log.append(
                u'  DosemeYan: sides={0} L={1:.3f}ft z={2:.3f}ft d={3:.4f}m2'.format(
                    side_cnt, embed_len, z_ov, to_m2(d)))

    # 2. DIS YUZ — ekleme yok
    # Dis yuzde tam h alinir (ne dusum ne ekleme).
    # Ic yuz: h - slab_t (yan_deduct ile zaten dusuldu).
    ext_add = 0.0

    # 3. ALT DESTEK DUSUMU (kolon/duvar)
    alt_deduct = 0.0
    if beam_bb is not None:
        for support in list(walls) + list(columns):
            if is_wall(support) and not is_structural_wall(support):
                continue
            sbb = get_bbox(support)
            if sbb is None: continue
            ov = xy_overlap_area(sbb, beam_bb)
            if ov <= 1e-9: continue
            if abs(sbb.Max.Z - beam_bb.Min.Z) > 0.066: continue
            alt_deduct += ov
            if do_trace:
                trace_log.append(
                    u'  AltDestek: id={0} ov={1:.4f}m2'.format(
                        get_element_id_int(support), to_m2(ov)))

    # 4. KIRIS-KIRIS DUSUMU
    kk_deduct = 0.0
    if all_beams:
        kk_deduct, kk_trace = _beam_beam_deduct(beam, all_beams, floors)
        if do_trace:
            for t in kk_trace:
                trace_log.append(u'  KirisKiris: ' + t)

    net = max(0.0, gross - yan_deduct + ext_add - alt_deduct - kk_deduct)

    if do_trace:
        trace_log.append(
            u'  yan={0:.4f} ext={1:.4f} alt={2:.4f} kk={3:.4f}'.format(
                to_m2(yan_deduct), to_m2(ext_add),
                to_m2(alt_deduct), to_m2(kk_deduct)))
        trace_log.append(u'  NET={0:.4f}m2'.format(to_m2(net)))

    return net, method_base
