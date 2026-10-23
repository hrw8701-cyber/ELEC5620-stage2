"""PricingAgent local evidence scoring. No web/model calls during price calculation."""
from datetime import datetime, timezone
import math
import re
from .market_store import reference_rows

FIELDS=('name','category','material','condition','age','width','depth','height')
MATERIALS={'fabric':['fabric','cloth','linen','velvet','polyester','cotton','chenille','microfibre','upholster','布','绒','麻'],
 'leather':['leather','皮'], 'wood':['wood','timber','oak','pine','mahogany','木'],
 'metal':['metal','steel','iron','金属','铁','钢'], 'glass':['glass','玻璃'], 'plastic':['plastic','塑料']}

def material(text):
    text=text.lower()
    # Upholstery material takes precedence over frame material.
    for group in ['leather','fabric','wood','metal','glass','plastic']:
        if any(x in text for x in MATERIALS[group]):return group
    return None

def attributes(row):
    text=(row.get('title','')+' '+row.get('description','')).lower()
    grade=3 if re.search(r'near.new|excellent|like.new|pristine',text) else 1 if re.search(r'poor condition|worn|heavy wear|damage',text) else 2 if re.search(r'good|minor wear|minor.*scratch|used condition',text) else None
    age=re.search(r'(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\s*old',text)
    dims={}
    for key,word in [('width','wide'),('depth','deep'),('height','high')]:
        found=re.search(r'(\d+(?:\.\d+)?)\s*cm\s*(?:'+word+r')',text) or re.search(r'(?:'+key+r')\s*[:=]?\s*(\d+(?:\.\d+)?)\s*cm',text)
        if found:dims[key]=float(found[1])
    return {'material':material(text),'condition':grade,'age':float(age[1]) if age else None,**dims}

def unavailable(status, **extra):
    return dict(suggested=None,evidence=[],status=status,source='Stored public used-furniture references',**extra)

def score_row(subject,row):
    title=row.get('title','').lower()
    if re.search(r'\b(bundle|sofa set|lounge set|sofa.*(?:and|,)\s*(?:matching\s*)?(?:armchair|chair|ottoman)|\d[ -]piece|bed.*and.*bedside|cover|cushion only)\b',title):return None
    if subject['category']=='沙发' and not re.search(r'sofa|couch|lounge',title):return None
    if subject['category']=='沙发':
        seats=re.search(r'(\d+)[ -]?seater',title)
        if seats and int(seats[1])*40>float(subject['width']):return None
    if subject['category']=='床' and (not re.search(r'\bbed\b|bedframe',title) or re.search(r'sofa|sofabed',title)):return None
    if subject['category']=='其他':
        types={'table':['table','desk','桌'],'chair':['chair','stool','椅','凳'],'storage':['cabinet','wardrobe','drawer','shelf','柜','架']}
        intended=next((k for k,v in types.items() if any(x in subject['name'].lower() for x in v)),None)
        if not intended or not any(x in title for x in types[intended] if x.isascii()):return None
    a=attributes(row); unknown=[];score=20;facts=[]
    target=material(subject['material'])
    if target and a['material']:
        if target!=a['material']:return None
        score+=25;facts.append('材质匹配')
    else:score+=10;unknown.append('材质')
    grade={'一般':1,'良好':2,'优秀':3}.get(subject['condition'],2)
    if a['condition'] is not None:score+=max(4,20-8*abs(grade-a['condition']));facts.append('已比较成色')
    else:score+=8;unknown.append('成色')
    if a['age'] is not None:score+=15*max(0,1-abs(float(subject['age'])-a['age'])/10);facts.append('已比较年限')
    else:score+=5;unknown.append('年限')
    size=[]
    for key,label in [('width','宽度'),('depth','深度'),('height','高度')]:
        if key in a:
            ratio=abs(float(subject[key])-a[key])/max(float(subject[key]),a[key])
            if ratio>.5:return None
            size.append(max(0,1-2*ratio))
        else:unknown.append(label)
    score+=15*(sum(size)+(3-len(size))*.33)/3
    tokens=set(re.findall(r'[a-z]{3,}',subject['name'].lower()))
    score+=5*(sum(t in title for t in tokens)/len(tokens) if tokens else .5)
    # Adjust only disclosed condition/age; never invent missing parameters.
    factor=1.0
    if a['condition'] is not None:factor*= {1:.65,2:.85,3:1}[grade]/{1:.65,2:.85,3:1}[a['condition']]
    if a['age'] is not None:factor*=max(.35,1-.06*float(subject['age']))/max(.35,1-.06*a['age'])
    factor=max(.7,min(1.3,factor))
    return dict(row,matchScore=round(score),unknowns=unknown,reason='；'.join(facts) or '同类二手家具',attributes=a,adjustmentFactor=round(factor,4),adjustedPrice=round(float(row['price'])*factor,2))

def market_price(form, model=None):
    subject={k:form.get(k) for k in FIELDS}
    if any(not str(subject.get(k) or '').strip() for k in ('name','category','material','condition')):return unavailable('incomplete')
    try:
        if any(not 0<float(subject[k])<=1000 for k in ('width','depth','height')) or not 0<=float(subject['age'])<=100:return unavailable('incomplete')
    except (ValueError,TypeError,KeyError):return unavailable('incomplete')
    rows=reference_rows(subject['category'])
    eligible=[]
    for row in rows:
        if row.get('currency')!='AUD' or not math.isfinite(float(row.get('price',0))) or float(row['price'])<=0:continue
        matched=score_row(subject,row)
        if matched and matched['matchScore']>=55:eligible.append(matched)
    eligible=sorted(eligible,key=lambda r:(-r['matchScore'],r['id']))[:5]
    if len(eligible)<3:return unavailable('insufficient',comparisons=eligible)
    ordered=sorted(eligible,key=lambda r:r['adjustedPrice']);half=sum(r['matchScore'] for r in ordered)/2;cumulative=0
    for row in ordered:
        cumulative+=row['matchScore']
        if cumulative>=half:suggested=row['adjustedPrice'];break
    return dict(suggested=suggested,status='ready',source='Stored public used-furniture references',subject=subject,evidence=eligible,
                retrievedAt=max(r['observedAt'] for r in eligible),generatedAt=datetime.now(timezone.utc).isoformat(),
                method='attribute_weighted_median_v2',priceBasis='public_asking_price_with_disclosed_attribute_adjustments',
                range=[min(r['adjustedPrice'] for r in eligible),max(r['adjustedPrice'] for r in eligible)])
