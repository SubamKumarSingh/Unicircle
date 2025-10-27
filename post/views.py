import asyncio
import os
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.templatetags.static import static
from django.http import JsonResponse
from django.urls import reverse
from .models import Post, Comment, Like
from .forms import CommentForm, PostForm
from django.views.decorators.csrf import csrf_exempt
import json
from google import genai
from dotenv import load_dotenv

load_dotenv()  # load GEMINI_API_KEY
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)
  # your Gemini API key

@login_required
def create_post(request):
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            new_post = form.save(commit=False)
            new_post.author = request.user
            new_post.save()

            profile = new_post.author.profile
            if profile.profile_picture and profile.profile_picture.name:  # safe check
                picture_url = profile.profile_picture.url
            else:
                picture_url = static("images/default_avatar.jpg")
            return JsonResponse({
                "id": new_post.id,
                "author": new_post.author.username,
                "content": new_post.content,
                "created_at": new_post.created_at.strftime("%Y-%m-%d %H:%M"),
                "image": new_post.image.url if new_post.image else None,
                "author_picture": picture_url,

                "user_type": new_post.author.user_type,
                "delete_post_url": reverse("post:delete_post", args=[new_post.id]),
                "create_comment_url": reverse("post:comment_post", args=[new_post.id]),
                "like_post_url": reverse("post:like_post", args=[new_post.id]),
               

            })
        else:
            # Return form errors as JSON
            errors = {field: error.get_json_data() for field, error in form.errors.items()}
            return JsonResponse({"errors": errors}, status=400)
    return JsonResponse({"error": "Invalid request method"}, status=400)


@csrf_exempt
def generate_ai_post(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        data = json.loads(request.body.decode())
    except Exception:
        data = request.POST.dict()
    prompt = data.get("prompt") or data.get("content_instruction") or ""
    add = "In not more than 300 words"
    prompt = f"{prompt}, {add}"
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )
    output_text = response.text
    print(output_text)

    return JsonResponse({"generated_text": output_text})

@login_required
def like_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    like, created = Like.objects.get_or_create(user=request.user, post=post)
    if not created:
        like.delete()
        liked = False
    else:
        liked = True

    return JsonResponse({
        "likes": post.likes.count(),
        "liked": liked
    })


@login_required
def comment_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
        return JsonResponse({
            "id": comment.id,
            "author": comment.author.username,
            "content": comment.content,
             "delete_comment_url": reverse("post:delete_comment", args=[comment.id]),
        })
    return JsonResponse({"errors": form.errors}, status=400)


@login_required
def delete_post(request, pk):
    post = get_object_or_404(Post, pk=pk, author=request.user)
    post.delete()
    return JsonResponse({"deleted": True, "post_id": pk})


def admin_del_post(request,pk):
    post = get_object_or_404(Post,pk = pk)
    post.delete()
    return redirect("unicircleapp:admin_allusers_page")

@login_required
def delete_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk, author=request.user)
    comment.delete()
    return JsonResponse({"deleted": True, "comment_id": pk})


def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    return render(request, "post/post_detail.html", {"post": post})


def post_list(request):
    posts = Post.objects.all().order_by("-created_at")
    return render(request, "post/post_list.html", {"posts": posts})
