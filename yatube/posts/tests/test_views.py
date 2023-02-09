import shutil
import tempfile

from django import forms
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import User, Follow, Group, Post

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.TEST_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='user')
        cls.group = Group.objects.create(
            title='заголовок',
            description='описание',
            slug='slug',
        )
        small_gif = (b'\x47\x49\x46\x38\x39\x61\x02\x00'
                     b'\x01\x00\x80\x00\x00\x00\x00\x00'
                     b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
                     b'\x00\x00\x00\x2C\x00\x00\x00\x00'
                     b'\x02\x00\x01\x00\x00\x02\x02\x0C'
                     b'\x0A\x00\x3B')
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            text='текст',
            author=cls.user,
            group=cls.group,
            image=uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def context_attributes(self, post):
        """Функция с проверки атрибутов контекста"""
        with self.subTest(post=post):
            self.assertEqual(post.text, self.post.text)
            self.assertEqual(post.author, self.post.author)
            self.assertEqual(post.group.id, self.post.group.id)
            self.assertEqual(post.image, self.post.image)

    def test_forms_show_correct_context(self):
        """Проверка коректности формы post_create/edit."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        response_2 = self.authorized_client.get(
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.id})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)
                form_field_2 = response_2.context['form'].fields[value]
                self.assertIsInstance(form_field_2, expected)

    def test_index_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.context_attributes(response.context['page_obj'][0])

    def test_group_list_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:posts',
                    kwargs={'slug': 'slug'})
        )
        self.assertEqual(response.context['group'], self.group)
        self.context_attributes(response.context['page_obj'][0])

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_detail',
                    kwargs={'post_id': self.post.id})
        )
        self.context_attributes(response.context['post'])

    def test_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:profile',
                    kwargs={'username': self.user})
        )
        self.assertEqual(response.context['author'], self.user)
        self.context_attributes(response.context['page_obj'][0])

    def test_signup_forms_show_correct_context(self):
        """Проверка коректности формы signup."""
        response = self.authorized_client.get(reverse('users:signup'))
        form_fields = {
            'first_name': forms.fields.CharField,
            'last_name': forms.fields.CharField,
            'username': forms.fields.CharField,
            'email': forms.fields.EmailField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
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
        first_page_post = (1, 10)
        second_page_post = (2, 3)
        page_post = [first_page_post,
                     second_page_post]
        urls = [
            reverse('posts:index'),
            reverse('posts:posts',
                    kwargs={'slug': self.group.slug}),
            reverse('posts:profile',
                    kwargs={'username': self.user}),
        ]
        for test_page in urls:
            with self.subTest(test_page=test_page):
                for page, count in page_post:
                    response = self.authorized_client.get(
                        test_page, {'page': page})
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
