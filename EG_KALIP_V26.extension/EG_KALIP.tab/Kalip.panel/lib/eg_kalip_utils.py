# -*- coding: utf-8 -*-
"""
eg_kalip_utils.py  v23
Tum yardimci fonksiyonlar: birim, bbox, geometri, parametre, eleman.
Hicbir hesap mantigi burada yok — sadece arac fonksiyonlari.
"""
from Autodesk.Revit.DB import (
    FilteredElementCollector, BuiltInCategory, ElementId,
    UnitUtils, BuiltInParameter, Options, Solid,
    ElementIntersectsElementFilter, BoundingBoxIntersectsFilter,
    Outline, XYZ,
)

try:
    from Autodesk.Revit.DB import UnitTypeId
    _USE_UNIT_TYPE_ID = True
except Exception:
    _USE_UNIT_TYPE_ID = False

# ---------------------------------------------------------------------------
# Birim
# ---------------------------------------------------------------------------
def to_m2(v):
    try:
        if _USE_UNIT_TYPE_ID:
            return UnitUtils.ConvertFromInternalUnits(v, UnitTypeId.SquareMeters)
        return UnitUtils.ConvertFromInternalUnits(v, DisplayUnitType.DUT_SQUARE_METERS)
    except Exception:
        return v * 0.09290304

def to_m(v):
    try:
        if _USE_UNIT_TYPE_ID:
            return UnitUtils.ConvertFromInternalUnits(v, UnitTypeId.Meters)
        return UnitUtils.ConvertFromInternalUnits(v, DisplayUnitType.DUT_METERS)
    except Exception:
        return v * 0.3048

# ---------------------------------------------------------------------------
# Parametre okuma
# ---------------------------------------------------------------------------
def get_param(el, names):
    for n in names:
        try:
            p = el.LookupParameter(n)
            if p and p.HasValue:
                return p
        except Exception:
            pass
    return None

def get_double(el, names):
    p = get_param(el, names)
    if p:
        try:
            return p.AsDouble()
        except Exception:
            pass
    return None

def get_string(el, names):
    p = get_param(el, names)
    if p:
        try:
            s = p.AsValueString()
            if s: return s
        except Exception:
            pass
        try:
            s = p.AsString()
            if s: return s
        except Exception:
            pass
    return ""

# ---------------------------------------------------------------------------
# Eleman bilgi
# ---------------------------------------------------------------------------
def get_element_id_int(el):
    try:
        return el.Id.Value
    except AttributeError:
        return el.Id.IntegerValue

def get_category_name(el):
    """BIC integer uzerinden dil bagimsiz kategori adi."""
    try:
        cat = el.Category
        if not cat:
            return ""
        cid = cat.Id
        try:
            bic = cid.IntegerValue
        except Exception:
            try:
                bic = cid.Value
            except Exception:
                bic = None
        if bic is not None:
            try:
                if bic == int(BuiltInCategory.OST_StructuralColumns):
                    return 'Structural Columns'
                if bic == int(BuiltInCategory.OST_StructuralFraming):
                    return 'Structural Framing'
                if bic == int(BuiltInCategory.OST_Walls):
                    return 'Walls'
                if bic == int(BuiltInCategory.OST_Floors):
                    return 'Floors'
                if bic == int(BuiltInCategory.OST_StructuralFoundation):
                    return 'Structural Foundations'
            except Exception:
                pass
        return cat.Name or ""
    except Exception:
        return ""

# ---------------------------------------------------------------------------
# v25b FIX 1: BuiltInCategory-based kategori tespiti (dil bagimsiz)
# ---------------------------------------------------------------------------
def get_category_bic(el):
    """Eleman BIC integer degerini dondurur. Kategori yoksa None."""
    try:
        cat = el.Category
        if not cat:
            return None
        cid = cat.Id
        try:
            return cid.IntegerValue
        except Exception:
            try:
                return cid.Value
            except Exception:
                return None
    except Exception:
        return None

def is_category(el, bic):
    """Eleman verilen BuiltInCategory'ye mi ait? Dil bagimsiz."""
    try:
        elbic = get_category_bic(el)
        if elbic is None:
            return False
        return elbic == int(bic)
    except Exception:
        return False

def is_wall(el):
    return is_category(el, BuiltInCategory.OST_Walls)

def is_column(el):
    return is_category(el, BuiltInCategory.OST_StructuralColumns)

def is_beam(el):
    return is_category(el, BuiltInCategory.OST_StructuralFraming)

def is_floor(el):
    return is_category(el, BuiltInCategory.OST_Floors)

def is_foundation(el):
    return is_category(el, BuiltInCategory.OST_StructuralFoundation)

def get_level_name(doc, el):
    try:
        lid = el.LevelId
        if lid and lid != ElementId.InvalidElementId:
            lvl = doc.GetElement(lid)
            if lvl: return lvl.Name
    except Exception:
        pass
    return get_string(el, ["Reference Level", "Base Level", "Level"])

def get_type_name(doc, el):
    try:
        tid = el.GetTypeId()
        if tid and tid != ElementId.InvalidElementId:
            typ = doc.GetElement(tid)
            if typ:
                fam = ""
                try: fam = typ.FamilyName
                except Exception: pass
                tname = ""
                try:
                    p = typ.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
                    if p: tname = p.AsString() or ""
                except Exception: pass
                if fam and tname: return fam + " : " + tname
                return tname or fam or ""
    except Exception:
        pass
    return ""

def is_structural_wall(wall):
    try:
        p = wall.get_Parameter(BuiltInParameter.WALL_STRUCTURAL_SIGNIFICANT)
        if p and p.AsInteger() == 1:
            return True
    except Exception:
        pass
    usage = get_string(wall, ["Structural Usage", "Yapisal Kullanim"])
    if usage:
        txt = usage.lower().strip()
        if txt not in ("", "non-bearing", "non bearing", "tasimayan"):
            return True
    return False

# ---------------------------------------------------------------------------
# Eleman toplama
# ---------------------------------------------------------------------------
def collect_category(doc, bic):
    try:
        return list(FilteredElementCollector(doc)
                    .OfCategory(bic)
                    .WhereElementIsNotElementType()
                    .ToElements())
    except Exception:
        return []

def collect_all(doc):
    """(elems, counts) — tum yapisal kategoriler."""
    BICATS = [
        BuiltInCategory.OST_StructuralColumns,
        BuiltInCategory.OST_StructuralFraming,
        BuiltInCategory.OST_Walls,
        BuiltInCategory.OST_Floors,
        BuiltInCategory.OST_StructuralFoundation,
    ]
    result, counts = [], {}
    for bic in BICATS:
        els = collect_category(doc, bic)
        counts[str(bic)] = len(els)
        result.extend(els)
    return result, counts

# ---------------------------------------------------------------------------
# BBox yardımcıları
# ---------------------------------------------------------------------------
def get_bbox(el):
    try:
        return el.get_BoundingBox(None)
    except Exception:
        return None

def bbox_dims(el):
    bb = get_bbox(el)
    if bb:
        return (abs(bb.Max.X - bb.Min.X),
                abs(bb.Max.Y - bb.Min.Y),
                abs(bb.Max.Z - bb.Min.Z))
    return (None, None, None)

def overlap_1d(a0, a1, b0, b1):
    return max(0.0, min(a1, b1) - max(a0, b0))

def xy_overlap_area(bb1, bb2):
    if bb1 is None or bb2 is None: return 0.0
    dx = overlap_1d(bb1.Min.X, bb1.Max.X, bb2.Min.X, bb2.Max.X)
    dy = overlap_1d(bb1.Min.Y, bb1.Max.Y, bb2.Min.Y, bb2.Max.Y)
    return dx * dy if dx > 1e-9 and dy > 1e-9 else 0.0

def rect_intersection_xy(bb1, bb2):
    if bb1 is None or bb2 is None: return None
    x0 = max(bb1.Min.X, bb2.Min.X); x1 = min(bb1.Max.X, bb2.Max.X)
    y0 = max(bb1.Min.Y, bb2.Min.Y); y1 = min(bb1.Max.Y, bb2.Max.Y)
    if x1 <= x0 + 1e-9 or y1 <= y0 + 1e-9: return None
    return (x0, x1, y0, y1)

def union_rectangles_area(rects):
    arc_extra = sum(r[1] for r in rects
                    if isinstance(r, tuple) and len(r)==2 and r[0]=='arc_area')
    rects = [r for r in rects
             if not (isinstance(r, tuple) and len(r)==2 and r[0]=='arc_area')]
    rects = [r for r in rects if r and r[1]>r[0]+1e-9 and r[3]>r[2]+1e-9]
    if not rects: return arc_extra
    xs = sorted(set([r[0] for r in rects]+[r[1] for r in rects]))
    total = 0.0
    for i in range(len(xs)-1):
        x0, x1 = xs[i], xs[i+1]
        if x1 <= x0+1e-9: continue
        intervals = []
        for rx0,rx1,ry0,ry1 in rects:
            if rx0 < x1-1e-9 and rx1 > x0+1e-9:
                intervals.append((ry0, ry1))
        if not intervals: continue
        intervals.sort()
        ys = 0.0; s,e = intervals[0]
        for cs,ce in intervals[1:]:
            if cs <= e+1e-9:
                if ce > e: e = ce
            else:
                ys += e-s; s,e = cs,ce
        ys += e-s
        total += (x1-x0)*ys
    return total + arc_extra

def xy_contact_or_overlap(bb1, bb2, tol=0.05):
    if bb1 is None or bb2 is None: return False
    return (bb1.Max.X >= bb2.Min.X-tol and bb1.Min.X <= bb2.Max.X+tol and
            bb1.Max.Y >= bb2.Min.Y-tol and bb1.Min.Y <= bb2.Max.Y+tol)

def bbox_overlaps_3d(bb1, bb2, tol=0.1):
    if bb1 is None or bb2 is None: return False
    return (bb1.Max.X > bb2.Min.X-tol and bb1.Min.X < bb2.Max.X+tol and
            bb1.Max.Y > bb2.Min.Y-tol and bb1.Min.Y < bb2.Max.Y+tol and
            bb1.Max.Z > bb2.Min.Z-tol and bb1.Min.Z < bb2.Max.Z+tol)

def point_in_bbox_xy(pt, bb, tol=1e-9):
    if pt is None or bb is None: return False
    return (bb.Min.X-tol <= pt.X <= bb.Max.X+tol and
            bb.Min.Y-tol <= pt.Y <= bb.Max.Y+tol)

# ---------------------------------------------------------------------------
# Geometri yardımcıları
# ---------------------------------------------------------------------------
def segment_midpoint(p0, p1):
    class _P(object): pass
    mp = _P()
    mp.X = (p0.X+p1.X)*0.5; mp.Y = (p0.Y+p1.Y)*0.5; mp.Z = (p0.Z+p1.Z)*0.5
    return mp

def segment_length_3d(p0, p1):
    dx=p1.X-p0.X; dy=p1.Y-p0.Y; dz=p1.Z-p0.Z
    return (dx*dx+dy*dy+dz*dz)**0.5

def point_segment_distance_xy(pt, a, b):
    ax=a.X; ay=a.Y; bx=b.X; by=b.Y; px=pt.X; py=pt.Y
    abx=bx-ax; aby=by-ay; apx=px-ax; apy=py-ay
    den=abx*abx+aby*aby
    if den<=1e-12:
        return ((px-ax)**2+(py-ay)**2)**0.5
    t=max(0.0,min(1.0,(apx*abx+apy*aby)/den))
    qx=ax+t*abx; qy=ay+t*aby
    return ((px-qx)**2+(py-qy)**2)**0.5

def curve_polyline_points(el, dense=False, step=0.25):
    """Eleman eksen egrisinin tessellate noktalari."""
    try:
        c = el.Location.Curve
        if dense:
            L = c.Length
            if L and L > step:
                div = max(8, int(L/step))
                pts = [c.Evaluate(float(i)/float(div), True) for i in range(div+1)]
                if len(pts) >= 2: return pts
        pts = list(c.Tessellate())
        if pts and len(pts) >= 2: return pts
        return [c.GetEndPoint(0), c.GetEndPoint(1)]
    except Exception:
        return []

def polyline_length_inside_bbox_xy(points, bb):
    if not points or len(points)<2 or bb is None: return 0.0
    total = 0.0
    for i in range(len(points)-1):
        mid = segment_midpoint(points[i], points[i+1])
        if point_in_bbox_xy(mid, bb, tol=1e-6):
            total += segment_length_3d(points[i], points[i+1])
    return total

def _union_intervals(intervals):
    if not intervals: return 0.0
    intervals.sort()
    total=0.0; s,e=intervals[0]
    for cs,ce in intervals[1:]:
        if cs<=e:
            if ce>e: e=ce
        else:
            total+=e-s; s,e=cs,ce
    total+=e-s
    return total

# ---------------------------------------------------------------------------
# v25b FIX 4: Intersection prefilter
# ElementIntersectsElementFilter (gercek geometri) + BoundingBoxIntersectsFilter
# (bbox yedek). Sonuclari birlestirip sadece kesisen elemanlari dondur.
# ---------------------------------------------------------------------------
def _bbox_outline(bb, pad=0.05):
    """BoundingBoxXYZ -> Outline (pad ft kadar genisletilmis)."""
    if bb is None:
        return None
    try:
        mn = XYZ(bb.Min.X - pad, bb.Min.Y - pad, bb.Min.Z - pad)
        mx = XYZ(bb.Max.X + pad, bb.Max.Y + pad, bb.Max.Z + pad)
        return Outline(mn, mx)
    except Exception:
        return None

def _candidate_ids(candidates):
    ids = []
    for c in candidates:
        try:
            ids.append(c.Id)
        except Exception:
            pass
    return ids

def _eid_int(eid):
    """ElementId -> integer (Revit 2024+ .Value, eski .IntegerValue)."""
    try:
        return eid.IntegerValue
    except Exception:
        try:
            return eid.Value
        except Exception:
            return None

def intersecting_elements(doc, host, candidates):
    """
    Host ile kesisen elemanlari dondur.

    v25b-fix: FilteredElementCollector(doc, cand_ids) YANLIStir — ikinci
    argüman View.Id olmali, ElementId listesi degil. Bunun yerine filtreyi
    tum dokuman uzerinde calistirip sonuclari cand_ids seti ile kesistiriyoruz.

    1) ElementIntersectsElementFilter(host) — tum dokumandan, sonra cand_ids'e gore filtrele
    2) BoundingBoxIntersectsFilter(host bbox) — ayni sekilde
    3) Manuel bbox_overlaps_3d fallback — filtreler hic calismazsa

    Uclu sonuc union'lanir; aday listesinin sirasi korunur.

    Parametreler:
      doc        : Autodesk.Revit.DB.Document
      host       : referans alinan eleman (kiris/kolon/doseme/duvar/temel)
      candidates : aday eleman listesi (ayni kategori olmasi sart degil)

    Doner: candidates listesinin kesisen alt kumesi.
    """
    if host is None or not candidates:
        return []

    # Aday id setini kur (integer olarak)
    cand_id_set = set()
    for c in candidates:
        try:
            cid = _eid_int(c.Id)
            if cid is not None:
                cand_id_set.add(cid)
        except Exception:
            pass
    if not cand_id_set:
        return []

    hit_ids = set()

    # 1) Gercek geometri kesisimi — tum dokumandan tarayip cand_id_set'e gore filtrele
    try:
        f_geo = ElementIntersectsElementFilter(host)
        col = (FilteredElementCollector(doc)
               .WhereElementIsNotElementType()
               .WherePasses(f_geo))
        for e in col:
            try:
                eid = _eid_int(e.Id)
                if eid is not None and eid in cand_id_set:
                    hit_ids.add(eid)
            except Exception:
                pass
    except Exception:
        pass

    # 2) BoundingBox — tum dokumandan tarayip cand_id_set'e gore filtrele
    try:
        hbb = get_bbox(host)
        outline = _bbox_outline(hbb, pad=0.05)
        if outline is not None:
            f_bb = BoundingBoxIntersectsFilter(outline)
            col = (FilteredElementCollector(doc)
                   .WhereElementIsNotElementType()
                   .WherePasses(f_bb))
            for e in col:
                try:
                    eid = _eid_int(e.Id)
                    if eid is not None and eid in cand_id_set:
                        hit_ids.add(eid)
                except Exception:
                    pass
    except Exception:
        pass

    # 3) Manuel bbox fallback (filtreler hic calismazsa)
    if not hit_ids:
        try:
            hbb = get_bbox(host)
            if hbb is not None:
                for c in candidates:
                    try:
                        cbb = get_bbox(c)
                        if cbb is None: continue
                        if bbox_overlaps_3d(hbb, cbb, tol=0.1):
                            cid = _eid_int(c.Id)
                            if cid is not None:
                                hit_ids.add(cid)
                    except Exception:
                        pass
        except Exception:
            pass

    if not hit_ids:
        return []

    # Aday listesindeki sirayi koruyarak filtrele
    result = []
    for c in candidates:
        try:
            cid = _eid_int(c.Id)
        except Exception:
            continue
        if cid is not None and cid in hit_ids:
            result.append(c)
    return result
