import json
import pytest
from app import public_market as public
from app.market_pricing import market_price, SearchPlan, Comparison, Match
from app.agents import ROUTES

FORM=dict(name='Fabric sofa',category='沙发',material='fabric',condition='良好',age=2,width=180,depth=80,height=75)

def model(schema,prompt,content):
    if schema is SearchPlan:return SearchPlan(query='fabric sofa',category='sofas')
    rows=json.loads(content)['records']
    return Comparison(matches=[Match(id=r['id'],score=80,reason='Comparable fabric sofa; age not supplied',unknowns=['age']) for r in rows]+[Match(id='invented',score=100,reason='fake',unknowns=[])])

def test_only_explicit_pricing_route_queries_market():
    assert 'PricingAgent' not in ROUTES['listing']
    assert ROUTES['pricing']==['ListingAgent','PricingAgent']

def test_incomplete_does_not_call_network(monkeypatch):
    monkeypatch.setattr(public,'public_candidates',lambda *args:pytest.fail('Network should not be called'))
    assert market_price({},model)['status']=='incomplete'

def test_evidence_weighted_median_ignores_invented_ids(monkeypatch):
    rows=[dict(id=str(i),url='https://www.zirkly.com.au/item/'+str(i),price=p,title='Used sofa') for i,p in enumerate([200,400,9000])]
    monkeypatch.setattr(public,'public_candidates',lambda *args:(rows,[]))
    result=market_price(FORM,model)
    assert result['suggested']==400
    assert len(result['evidence'])==3
    assert result['retrievedAt']
    assert result['subject']['age']==2

def test_no_fallback_when_evidence_or_model_missing(monkeypatch):
    monkeypatch.setattr(public,'public_candidates',lambda *args:([],[]))
    assert market_price(FORM,model)['suggested'] is None
    def broken(*args):raise RuntimeError('offline')
    assert market_price(FORM,broken)['suggested'] is None

def test_low_similarity_never_prices(monkeypatch):
    monkeypatch.setattr(public,'public_candidates',lambda *args:([{'id':str(i),'price':100} for i in range(3)],[]))
    def low(schema,*args):
        if schema is SearchPlan:return SearchPlan(query='sofa',category='sofas')
        return Comparison(matches=[Match(id=str(i),score=20,reason='Wrong material',unknowns=[]) for i in range(3)])
    assert market_price(FORM,low)['status']=='insufficient'

@pytest.mark.parametrize('currency,condition,availability,price,valid',[
    ('AUD','UsedCondition','InStock','250',True),('USD','UsedCondition','InStock','250',False),
    ('AUD','NewCondition','InStock','250',False),('AUD','UsedCondition','SoldOut','250',False),
    ('AUD','UsedCondition','InStock','NaN',False),('AUD','UsedCondition','InStock','0',False)])
def test_public_schema_prices(currency,condition,availability,price,valid):
    page=public.Page()
    row={'@type':'Product','name':'Sofa','description':'Good fabric sofa','offers':{'price':price,'priceCurrency':currency,'itemCondition':'https://schema.org/'+condition,'availability':'https://schema.org/'+availability}}
    page.feed('<script type="application/ld+json">'+json.dumps(row)+'</script>')
    assert bool(public.product(page,'https://www.zirkly.com.au/item'))==valid

def test_fetch_allowlist():
    assert public.allowed('https://www.zirkly.com.au/second-hand-furniture')
    assert not public.allowed('https://www.zirkly.com.au.evil.test/')
    assert not public.allowed('http://127.0.0.1/')
