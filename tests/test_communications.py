import unittest
from datetime import datetime
import test_task_permissions as base
from app.extensions import db
from app.models.client import Client
from app.models.lead import Lead
from app.models.contact import Contact

class CommunicationTest(unittest.TestCase):
    tearDown=base.TaskPermissionsTest.tearDown
    call=base.TaskPermissionsTest.call
    def setUp(self):
        base.TaskPermissionsTest.setUp(self)
        db.session.add_all([Client(id=1,name='Firma'),Lead(id=1,title='Szansa'),Contact(id=1,first_name='Jan',last_name='Test')]); db.session.commit()
    def post(self,**extra):
        return self.call(1,'/api/comments',dict(content='Ustalenia',entity_type='client',entity_id=1,**extra),'post')
    def test_kinds_and_entity_isolation(self):
        for entity in ['client','lead','contact']:
            for kind,states in [('call',['answered','missed']),('email',['outgoing','incoming'])]:
                for state in states:
                    data=dict(content='Ustalenia',entity_type=entity,entity_id=1,kind=kind,communication_status=state,address='123')
                    response=self.call(1,'/api/comments',data,'post'); self.assertEqual(response.status_code,201,response.json)
                    self.assertEqual(response.json['communication_status'],state); self.assertEqual(response.json['user']['id'],1)
            items=self.call(1,'/api/comments?entity_type='+entity+'&entity_id=1',None,'get').json
            self.assertEqual(len(items),4); self.assertTrue(all(x['entity_type']==entity for x in items))
    def test_legacy_and_validation(self):
        self.assertEqual(self.post().json['kind'],'note')
        for data in [dict(kind='call',communication_status='outgoing'),dict(kind='email',communication_status='missed'),dict(kind='other'),dict(kind='note',communication_status='answered')]:
            self.assertEqual(self.post(**data).status_code,400)
        result=self.call(1,'/api/comments',dict(content='x',entity_type='contact',entity_id=999),'post'); self.assertEqual(result.status_code,404)
        db.session.get(Client,1).deleted_at=datetime.utcnow(); db.session.commit(); self.assertEqual(self.post().status_code,404)

    def test_manual_call_note_can_be_updated(self):
        created = self.post(kind='call', communication_status='answered')
        self.assertEqual(created.status_code, 201)
        path = f"/api/comments/{created.json['id']}"
        updated = self.call(1, path, {'content': '  Dalsze ustalenia  '}, 'put')
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json['content'], 'Dalsze ustalenia')
        self.assertEqual(self.call(1, path, {'content': ''}, 'put').status_code, 400)
