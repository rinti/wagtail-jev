from django.urls import path

from wagtail_jev import views

app_name = "wagtail_jev"

urlpatterns = [
    path("suggest/", views.suggest, name="suggest"),
    path("rate/", views.rate, name="rate"),
]
