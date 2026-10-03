"""Static frontend assets are served with the content types browsers expect."""
import unittest

from app import create_app
from app.config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    PUSH_ENABLED = False
    SECRET_KEY = 'test-secret'
    JWT_SECRET_KEY = 'test-jwt-secret'


class StaticAssetsTest(unittest.TestCase):
    def test_hero_images_are_served_as_webp(self):
        client = create_app(TestConfig).test_client()
        for name in ('mountains', 'forest', 'coast'):
            response = client.get(f'/images/hero-{name}-photo.webp')
            self.assertEqual(response.status_code, 200, name)
            self.assertEqual(response.mimetype, 'image/webp', name)
            response.close()


if __name__ == '__main__':
    unittest.main()
