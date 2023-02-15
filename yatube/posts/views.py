from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.cache import cache_page
from django.urls import reverse
from yatube.settings import POSTS_LIMIT

from .models import Follow, Post, Group, User
from .forms import PostForm, CommentForm
from .utils import create_paginator


@cache_page(20, key_prefix="index_page")
def index(request):
    posts = Post.objects.all()
    page_obj = create_paginator(request, posts, POSTS_LIMIT)
    return render(request, 'posts/index.html', {'page_obj': page_obj})


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    page_obj = create_paginator(request, posts, POSTS_LIMIT)
    return render(request, 'posts/group_list.html', {
        'page_obj': page_obj, 'group': group})


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts = author.posts.all()
    page_obj = create_paginator(request, posts, POSTS_LIMIT)
    if request.user.is_authenticated:
        following = Follow.objects.filter(
            user=request.user, author=author
        ).exists()

    else:
        following = False
    return render(request, 'posts/profile.html',
                  {'author': author,
                   'page_obj': page_obj,
                   'following': following})


def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    comments = post.comments.all()

    return render(request, 'posts/post_detail.html',
                  {'post': post,
                   'form': form,
                   'comments': comments})


@login_required
def post_create(request):
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
    )
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', request.user.username)
    form = PostForm()
    return render(request, 'posts/post_create.html', {
        'form': form,
    })


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post_id=post_id, )
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id)
    else:
        return render(request, 'posts/post_create.html', {
            'post': post,
            'is_edit': True,
            'form': form,
        })


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    post_list = Post.objects.filter(author__following__user=request.user)
    page_obj = create_paginator(request, post_list, POSTS_LIMIT)
    return render(request, 'posts/follow.html', {'page_obj': page_obj})


@login_required
def profile_follow(request, username):
    user = request.user
    author = User.objects.get(username=username)
    is_follower = Follow.objects.filter(user=user, author=author)
    if user != author and not is_follower.exists():
        Follow.objects.create(user=user, author=author)
    return redirect(reverse('posts:profile', args=[username]))


@login_required
def profile_unfollow(request, username):
    unfollow_author = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user, author=unfollow_author).delete()
    return redirect("posts:profile", username=username)
