from io import BytesIO
import os
from PIL import Image
from fastapi.testclient import TestClient

from app.design import Design, parse_edit, render_design
from app.main import app
from app import youcam

client = TestClient(app)


def test_health_reports_unconfigured(monkeypatch):
    monkeypatch.delenv('YOUCAM_API_KEY', raising=False)
    result = client.get('/api/health')
    assert result.status_code == 200
    assert result.json()['youcam_configured'] is False


def test_frontend():
    result = client.get('/')
    assert result.status_code == 200
    assert 'THREADFORM' in result.text
    assert client.get('/static/app.js').status_code == 200


def test_render_has_reference_dimensions():
    result = client.post('/api/preview', json={'design': Design().asdict()})
    assert result.status_code == 200
    img = Image.open(BytesIO(result.content))
    assert img.size == (533, 729)
    assert img.format == 'JPEG'


def test_variants_are_nonidentical():
    a = render_design(Design())
    b = render_design(Design(base_color='#347d62', line_color='#17191c', pattern='solid'))
    assert a != b


def test_edit_preserves_unmentioned_fields():
    base = Design()
    revised, changed, message = parse_edit('make the checks smaller and black', base)
    assert revised.check_spacing == 6
    assert revised.line_color == '#17191c'
    assert revised.base_color == base.base_color
    assert 'check_spacing' in changed
    assert message is None


def test_more_green_only_changes_base():
    base=Design()
    revised, changed, _ = parse_edit('make the shirt greener',base)
    assert revised.base_color == '#287b5f'
    assert revised.pattern == base.pattern
    assert changed == ['base_color']


def test_unrecognized_edit_does_not_fake_capability():
    base=Design()
    revised, changed, message=parse_edit('make the collar detachable',base)
    assert not changed and message and revised == base


def test_reject_malformed_color():
    result=client.post('/api/preview',json={'design':{'base_color':'not-a-color'}})
    assert result.status_code==422


def test_no_token_refuses_tryon(monkeypatch):
    monkeypatch.delenv('YOUCAM_API_KEY', raising=False)
    result=client.post('/api/tryon',data={'design_json':'{}'}, files={'person':('person.jpg',b'bad','image/jpeg')})
    assert result.status_code == 503


def test_bad_taskid():
    assert client.get('/api/tryon/not:valid').status_code == 400


def test_mocked_provider_workflow(monkeypatch):
    class Res:
        def __init__(self, data, status=200):
            self._data=data;self.status_code=status
        def json(self):return self._data
    from PIL import Image
    from io import BytesIO
    b=BytesIO();Image.new('RGB',(16,22),'teal').save(b,format='JPEG');img=b.getvalue()
    monkeypatch.setenv('YOUCAM_API_KEY','test-only')
    calls=[]
    def post(url,**kw):
        calls.append(('POST',url,kw))
        if url.endswith('/file'):
            return Res({'status':200,'data':{'files':[{'file_id':'file123','requests':[{'url':'https://abc.s3.amazonaws.com/mock','headers':{'Content-Type':'image/jpg'}}]}]}})
        return Res({'status':200,'data':{'task_id':'TASK-12345'}})
    def put(url,**kw):
        calls.append(('PUT',url,kw));return Res({},200)
    def get(url,**kw):
        calls.append(('GET',url,kw));return Res({'status':200,'data':{'task_status':'success','results':{'url':'https://abc.s3.amazonaws.com/signed-result'}}})
    monkeypatch.setattr(youcam.requests,'post',post)
    monkeypatch.setattr(youcam.requests,'put',put)
    monkeypatch.setattr(youcam.requests,'get',get)
    task=youcam.create_tryon(img,'person.jpg',img,'garment.jpg')
    assert task=='TASK-12345'
    assert len([c for c in calls if c[0]=='PUT'])==2
    result=youcam.poll_tryon(task)
    assert result['status']=='success' and result['image_url']


def test_explicit_black_checks_preserves_base_and_pattern():
    base=Design(line_color='#233b63',pattern='window-check')
    revised, changed, _=parse_edit('make the checks black',base)
    assert revised.line_color == '#17191c'
    assert revised.base_color == base.base_color
    assert revised.pattern == 'window-check'
    assert changed == ['line_color']


def test_two_colors_are_targeted_correctly():
    base=Design()
    revised, changed, _=parse_edit('make the shirt green with black checks',base)
    assert revised.base_color == '#347d62'
    assert revised.line_color == '#17191c'
    assert 'base_color' in changed
