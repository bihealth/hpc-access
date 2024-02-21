from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import include, path
from django.views import defaults as default_views
from django.views.generic.base import TemplateView
from sentry_sdk import last_event_id

from usersec import views


def handler500(request, *args, **argv):
    if request.user and "User" in str(type(request.user)):
        return render(
            request,
            "500.html",
            {"sentry_event_id": last_event_id()},
            status=500,
        )
    else:
        return HttpResponse(status=500)


urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    # UserSec URLs
    path("usersec/", include("usersec.urls", namespace="usersec")),
    path("adminsec/", include("adminsec.urls", namespace="adminsec")),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    path("users/", include("hpcaccess.users.urls", namespace="users")),
    path("accounts/", include("allauth.urls")),
    # Your stuff: custom urls includes go here
    # Login and logout
    path(
        r"login/",
        auth_views.LoginView.as_view(template_name="pages/login.html"),
        name="login",
    ),
    path(r"logout/", auth_views.logout_then_login, name="logout"),
    path("impersonate/", include("impersonate.urls")),
    path(
        "admin_landing/",
        permission_required("", login_url="home")(
            TemplateView.as_view(template_name="pages/admin_landing.html")
        ),
        name="admin-landing",
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
