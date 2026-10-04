import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from flask_jwt_extended import create_access_token
from app import create_app
from app.config import Config
from app.extensions import db
from app.models.user import User


class EmployeeAvatarTests(unittest.TestCase):
    def setUp(self):
        class TestConfig(Config):
            TESTING = True
            SQLALCHEMY_DATABASE_URI = 'sqlite://'
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context(); self.ctx.push()
        self.headers = []
        self.ids = []
        for role in ['admin', 'employee', 'manager']:
            user = User(email=role+'@avatar.test', first_name=role, last_name='Test', role=role, is_active=True)
            user.set_password('test-password-123')
            db.session.add(user); db.session.commit()
            self.ids.append(user.id)
            self.headers.append({'Authorization':'Bearer '+create_access_token(identity=str(user.id))})
        self.client = self.app.test_client()
        self.temp = tempfile.TemporaryDirectory()
        self.upload_patch = patch('app.api.users.AVATAR_DIR', self.temp.name)
        self.serve_patch = patch('app.api.avatars.AVATAR_DIR', self.temp.name)
        self.upload_patch.start(); self.serve_patch.start()

    def tearDown(self):
        self.upload_patch.stop(); self.serve_patch.stop(); self.temp.cleanup()
        db.session.remove(); self.ctx.pop()

    def upload(self, actor=0, employee=1, content=None):
        if content is None:
            stream = io.BytesIO(); metadata = Image.Exif(); metadata[305] = 'Private camera metadata'
            Image.new('RGB',(1200,800),'blue').save(stream,format='JPEG',exif=metadata); content=stream.getvalue()
        return self.client.post(f'/api/users/{self.ids[employee]}/avatar', data={'file':(io.BytesIO(content),'photo.jpg')}, headers=self.headers[actor])

    def test_admin_can_add_replace_and_remove_employee_photo(self):
        first = self.upload(); self.assertEqual(first.status_code,200)
        old_url = first.json['avatar_url']
        served = self.client.get(old_url)
        with Image.open(io.BytesIO(served.data)) as image:
            self.assertEqual(image.format,'PNG'); self.assertEqual(image.size,(512,341))
            self.assertNotIn('exif',image.info)
        served.close()
        second = self.upload(); self.assertEqual(second.status_code,200)
        self.assertNotEqual(old_url,second.json['avatar_url'])
        self.assertEqual(self.client.get(old_url).status_code,404)
        response = self.client.delete(f'/api/users/{self.ids[1]}/avatar', headers=self.headers[0])
        self.assertEqual(response.status_code,200)
        self.assertIsNone(db.session.get(User,self.ids[1]).avatar_url)
        self.assertEqual(list(Path(self.temp.name).iterdir()),[])

    def test_employee_and_manager_cannot_change_other_users_photo(self):
        for actor in [1,2]:
            self.assertEqual(self.upload(actor,0).status_code,403)
            self.assertEqual(self.client.delete(f'/api/users/{self.ids[0]}/avatar',headers=self.headers[actor]).status_code,403)
        self.assertEqual(self.upload(1,1).status_code,200)

    def test_invalid_and_oversized_uploads_preserve_existing_photo(self):
        old_url = self.upload().json['avatar_url']
        for content in [b'<script>alert(1)</script>',b'x'*(2*1024*1024+1)]:
            self.assertIn(self.upload(content=content).status_code,[400,413])
            self.assertEqual(db.session.get(User,self.ids[1]).avatar_url,old_url)
            response = self.client.get(old_url)
            self.assertEqual(response.status_code,200)
            response.close()
