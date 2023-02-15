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

        cls.public_urls = {
            reverse("posts:index"): HTTPStatus.OK,
            reverse("posts:posts", kwargs={
                'slug': cls.group.slug}):
            HTTPStatus.OK,
            reverse("posts:profile", kwargs={
                'username': cls.user}):
            HTTPStatus.OK,
            reverse("posts:post_detail", kwargs={
                'post_id': cls.post.id}):
            HTTPStatus.OK,
            '/unexisting_page/': HTTPStatus.NOT_FOUND,
        }

        cls.not_public_urls = {
            reverse("posts:post_edit", kwargs={'post_id': cls.post.id}):
            HTTPStatus.FOUND,
            reverse("posts:post_create"): HTTPStatus.OK,
            reverse("posts:add_comment", kwargs={
                'post_id': cls.post.id}): HTTPStatus.FOUND,
            reverse("posts:follow_index"): HTTPStatus.OK,
            reverse("posts:profile_follow", kwargs={
                'username': cls.author}): HTTPStatus.FOUND,
            reverse("posts:profile_unfollow", kwargs={
                'username': cls.author}): HTTPStatus.FOUND,
        }

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.author_client = Client()
        self.author_client.force_login(self.author)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_urls_exists_at_desired_location(self):
        """Страницы доступны любому пользователю."""
        for reverse_name, http_status in self.public_urls.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertEqual(response.status_code, http_status)

    def test_urls_exists_at_desired_location_authorized(self):
        """Страницы доступны авторизованному пользователю."""
        for reverse_name, http_status in self.not_public_urls.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertEqual(response.status_code, http_status)

    def test_post_edit_author(self):
        """Страница posts/<post_id>/edit/ доступна автору"""
        responce = self.author_client.get(f'/posts/{self.post.id}/edit/')
        self.assertEqual(responce.status_code, HTTPStatus.OK)

    def test_anonymus_user_redirect(self):
        """Страница перенаправляет анонимного пользователя на логин"""
        responce = self.guest_client.get('/create/')
        self.assertRedirects(responce, '/auth/login/?next=/create/')
