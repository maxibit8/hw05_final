from django.test import TestCase

from ..models import User, Comment, Follow, Group, Post


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='user')
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
        )

    def test_post_str(self):
        """Проверка __str__ у post."""
        self.assertEqual(self.post.text, str(self.post))

    def test_post_verbose_name(self):
        """Проверка verbose_name у post."""
        field_verboses = {
            'text': 'Текст поста',
            'pub_date': 'Дата публикации',
            'author': 'Автор',
            'group': 'Группа',
        }
        for value, expected in field_verboses.items():
            with self.subTest(value=value):
                verbose_name = self.post._meta.get_field(value).verbose_name
                self.assertEqual(verbose_name, expected)

    def test_post_help_text(self):
        """Проверка help_text у post."""
        feild_help_texts = {
            'text': 'Введите текст поста',
            'group': 'Группа, к которой будет относиться пост',
        }
        for value, expected in feild_help_texts.items():
            with self.subTest(value=value):
                help_text = self.post._meta.get_field(value).help_text
                self.assertEqual(help_text, expected)


class GroupModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='user')
        cls.group = Group.objects.create(
            title='группа',
            description='описание',
        )

    def test_group_str(self):
        """Проверка __str__ у group."""
        self.assertEqual(self.group.title, str(self.group))


class CommentModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='user')
        cls.post = Post.objects.create(
            text='текст',
            author=cls.user,
        )
        cls.comment = Comment.objects.create(
            text='комментарий',
            author=cls.user,
            post=cls.post
        )

    def test_comment_str(self):
        """Проверка __str__ у comment."""
        self.assertEqual(self.comment.text, str(self.comment))

    def test_comment_verbose_name(self):
        """Проверка verbose_name у comment."""
        field_verboses = {
            'post': 'Комментарий',
            'author': 'Автор',
            'text': 'Текст комментария',
            'created': 'Дата комментария'
        }
        for value, expected in field_verboses.items():
            with self.subTest(value=value):
                verbose_name = self.comment._meta.get_field(value).verbose_name
                self.assertEqual(verbose_name, expected)


class FollowModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='user1')
        cls.author = User.objects.create_user(username='user2')
        cls.follow = Follow.objects.create(
            user=cls.user,
            author=cls.author,
        )

    def test_follow_verbose_name(self):
        """Проверка verbose_name у follow."""
        field_verboses = {
            'user': 'Пользователь',
            'author': 'Автор',
        }
        for value, expected in field_verboses.items():
            with self.subTest(value=value):
                verbose_name = self.follow._meta.get_field(value).verbose_name
                self.assertEqual(verbose_name, expected)
