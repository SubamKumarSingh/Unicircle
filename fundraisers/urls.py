from django.urls import path
from . import views

app_name = "fundraisers"

urlpatterns = [
    path("", views.fundraiser_list, name="allfundraiserspage"),              # shows form + fundraisers
    path("<int:pk>/", views.fundraiser_detail, name="detail"),
    path("<int:pk>/donate/", views.donate_view, name="donate"),
    path("<int:pk>/close/", views.fundraiser_close, name="close"),
    path("<int:pk>/complete/", views.fundraiser_mark_completed, name="complete"),

    path("<int:pk>/create-checkout-session/", views.create_checkout_session, name="create_checkout_session"),
    # path("stripe-webhook/", views.stripe_webhook, name="stripe_webhook"),
]