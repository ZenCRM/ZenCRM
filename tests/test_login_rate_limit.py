import unittest
from app import create_app
from app.config import Config
from app.extensions import db
from app.models.user import User


class LoginRateLimitTest(unittest.TestCase):
    def setUp(self):
        class TestConfig(Config):
            TESTING = True
            SQLALCHEMY_DATABASE_URI = 'sqlite://'
            JWT_SECRET_KEY = 'login-limit-test-key-with-at-least-32-bytes'
            PUSH_ENABLED = False
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.client = self.app.test_client()
        admin = User(email='admin@example.com', first_name='Test', last_name='Admin', role='admin', is_active=True)
        admin.set_password('correct-password')
        db.session.add(admin)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def login(self, email, password, ip):
        return self.client.post('/api/auth/login', json={'email': email, 'password': password},
                                environ_base={'REMOTE_ADDR': ip})

    def test_password_spraying_from_one_address_is_throttled(self):
        statuses = [self.login(f'user{i}@example.com', 'guess', '1.1.1.1').status_code for i in range(31)]
        self.assertEqual(statuses[:30], [401] * 30)
        self.assertEqual(statuses[30], 429)

    def test_failed_logins_from_another_address_do_not_lock_the_account(self):
        for _ in range(31):
            self.login('admin@example.com', 'wrong-password', '1.1.1.1')
        self.assertEqual(self.login('admin@example.com', 'correct-password', '9.9.9.9').status_code, 200)


if __name__ == '__main__':
    unittest.main()
