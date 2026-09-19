from django.urls import include, path
from wagtail import hooks


@hooks.register("register_admin_urls")
def register_admin_urls():
    return [path("jev/", include("wagtail_jev.urls", namespace="wagtail_jev"))]
