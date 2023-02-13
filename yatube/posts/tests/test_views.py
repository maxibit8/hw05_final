from django import forms
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from ..views import POSTS_LIMIT
from ..models import User, Follow, Group, Post


SECOND_PAGE_POSTS = 3


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='user')
        cls.group = Group.objects.create(
            title='заголовок',
            description='описание',
            slug='slug',
        )
        cls.small_gif = (b'\x47\x49\x46\x38\x39\x61\x02\x00'
                         b'\x01\x00\x80\x00\x00\x00\x00\x00'
                         b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
                         b'\x00\x00\x00\x2C\x00\x00\x00\x00'
                         b'\x02\x00\x01\x00\x00\x02\x02\x0C'
                         b'\x0A\x00\x3B')

        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
            image=cls.uploaded
        )
        cls.public_urls = (
            (reverse('posts:index'), 'posts/index.html'),
            (reverse(
                'posts:posts', kwargs={
                    'slug': cls.group.slug}),
                'posts/group_list.html'),
            (reverse(
                'posts:profile', kwargs={
                    'username': cls.post.author}),
                'posts/profile.html'),
            (reverse(
                'posts:post_detail', kwargs={
                    'post_id': cls.post.id}),
                'posts/post_detail.html')
        )
        cls.not_public_urls = (
            (reverse('posts:post_create'), 'posts/post_create.html'),
            (reverse(
                'posts:post_edit', kwargs={
                    'post_id': cls.post.id}),
                'posts/post_create.html')
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for reverse_name, template in self.public_urls + self.not_public_urls:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def check_fields(self, post):
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.group, self.group)
        self.assertEqual(post.image, self.post.image)

    def test_public_contest(self):
        """Шаблон public сформирован с правильным контекстом"""
        for reverse_name, _ in self.public_urls:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                if 'page_obj' in response.context:
                    post = response.context.get('page_obj')[0]
                else:
                    post = response.context.get('post')
                self.check_fields(post)

    def test_not_public_contest(self):
        """Шаблон not_public сформирован с правильным контекстом"""
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.ChoiceField,
            'image': forms.fields.ImageField
        }
        for reverse_name, _ in self.not_public_urls:
            for field_name, expected in form_fields.items():
                with self.subTest(
                        reverse_name=reverse_name, field_name=field_name):
                    response = self.authorized_client.get(reverse_name)
                    form_field = response.context.get(
                        'form'
                    ).fields.get(field_name)
                    self.assertIsInstance(form_field, expected)

    def test_cache_index_page(self):
        """Проверка работы кэша"""
        Post.objects.create(
            author=self.user,
            text='Текст кэша',
        )
        response = self.authorized_client.get(reverse('posts:index'))
        delete_post = response.content
        Post.objects.filter(text='Текст кэша').delete()
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(delete_post, response.content)
        cache.clear()
        response_clear = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(response_clear.content, response.content)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='заголовок',
            description='описание',
            slug='test_slug',
        )
        sort_test_post = 13
        list_post = [
            Post(text=f'текст {i}',
                 author=cls.user,
                 group=cls.group) for i in range(sort_test_post)]
        Post.objects.bulk_create(list_post)
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

    def test_paginator_on_pages(self):
        """Проверка пагинации на страницах."""
        posts_in_pages = [POSTS_LIMIT, SECOND_PAGE_POSTS]
        urls = [
            reverse('posts:index'),
            reverse('posts:posts',
                    kwargs={'slug': self.group.slug}),
            reverse('posts:profile',
                    kwargs={'username': self.user}),
        ]
        for test_page in urls:
            with self.subTest(test_page=test_page):
                for page, count in enumerate(posts_in_pages):
                    response = self.authorized_client.get(
                        test_page, {'page': page + 1})
                    self.assertEqual(
                        len(response.context.get('page_obj')), count)


class FollowViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='user')
        cls.follower = User.objects.create(username='follower')
        cls.post = Post.objects.create(
            text='текст',
            author=cls.user
        )

    def setUp(self):
        cache.clear()
        self.author_client = Client()
        self.author_client.force_login(self.user)
        self.follower_client = Client()
        self.follower_client.force_login(self.follower)

    def test_follow(self):
        """Проверка подписки на автора"""
        self.follower_client.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.user}))
        self.assertEqual(Follow.objects.all().count(), 1)

    def test_unfollow(self):
        """Проверка отписки от автора"""
        self.follower_client.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.user}))
        self.follower_client.get(
            reverse('posts:profile_unfollow',
                    kwargs={'username': self.user}))
        self.assertEqual(Follow.objects.all().count(), 0)

    def test_post_follow_unfollow(self):
        """Проверка поста в подписках и без подписок"""
        Follow.objects.create(
            user=self.follower,
            author=self.user)
        response = self.follower_client.get(
            reverse('posts:follow_index'))
        self.assertIn(self.post, response.context['page_obj'].object_list)
        response = self.author_client.get(
            reverse('posts:follow_index'))
        self.assertNotIn(self.post, response.context['page_obj'].object_list)
