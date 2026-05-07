import io
import unittest

from PIL import Image

from wrap import app


def build_image_bytes(fmt='JPEG'):
    image = Image.new('RGB', (16, 16), color='navy')
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    buffer.seek(0)
    return buffer


class ScrubberApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_health_endpoint(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json().get('status'), 'healthy')

    def test_scrub_missing_image_returns_400(self):
        response = self.client.post('/scrub', data={}, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertEqual(body.get('category'), 'input_error')

    def test_scrub_sanitizes_filename_in_download_name(self):
        img = build_image_bytes('JPEG')
        response = self.client.post(
            '/scrub',
            data={'image': (img, '../../unsafe name.jpg')},
            content_type='multipart/form-data'
        )
        try:
            self.assertEqual(response.status_code, 200)
            disposition = response.headers.get('Content-Disposition', '')
            self.assertIn('attachment;', disposition)
            self.assertNotIn('..', disposition)
            self.assertIn('scrubbed_unsafe_name.jpg', disposition)
        finally:
            response.close()

    def test_scrub_success_returns_headers(self):
        img = build_image_bytes('PNG')
        response = self.client.post(
            '/scrub',
            data={'image': (img, 'clean.png')},
            content_type='multipart/form-data'
        )
        try:
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.headers.get('X-Processing-Time'))
            self.assertIsNotNone(response.headers.get('X-Metadata-Removed'))
        finally:
            response.close()


if __name__ == '__main__':
    unittest.main()
