import pytest
from app.review_messages import review_status, MESSAGES
from app.main import result_view

@pytest.mark.parametrize('mode,expected',[
 ('input_validation','input_invalid'),
 ('campus-qwen','photo_rejected'),
 ('explicit_demo_photos','photo_rejected'),
 ('model_unavailable:OpenAIRateLimitError:HTTP429','review_busy'),
 ('model_unavailable:APITimeoutError','review_timeout'),
 ('model_unavailable:APIConnectionError','review_unavailable'),
 ('model_unavailable:AuthenticationError:HTTP401','review_unavailable'),
 ('model_unavailable:InternalServerError:HTTP500','review_unavailable'),
 ('model_unavailable:ValidationError','review_unavailable'),
])
def test_review_failures_have_distinct_public_messages(mode,expected):
    assessment={'mode':mode,'errors':{'front':'Internal error'}}
    assert review_status(assessment)==expected
    raw={'assessment':assessment,'errors':dict(assessment['errors']),'screenReason':'Internal error'}
    public=result_view(raw,'seller')
    assert public['reviewStatus']==expected
    assert 'assessment' not in public
    if expected in MESSAGES:assert public['errors']['front']==MESSAGES[expected]
    assert result_view(raw,'manager')==raw

def test_missing_fields_are_not_photo_policy_violations():
    errors={'name':'请填写有效内容（2–80 字符）','front':'请上传正面照片'}
    result=result_view({'assessment':{'mode':'input_validation','errors':errors},'errors':errors},'seller')
    assert result['reviewStatus']=='input_invalid'
    assert result['errors']==errors
