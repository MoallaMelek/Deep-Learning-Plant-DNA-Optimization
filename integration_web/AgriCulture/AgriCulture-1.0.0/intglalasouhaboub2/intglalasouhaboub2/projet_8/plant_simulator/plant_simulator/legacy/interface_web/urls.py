from django.urls import path

from interface_web.views import home

urlpatterns = [
    path("", home, name="home"),
]
