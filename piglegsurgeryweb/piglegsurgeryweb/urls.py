"""piglegsurgeryweb URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

# from ..uploader import views

urlpatterns = [
    path(
        "uploader/",
        include(
            "uploader.urls"
            # , namespace="uploader"
        ),
    ),
    # path("", RedirectView.as_view(pattern_name='model_form_upload')),
    # path("", views.model_form_upload, name="model_form_upload"),
    path("admin/", admin.site.urls),
]

urlpatterns += staticfiles_urlpatterns()  # used for static files with gunicorn not for production
