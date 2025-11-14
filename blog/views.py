from django.shortcuts import render, get_object_or_404, redirect
from .models import BlogPost, BlogComment, BlogRating, BlogCategory
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, F
from urllib.parse import quote
from django.utils.html import strip_tags
from django.utils import timezone

def blog_list(request):
    categories = BlogCategory.objects.all()
    selected_slug = request.GET.get('category')
    posts = BlogPost.objects.filter(
        published_at__isnull=False,
        published_at__lte=timezone.now()
    ).order_by('-published_at')
    if selected_slug:
        posts = posts.filter(category__slug=selected_slug)
    return render(request, 'blog/blog_list.html', {
        'posts': posts,
        'categories': categories,
        'selected_slug': selected_slug,
    })

def blog_detail(request, slug):
    post = get_object_or_404(
        BlogPost,
        slug=slug,
        published_at__isnull=False,
        published_at__lte=timezone.now()
    )
    
    # Increment views
    BlogPost.objects.filter(pk=post.pk).update(views=F('views') + 1)
    post.refresh_from_db(fields=['views'])
    
    absolute_url = request.build_absolute_uri(request.path)
    image_url = request.build_absolute_uri(post.image.url) if getattr(post, "image", None) else ""

    # Previous and next posts (by created_at)
    prev_post = BlogPost.objects.filter(created_at__lt=post.created_at).order_by('-created_at').first()
    next_post = BlogPost.objects.filter(created_at__gt=post.created_at).order_by('created_at').first()


    # short description (match template truncation length if you want)
    share_desc = post.meta_description or strip_tags(post.content)[:200]

    # build plain text with real newlines, then URL-encode once
    share_text = f"{post.title}\n\n{share_desc}\n\n{absolute_url}"
    if image_url:
        share_text += f"\n\n{image_url}"

    share_text_encoded = quote(share_text)  # safe for inserting directly into href

    user_rating = None
    if request.user.is_authenticated:
        user_rating = BlogRating.objects.filter(post=post, user=request.user).first()

    agg = post.ratings.aggregate(avg=Avg('value'), cnt=Count('id'))
    avg_rating = agg['avg'] or 0
    rating_count = agg['cnt'] or 0
    avg_rounded = int(round(avg_rating))

    return render(request, 'blog/blog_detail.html', {
        'post': post,
        'user_rating': user_rating,
        'avg_rating': avg_rating,
        'avg_rounded': avg_rounded,
        'rating_count': rating_count,
        'absolute_url': absolute_url,
        'image_url': image_url,
        'share_text_encoded': share_text_encoded,
        'prev_post': prev_post,
        'next_post': next_post,
    })

@login_required
def rate_post(request, slug):
    post = get_object_or_404(BlogPost, slug=slug)
    value = int(request.POST.get('rating', 0))
    if 1 <= value <= 5:
        BlogRating.objects.update_or_create(post=post, user=request.user, defaults={'value': value})
    return redirect('blog_detail', slug=slug)

@login_required
def comment_post(request, slug):
    post = get_object_or_404(BlogPost, slug=slug)
    content = request.POST.get('content', '').strip()
    if content:
        BlogComment.objects.create(post=post, user=request.user, content=content)
    return redirect('blog_detail', slug=slug)
