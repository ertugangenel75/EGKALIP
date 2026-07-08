# -*- coding: utf-8 -*-
"""eg_kalip_core.py v25b"""
from Autodesk.Revit.DB import BuiltInCategory, Transaction
from eg_kalip_utils import (
    collect_all, collect_category,
    get_category_name, get_category_bic, get_element_id_int,
    get_type_name, get_level_name, to_m2,
    intersecting_elements,
)
from eg_kalip_beam       import area_beam
from eg_kalip_floor      import area_floor
from eg_kalip_column     import area_column
from eg_kalip_wall       import area_wall
from eg_kalip_foundation import area_foundation

KALIP_POZLAR = {
    '15.180.1001': {'tanim': u'Ahsaptan seri kalip',                      'fiyat': 267.76},
    '15.180.1002': {'tanim': u'Ahsaptan duz yuzeyli betonarme kalibi',    'fiyat': 705.75},
    '15.180.1003': {'tanim': u'Plywood ile duz yuzeyli betonarme kalibi', 'fiyat': 824.39},
    '15.180.1004': {'tanim': u'Sac ile egri yuzeyli betonarme kalibi',    'fiyat': 779.49},
    '15.180.1007': {'tanim': u'Tunel kalip sistemi',                      'fiyat': 853.36},
}
_DEFAULT_POZ = {
    'Structural Columns':     '15.180.1002',
    'Structural Framing':     '15.180.1002',
    'Structural Foundations': '15.180.1002',
    'Floors':                 '15.180.1003',
    'Floors_Edge':            '15.180.1003',
    'Walls':                  '15.180.1003',
}

def calculate(doc, include_edges):
    rows=[];totals={};grand=0.0;trace_dict={}
    elems,counts=collect_all(doc)
    columns=collect_category(doc,BuiltInCategory.OST_StructuralColumns)
    beams  =collect_category(doc,BuiltInCategory.OST_StructuralFraming)
    walls  =collect_category(doc,BuiltInCategory.OST_Walls)
    floors =collect_category(doc,BuiltInCategory.OST_Floors)
    debug=[u'EG_KALIP v25b:']
    for k in sorted(counts): debug.append(u'  {0}={1}'.format(k,counts[k]))
    methods={};zeros={};errors=[]

    # v25b FIX: kategori id'leri onceden hesaplan (dil bagimsiz dispatch)
    _BIC_COL   = int(BuiltInCategory.OST_StructuralColumns)
    _BIC_BEAM  = int(BuiltInCategory.OST_StructuralFraming)
    _BIC_WALL  = int(BuiltInCategory.OST_Walls)
    _BIC_FLOOR = int(BuiltInCategory.OST_Floors)
    _BIC_FND   = int(BuiltInCategory.OST_StructuralFoundation)

    for el in elems:
        a_kenar=0.0;trace_log=[]
        eid_str=str(get_element_id_int(el))
        try:
            el_bic = get_category_bic(el)
            cat=get_category_name(el)
            trace_log.append(u'=== {0} id={1} ==='.format(cat,eid_str))

            # v25b FIX 4: Intersection prefilter — her eleman icin kesisen
            # adaylari on-secimle dar. ElementIntersectsElementFilter +
            # BoundingBoxIntersectsFilter merge. Bos donerse motor yine
            # guvenli calisir (deduct 0 olur, brut alan yaziliyor).
            try:
                pf_beams   = intersecting_elements(doc, el, beams)   if beams   else []
                pf_floors  = intersecting_elements(doc, el, floors)  if floors  else []
                pf_walls   = intersecting_elements(doc, el, walls)   if walls   else []
                pf_columns = intersecting_elements(doc, el, columns) if columns else []
            except Exception:
                # Guvenlik: prefilter cokerse tum listelerle devam (skip yok)
                pf_beams, pf_floors, pf_walls, pf_columns = beams, floors, walls, columns

            trace_log.append(
                u'  Prefilter: beams={0} floors={1} walls={2} cols={3}'.format(
                    len(pf_beams), len(pf_floors), len(pf_walls), len(pf_columns)))

            # v25b FIX 1+2: BuiltInCategory integer uzerinden dispatch.
            # Dil bagimsiz; hicbir eleman yanlislikla 'skip' olmaz.
            if   el_bic == _BIC_COL:
                a,method=area_column(el,pf_beams,pf_floors,pf_walls,trace_log)
            elif el_bic == _BIC_BEAM:
                a,method=area_beam(el,pf_floors,pf_walls,pf_columns,pf_beams,trace_log)
            elif el_bic == _BIC_WALL:
                a,method=area_wall(el,pf_beams,pf_columns,trace_log)
            elif el_bic == _BIC_FLOOR:
                _,method,a_alt,a_kenar=area_floor(el,include_edges,pf_columns,pf_beams,pf_walls,trace_log)
                a=a_alt
            elif el_bic == _BIC_FND:
                a,method=area_foundation(el,pf_walls,trace_log)
            else:
                a,method=0.0,'skip'
        except Exception as ex:
            a,method=0.0,'error'
            trace_log.append(u'HATA: {0}'.format(str(ex)))
            errors.append(u'Id={0}: {1}'.format(eid_str,str(ex)))

        trace_dict[eid_str]=trace_log
        methods[method]=methods.get(method,0)+1
        cat=get_category_name(el) or 'Unknown'

        def _row(rc,ra,rm,fw=None):
            am2=to_m2(ra)
            if fw is None: fw=ra
            pno =_DEFAULT_POZ.get(rc,'15.180.1002')
            pinf=KALIP_POZLAR.get(pno,{})
            return {'category':rc,'fw_area_internal':fw,'element_id':eid_str,
                    'type_name':get_type_name(doc,el),'level':get_level_name(doc,el),
                    'area_internal':ra,'area_m2':am2,'method':rm,
                    'poz_no':pno,'poz_tanim':pinf.get('tanim',pno),'poz_fiyat':pinf.get('fiyat',0.0)}

        fw_total=a+a_kenar
        if a>1e-9:
            grand+=to_m2(a);totals[cat]=totals.get(cat,0.0)+to_m2(a)
            rows.append(_row(cat,a,method,fw=fw_total))
        else:
            zeros[cat]=zeros.get(cat,0)+1
        if a_kenar>0.001:
            ke_m2=to_m2(a_kenar);grand+=ke_m2
            totals['Floors_Edge']=totals.get('Floors_Edge',0.0)+ke_m2
            rows.append(_row('Floors_Edge',a_kenar,'floor_edge'))

    debug.append(u'Hesaplanan={0} Sifir={1} Hata={2}'.format(len(rows),sum(zeros.values()),len(errors)))
    if errors:
        for e in errors[:20]: debug.append(u'  '+e)
    return rows,totals,grand,debug,trace_dict

KALIP_PARAMS=[
    ('Formwork_Area',      'ee000001-aa00-4b00-bb00-000000000001','NUMBER',u'Kalip alani m2'),
    ('TR_KalipAlani',      'a1b2c3d4-e5f6-4a7b-8c9d-000000000004','TEXT',u'Kalip alani m2'),
    ('TR_KalipPozNo',      'a1b2c3d4-e5f6-4a7b-8c9d-000000000001','TEXT',u'Poz no'),
    ('TR_KalipPozAdi',     'a1b2c3d4-e5f6-4a7b-8c9d-000000000002','TEXT',u'Poz adi'),
    ('TR_KalipBirimFiyat', 'a1b2c3d4-e5f6-4a7b-8c9d-000000000003','TEXT',u'Birim fiyat'),
    ('TR_KalipToplamTutar','a1b2c3d4-e5f6-4a7b-8c9d-000000000005','TEXT',u'Toplam tutar'),
]
KALIP_KATEGORILER=[
    BuiltInCategory.OST_StructuralColumns,BuiltInCategory.OST_StructuralFraming,
    BuiltInCategory.OST_Walls,BuiltInCategory.OST_Floors,BuiltInCategory.OST_StructuralFoundation,
]

def _param_exists(doc,pname):
    try:
        it=doc.ParameterBindings.ForwardIterator()
        while it.MoveNext():
            try:
                if it.Key.Name==pname: return True
            except Exception: pass
    except Exception: pass
    return False

def _write_sp(path):
    import io
    lines=['# EG_KALIP sp','*META\tVERSION\tMINVERSION','META\t2\t1',
           '*GROUP\tID\tNAME','GROUP\t1\tEGKalip',
           '*PARAM\tGUID\tNAME\tDATATYPE\tDATACATEGORY\tGROUP\tVISIBLE\tDESCRIPTION\tUSERMODIFIABLE\tHIDEWHENNOVALUE']
    for (pn,guid,dtype,desc) in KALIP_PARAMS:
        lines.append('PARAM\t{0}\t{1}\t{2}\t\t1\t1\t{3}\t1\t0'.format(guid,pn,dtype,desc))
    with io.open(path,'w',encoding='utf-8') as f:
        f.write(u'\n'.join(u'{0}'.format(l) for l in lines))

def ensure_kalip_params(doc):
    from Autodesk.Revit.DB import InstanceBinding,CategorySet
    import tempfile,os
    app=doc.Application;cats=CategorySet()
    for bic in KALIP_KATEGORILER:
        try:
            c=doc.Settings.Categories.get_Item(bic)
            if c: cats.Insert(c)
        except Exception: pass
    binding=InstanceBinding(cats)
    spf=os.path.join(tempfile.gettempdir(),'eg_kalip_sp.txt')
    _write_sp(spf);orig=app.SharedParametersFilename
    created=skipped=0
    try:
        app.SharedParametersFilename=spf
        spfile=app.OpenSharedParameterFile()
        if spfile is None: return 0,0
        grp=spfile.Groups.get_Item('EGKalip')
        if grp is None: return 0,0
        t=Transaction(doc,u'EG_KALIP Parametreler');t.Start()
        try:
            for defn in grp.Definitions:
                if _param_exists(doc,defn.Name): skipped+=1; continue
                try: doc.ParameterBindings.Insert(defn,binding); created+=1
                except Exception: pass
            t.Commit()
        except Exception: t.RollBack()
    finally:
        try: app.SharedParametersFilename=orig if orig else ''
        except Exception: pass
    return created,skipped

def write_back_all(doc,rows):
    from Autodesk.Revit.DB import StorageType
    _rm=[r for r in rows if r['category']!='Floors_Edge']
    mp_fw =dict((r['element_id'],r.get('fw_area_internal',r['area_internal'])) for r in _rm)
    mp_cat=dict((r['element_id'],r['category']) for r in _rm)

    def _set(el,pname,val):
        try:
            p=el.LookupParameter(pname)
            if p is None or p.IsReadOnly: return
            if   p.StorageType==StorageType.String:
                p.Set(u'{0:.2f}'.format(float(val)) if isinstance(val,(int,float)) else u'{0}'.format(val))
            elif p.StorageType==StorageType.Double: p.Set(float(val))
            elif p.StorageType==StorageType.Integer: p.Set(int(round(val)))
        except Exception: pass

    t=Transaction(doc,u'EG_KALIP Yaz');t.Start()
    try:
        elems,_=collect_all(doc)
        fw_w=poz_w=poz_s=0
        for el in elems:
            key=str(get_element_id_int(el))
            cat=mp_cat.get(key,get_category_name(el))
            afw=mp_fw.get(key,0.0);am2=to_m2(afw)
            p_fw=el.LookupParameter('Formwork_Area')
            if p_fw and not p_fw.IsReadOnly:
                try:
                    if p_fw.StorageType==StorageType.Double:
                        _ia=True
                        try:
                            from Autodesk.Revit.DB import SpecTypeId
                            _ia=(p_fw.Definition.GetSpecTypeId()==SpecTypeId.Area)
                        except Exception: pass
                        p_fw.Set(float(afw) if _ia else float(am2))
                    else: _set(el,'Formwork_Area',am2)
                    fw_w+=1
                except Exception: pass
            _set(el,'TR_KalipAlani',am2)
            p_poz=el.LookupParameter('TR_KalipPozNo');mev=''
            if p_poz:
                try: mev=(p_poz.AsString() or '').strip()
                except Exception: pass
            if not mev:
                dp=_DEFAULT_POZ.get(cat,'15.180.1002');pi=KALIP_POZLAR.get(dp,{});bf=pi.get('fiyat',0.0)
                _set(el,'TR_KalipPozNo',dp);_set(el,'TR_KalipPozAdi',pi.get('tanim',''))
                _set(el,'TR_KalipBirimFiyat',bf);poz_w+=1
            else:
                poz_s+=1;pi=KALIP_POZLAR.get(mev,{});bf=pi.get('fiyat',0.0)
                p2=el.LookupParameter('TR_KalipBirimFiyat')
                if p2:
                    try:
                        if p2.StorageType==StorageType.Double: bf=p2.AsDouble()
                        elif p2.StorageType==StorageType.String:
                            s=(p2.AsString() or '').strip()
                            if s: bf=float(s.replace(',','.'))
                    except Exception: pass
            _set(el,'TR_KalipToplamTutar',am2*bf)
        t.Commit();return fw_w,poz_w,poz_s
    except Exception: t.RollBack(); raise
