import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..forms import PostForm
from ..models import User, Comment, Group, Post

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.TEST_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='user')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test_slug',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
        )
        cls.form = PostForm()
        cache.clear()
        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_authorized_client_post_create(self):
        """Проверка post_create авторизированным клиентом."""
        post_count = Post.objects.count()
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
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:profile',
                    kwargs={'username': self.user})
        )
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                group=form_data['group'],
                author=self.user,
                image='posts/small.gif'
            ).exists()
        )

    def test_authorized_authorized_client_post_edit(self):
        """Проверка post_edit автором."""
        self.group_2 = Group.objects.create(
            title='группа_2',
            slug='slug_2',
            description='Тестовое описание_2')
        form_data = {
            'text': 'отредактированый текст',
            'group': self.group_2.id,
        }
        response = self.authorized_client.post(
            reverse(
                'posts:post_edit',
                args=[self.post.id]),
            data=form_data,
            follow=True
        )
        old_group_response = self.authorized_client.get(
            reverse('posts:posts', args=(self.group.slug,))
        )
        new_group_response = self.authorized_client.get(
            reverse('posts:posts', args=(self.group_2.slug,)))
        self.assertRedirects(
            response,
            reverse('posts:post_detail',
                    kwargs={'post_id': self.post.id})
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                group=form_data['group'],
                author=self.user
            ).exists()
        )
        self.assertEqual(
            new_group_response.context['page_obj'].paginator.count, 1)
        self.assertEqual(
            old_group_response.context['page_obj'].paginator.count, 0)

    def test_guest_client_post_create(self):
        """Проверка post_create гостем."""
        post_count = Post.objects.count()
        form_data = {
            'text': 'Текст поста',
            'group': self.group.id,
        }
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        redirect = reverse('login') + '?next=' + reverse(
            'posts:post_create')
        last_post = Post.objects.last()
        self.assertEqual(last_post.author, self.user)
        self.assertEqual(last_post.group, self.group)
        self.assertEqual(Post.objects.count(), post_count)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(
            response, redirect)

    def test_authorized_client_add_comment(self):
        """Проверка add_comment авторизованным пользователем"""
        form_data = {
            'text': 'Тестовый коммент'
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', args=[self.post.id]),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail',
                    kwargs={'post_id': self.post.id})
        )
        new_comment = Comment.objects.last()
        self.assertEqual(new_comment.author, self.user)
        self.assertEqual(new_comment.post, self.post)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(
            Comment.objects.filter(
                text=form_data['text'],
                author=self.user
            ).exists()
        )

    def test_guest_client_add_comment(self):
        """Проверка add_comment гостем."""
        comment_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовый коммент',
        }
        response = self.guest_client.post(
            reverse('posts:add_comment', args=[self.post.id]),
            data=form_data,
            follow=True
        )
        redirect = reverse('login') + '?next=' + reverse(
            'posts:add_comment', args=[self.post.id])
        self.assertEqual(Comment.objects.count(), comment_count)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(response, redirect)
