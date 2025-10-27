from django.urls import path
from . import views

app_name = "post"   # so we can use namespaced URLs like post:like

urlpatterns = [
    # Post actions

    path("create/", views.create_post, name="create_post"),
    path("generate_ai_post/", views.generate_ai_post, name="generate_ai_post"),
    path("like_post/<int:pk>/", views.like_post, name="like_post"),
    path("<int:pk>/comment/", views.comment_post, name="comment_post"),
    path("<int:pk>/delete/", views.delete_post, name="delete_post"),
    path("<int:pk>/admindelete/", views.admin_del_post, name="admin_delete_post"),

    # Optional: if you want full post details page later
    path("<int:pk>/", views.post_detail, name="post_detail"),

    path("comment/delete/<int:pk>/", views.delete_comment, name="delete_comment"),


    # Optional: if you want a dedicated list of all posts
    path("", views.post_list, name="post_list"),
]