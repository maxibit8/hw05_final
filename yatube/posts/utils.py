from django.core.paginator import Paginator


def create_paginator(request, posts, POSTS_LIMIT):
    paginator = Paginator(posts, POSTS_LIMIT)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
