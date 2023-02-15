from http import HTTPStatus
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='user')

        cls.url_about = {
            reverse("about:author"): ('about/author.html', HTTPStatus.OK),
            reverse("about:tech"): ('about/tech.html', HTTPStatus.OK)
        }

    def setUp(self):
        self.guest_client = Client()

    def test_about_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for url, template in self.url_about.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertTemplateUsed(response, template[0])

    def test_urls_exists_at_desired_location(self):
        """Страницы доступны любому пользователю."""
        for url, template in self.url_about.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, template[1])
