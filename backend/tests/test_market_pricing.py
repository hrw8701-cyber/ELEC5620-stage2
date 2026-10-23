import json
import pytest
from app import public_market as public
from app.market_pricing import market_price, attributes, score_row
from app.agents import ROUTES

FORM=dict(name='Fabric sofa',category='沙发',material='fabric',condition='良好',age=2,width=180,depth=80,height=75)

def records():
    return [dict(id=str(i),url='https://www.zirkly.com.au/item/'+str(i),price=p,title='Used fabric sofa',description='Good condition, 2 years old, width 180 cm depth 80 cm height 75 cm',currency='AUD',observedAt='2026-10-23T00:00:00Z') for i,p in enumerate([200,400,9000])]

def test_only_explicit_pricing_route_queries_market():
    assert 'PricingAgent' not in ROUTES['listing']
    assert ROUTES['pricing']==['ListingAgent','PricingAgent']

def test_incomplete_does_not_call_network(monkeypatch):
    monkeypatch.setattr(public,'public_candidates',lambda *args:pytest.fail('Network should not be called'))
    assert market_price({})['status']=='incomplete'

def test_cached_pricing_no_network_or_model_and_resists_outlier(monkeypatch):
    monkeypatch.setattr('app.market_pricing.reference_rows',lambda *args:records())
    monkeypatch.setattr(public,'public_candidates',lambda *args:pytest.fail('Pricing must use stored references'))
    result=market_price(FORM,lambda *args:pytest.fail('Pricing must not wait for a model'))
    assert result['suggested']==400 and len(result['evidence'])==3
    assert result['method']=='attribute_weighted_median_v2'
    assert market_price(FORM)['suggested']==result['suggested']

def test_no_platform_fallback(monkeypatch):
    monkeypatch.setattr('app.market_pricing.reference_rows',lambda *args:[])
    assert market_price(FORM)['suggested'] is None

def test_wrong_material_and_large_size_excluded():
    row=records()[0]
    assert score_row(dict(FORM,material='leather'),row) is None
    assert score_row(dict(FORM,width=500),row) is None

def test_unknown_age_not_invented():
    row=records()[0];row['description']='good condition fabric sofa'
    result=score_row(FORM,row)
    assert result['attributes']['age'] is None and '年限' in result['unknowns']

def test_condition_adjustment_uses_disclosed_evidence(monkeypatch):
    monkeypatch.setattr('app.market_pricing.reference_rows',lambda *args:records())
    assert market_price(dict(FORM,condition='一般'))['suggested'] < market_price(FORM)['suggested']

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
