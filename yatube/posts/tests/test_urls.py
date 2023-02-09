from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='user')
        cls.author = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test_slug',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.author,
            group=cls.group,
        )

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.author_client = Client()
        self.author_client.force_login(self.author)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            reverse("posts:index"): 'posts/index.html',
            reverse("posts:posts", kwargs={'slug': self.group.slug}):
            'posts/group_list.html',
            reverse("posts:profile", kwargs={'username': self.user}):
            'posts/profile.html',
            reverse("posts:post_detail", kwargs={'post_id': self.post.id}):
            'posts/post_detail.html',
            reverse("posts:post_edit", kwargs={'post_id': self.post.id}):
            'posts/post_create.html',
            reverse("posts:post_create"): 'posts/post_create.html',
            '/unexisting_page/': 'core/404.html'
        }

        for url, template in templates_url_names.items():
            with self.subTest(url=url):
                response = self.author_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_urls_exists_at_desired_location(self):
        """Страницы доступны любому пользователю."""
        urls = {
            reverse("posts:index"): HTTPStatus.OK,
            reverse("posts:posts", kwargs={'slug': self.group.slug}):
            HTTPStatus.OK,
            reverse("posts:profile", kwargs={'username': self.user}):
            HTTPStatus.OK,
            reverse("posts:post_detail", kwargs={'post_id': self.post.id}):
            HTTPStatus.OK,
            '/unexisting_page/': HTTPStatus.NOT_FOUND,
        }
        for url, http_status in urls.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, http_status)

    def test_urls_exists_at_desired_location_authorized(self):
        """Страницы доступны авторизованному пользователю."""
        urls = {
            reverse("posts:index"): HTTPStatus.OK,
            reverse("posts:posts", kwargs={'slug': self.group.slug}):
            HTTPStatus.OK,
            reverse("posts:profile", kwargs={'username': self.user}):
            HTTPStatus.OK,
            reverse("posts:post_detail", kwargs={'post_id': self.post.id}):
            HTTPStatus.OK,
            reverse("posts:post_edit", kwargs={'post_id': self.post.id}):
            HTTPStatus.FOUND,
            reverse("posts:post_create"): HTTPStatus.OK,
        }

        for url, http_status in urls.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertEqual(response.status_code, http_status)

    def test_post_edit_author(self):
        """Страница posts/<post_id>/edit/ доступна автору"""
        responce = self.author_client.get(f'/posts/{self.post.id}/edit/')
        self.assertEqual(responce.status_code, HTTPStatus.OK)

    def test_anonymus_user_redirect(self):
        """Страница перенаправляет анонимного пользователя на логин"""
        responce = self.guest_client.get('/create/')
        self.assertRedirects(responce, '/auth/login/?next=/create/')
