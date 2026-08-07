"""Public API / admin URLConf for ``SERVICE_TYPE=api``."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("api.urls")),
]
