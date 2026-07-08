# -*- coding: utf-8 -*-
"""
eg_kalip_column.py  v26
Kolon kalip alani hesabi.

FORMUL:
  Ana govde = (cevre - duvar_temas) x H_govde
    H_govde = kolon alt kotu -> kiriş alt kotu (veya doseme alt)
    duvar_temas: tasiyici duvar kolon yan yuzune temas ediyorsa dusulur

  Kolon basi (kiriş varsa):
    Her yuz (N/S/E/W): brut - kiris dusumu - doseme dusumu
    brut_yuz   = dim x head_h
    kiris_d    = b_kiris x head_h        (kirisin kapattigi dikey serit)
    doseme_d   = floor_t x (dim-b_kiris) (dosemenin kapattigi yatay serit)
"""
from eg_kalip_utils import (
    get_bbox, bbox_dims, overlap_1d,
    xy_contact_or_overlap, xy_overlap_area, bbox_overlaps_3d,
    get_element_id_int, is_structural_wall, to_m2,
)

# ---------------------------------------------------------------------------
# Yardimcilar
# ---------------------------------------------------------------------------
def column_section(el):
    dx, dy, dz = bbox_dims(el)
    if dx is None: return (None, None, None)
    return (dx, dy, dz)

def _find_support_z(col_bb, beams, floors, tol=0.15):
    """
    Kolonun ana govdesinin ust siniri.
    Once kirislerin en dusuk alt kotu, yoksa dosemelerin alt kotu, yoksa kolon ustu.
    Doner: (z_ft, has_beam)
    """
    if col_bb is None: return None, False
    z_beam = []
    for beam in beams:
        bbb = get_bbox(beam)
        if bbb is None: continue
        if not xy_contact_or_overlap(col_bb, bbb, tol=tol): continue
        zb = bbb.Min.Z
        if col_bb.Min.Z - tol <= zb <= col_bb.Max.Z + tol:
            z_beam.append(zb)
    if z_beam:
        return min(z_beam), True
    z_floor = []
    for floor in floors:
        fbb = get_bbox(floor)
        if fbb is None: continue
        if not xy_contact_or_overlap(col_bb, fbb, tol=tol): continue
        zb = fbb.Min.Z
        if col_bb.Min.Z - tol <= zb <= col_bb.Max.Z + tol:
            z_floor.append(zb)
    if z_floor:
        return min(z_floor), False
    return col_bb.Max.Z, False

def _face_covered_by_beam(face, col_bb, beam_bb, z0, z1, tol=0.05):
    if col_bb is None or beam_bb is None: return False
    if overlap_1d(beam_bb.Min.Z, beam_bb.Max.Z, z0, z1) <= 1e-9: return False
    if face == 'W':
        return (abs(beam_bb.Max.X - col_bb.Min.X) <= tol and
                overlap_1d(beam_bb.Min.Y, beam_bb.Max.Y, col_bb.Min.Y, col_bb.Max.Y) > 1e-9)
    if face == 'E':
        return (abs(beam_bb.Min.X - col_bb.Max.X) <= tol and
                overlap_1d(beam_bb.Min.Y, beam_bb.Max.Y, col_bb.Min.Y, col_bb.Max.Y) > 1e-9)
    if face == 'S':
        return (abs(beam_bb.Max.Y - col_bb.Min.Y) <= tol and
                overlap_1d(beam_bb.Min.X, beam_bb.Max.X, col_bb.Min.X, col_bb.Max.X) > 1e-9)
    if face == 'N':
        return (abs(beam_bb.Min.Y - col_bb.Max.Y) <= tol and
                overlap_1d(beam_bb.Min.X, beam_bb.Max.X, col_bb.Min.X, col_bb.Max.X) > 1e-9)
    return False

def _face_covered_by_floor(face, col_bb, floor_bb, tol=0.066):
    if col_bb is None or floor_bb is None: return False
    if face == 'W':
        return (abs(floor_bb.Max.X - col_bb.Min.X) <= tol and
                overlap_1d(floor_bb.Min.Y, floor_bb.Max.Y, col_bb.Min.Y, col_bb.Max.Y) > 1e-9)
    if face == 'E':
        return (abs(floor_bb.Min.X - col_bb.Max.X) <= tol and
                overlap_1d(floor_bb.Min.Y, floor_bb.Max.Y, col_bb.Min.Y, col_bb.Max.Y) > 1e-9)
    if face == 'S':
        return (abs(floor_bb.Max.Y - col_bb.Min.Y) <= tol and
                overlap_1d(floor_bb.Min.X, floor_bb.Max.X, col_bb.Min.X, col_bb.Max.X) > 1e-9)
    if face == 'N':
        return (abs(floor_bb.Min.Y - col_bb.Max.Y) <= tol and
                overlap_1d(floor_bb.Min.X, floor_bb.Max.X, col_bb.Min.X, col_bb.Max.X) > 1e-9)
    return False

def _face_covered_by_wall(face, col_bb, wall_bb, z0, z1, tol=0.05):
    if col_bb is None or wall_bb is None: return False
    if overlap_1d(wall_bb.Min.Z, wall_bb.Max.Z, z0, z1) <= 1e-9: return False
    if face == 'W':
        return (abs(wall_bb.Max.X - col_bb.Min.X) <= tol and
                overlap_1d(wall_bb.Min.Y, wall_bb.Max.Y, col_bb.Min.Y, col_bb.Max.Y) > 1e-9)
    if face == 'E':
        return (abs(wall_bb.Min.X - col_bb.Max.X) <= tol and
                overlap_1d(wall_bb.Min.Y, wall_bb.Max.Y, col_bb.Min.Y, col_bb.Max.Y) > 1e-9)
    if face == 'S':
        return (abs(wall_bb.Max.Y - col_bb.Min.Y) <= tol and
                overlap_1d(wall_bb.Min.X, wall_bb.Max.X, col_bb.Min.X, col_bb.Max.X) > 1e-9)
    if face == 'N':
        return (abs(wall_bb.Min.Y - col_bb.Max.Y) <= tol and
                overlap_1d(wall_bb.Min.X, wall_bb.Max.X, col_bb.Min.X, col_bb.Max.X) > 1e-9)
    return False

# ---------------------------------------------------------------------------
# v26: Ana govde duvar temas dusumu
# ---------------------------------------------------------------------------
def _wall_contact_width(face, col_bb, wall_bb, tol=0.05):
    """
    Tasiyici duvar kolon ana govdesinin belirli yuzune temas ediyorsa
    temas genisligini dondur (ft). Temas yoksa 0.
    X-kiriş yonunde kolon: W/E yuzlerde dy, S/N yuzlerde dx temas olabilir.
    """
    if col_bb is None or wall_bb is None: return 0.0
    if face == 'W' or face == 'E':
        at_face = (abs(wall_bb.Max.X - col_bb.Min.X) <= tol if face == 'W'
                   else abs(wall_bb.Min.X - col_bb.Max.X) <= tol)
        if not at_face: return 0.0
        return overlap_1d(wall_bb.Min.Y, wall_bb.Max.Y, col_bb.Min.Y, col_bb.Max.Y)
    if face == 'S' or face == 'N':
        at_face = (abs(wall_bb.Max.Y - col_bb.Min.Y) <= tol if face == 'S'
                   else abs(wall_bb.Min.Y - col_bb.Max.Y) <= tol)
        if not at_face: return 0.0
        return overlap_1d(wall_bb.Min.X, wall_bb.Max.X, col_bb.Min.X, col_bb.Max.X)
    return 0.0

# ---------------------------------------------------------------------------
# ANA HESAP: area_column  v26
# ---------------------------------------------------------------------------
def area_column(col, beams, floors, walls, trace_log=None):
    """
    Kolon kalip alani.
    Doner: (net_ft2, method_str)
    """
    do_trace = trace_log is not None
    dx, dy, dz = column_section(col)
    if dx is None or dz is None or dz < 1e-9:
        return 0.0, 'col_no_dims'
    col_bb = get_bbox(col)
    if col_bb is None: return 0.0, 'col_no_bbox'

    cevre = 2.0 * (dx + dy)

    support_z, has_beam = _find_support_z(col_bb, beams, floors)
    if support_z is None: return 0.0, 'col_no_support'
    support_z = max(col_bb.Min.Z, min(col_bb.Max.Z, support_z))
    H_main = max(0.0, support_z - col_bb.Min.Z)

    # v26: Ana govde duvar temas dusumu
    # Tasiyici duvar kolon ana govdesinin bir yuzune temas ediyorsa
    # o yuzun temas genisligi x H_main dusulur.
    FACES = ('W', 'E', 'S', 'N')
    wall_contact_deduct = 0.0
    if walls:
        face_wall_width = {'W': 0.0, 'E': 0.0, 'S': 0.0, 'N': 0.0}
        for wall in walls:
            if not is_structural_wall(wall): continue
            wbb = get_bbox(wall)
            if wbb is None: continue
            if overlap_1d(wbb.Min.Z, wbb.Max.Z, col_bb.Min.Z, support_z) <= 1e-9: continue
            for face in FACES:
                w = _wall_contact_width(face, col_bb, wbb)
                if w > face_wall_width[face]:
                    face_wall_width[face] = w
        for face in FACES:
            w = face_wall_width[face]
            if w > 1e-9:
                wall_contact_deduct += w * H_main
                if do_trace:
                    trace_log.append(
                        u'  DuvarTemas_Govde: yuz={0} w={1:.3f}ft '
                        u'H={2:.3f}ft d={3:.4f}m2'.format(
                            face, w, H_main, to_m2(w * H_main)))

    A_main = max(0.0, cevre * H_main - wall_contact_deduct)

    if do_trace:
        trace_log.append(u'  dx={0:.3f}m dy={1:.3f}m cevre={2:.3f}m'.format(
            dx*0.3048, dy*0.3048, cevre*0.3048))
        trace_log.append(u'  H_main={0:.3f}m A_main={1:.4f}m2'.format(
            H_main*0.3048, to_m2(A_main)))
        trace_log.append(u'  has_beam={0} support_z={1:.3f}ft'.format(
            has_beam, support_z))

    # Kolon basi (kiris varsa)
    A_head = 0.0
    if has_beam and col_bb.Max.Z > support_z + 1e-9:
        floor_z = col_bb.Max.Z
        head_h  = floor_z - support_z
        face_dims   = {'W': dy, 'E': dy, 'S': dx, 'N': dx}
        face_beam_b = {'W': 0.0, 'E': 0.0, 'S': 0.0, 'N': 0.0}
        face_floor_t= {'W': 0.0, 'E': 0.0, 'S': 0.0, 'N': 0.0}
        face_wall_b = {'W': 0.0, 'E': 0.0, 'S': 0.0, 'N': 0.0}

        for beam in beams:
            bbb = get_bbox(beam)
            if bbb is None: continue
            if (xy_overlap_area(col_bb, bbb) <= 1e-9 and
                    not bbox_overlaps_3d(col_bb, bbb, tol=0.25)): continue
            try:
                from eg_kalip_beam import beam_section as _bs
                _bval, _ = _bs(beam)
            except Exception:
                _bval = None
            for face in list(face_dims.keys()):
                if _face_covered_by_beam(face, col_bb, bbb, support_z, floor_z):
                    if _bval and _bval > face_beam_b[face]:
                        face_beam_b[face] = _bval

        for wall in walls:
            if not is_structural_wall(wall): continue
            wbb = get_bbox(wall)
            if wbb is None: continue
            for face in list(face_dims.keys()):
                if _face_covered_by_wall(face, col_bb, wbb, support_z, floor_z):
                    w = _wall_contact_width(face, col_bb, wbb)
                    if w > face_wall_b[face]: face_wall_b[face] = w

        for floor in floors:
            fbb = get_bbox(floor)
            if fbb is None: continue
            if not (fbb.Min.Z < floor_z + 0.033 and fbb.Max.Z > support_z - 0.033):
                continue
            try:
                from eg_kalip_utils import get_double as _gd
                T = _gd(floor, ['Thickness', 'Default Thickness'])
            except Exception:
                T = None
            if T is None or T <= 1e-9: continue
            for face in ('W', 'E', 'S', 'N'):
                if _face_covered_by_floor(face, col_bb, fbb, tol=0.066):
                    if T > face_floor_t[face]:
                        face_floor_t[face] = T

        for face, dim in face_dims.items():
            brut     = dim * head_h
            b_beam   = face_beam_b[face]
            t_fl     = face_floor_t[face]
            b_wall   = face_wall_b[face]
            # Kiris kapattigi dikey serit
            kiris_d  = b_beam * head_h
            # Doseme kapattigi yatay serit (kirisin disinda kalan kisim)
            doseme_d = t_fl * max(0.0, dim - b_beam)
            # Duvar temas
            wall_d   = b_wall * head_h
            net_face = max(0.0, brut - kiris_d - doseme_d - wall_d)
            A_head  += net_face
            if do_trace:
                trace_log.append(
                    u'  Yuz {0}: dim={1:.3f}m h={2:.3f}m '
                    u'beam_b={3:.3f}m fl_t={4:.3f}m wall_b={5:.3f}m '
                    u'net={6:.4f}m2'.format(
                        face,
                        dim*0.3048, head_h*0.3048,
                        b_beam*0.3048, t_fl*0.3048, b_wall*0.3048,
                        to_m2(net_face)))

        if do_trace:
            trace_log.append(u'  head_h={0:.3f}m A_head={1:.4f}m2'.format(
                head_h*0.3048, to_m2(A_head)))

    net = max(0.0, A_main + A_head)
    if do_trace:
        trace_log.append(u'  NET={0:.4f}m2'.format(to_m2(net)))
    return net, 'col_v26'
