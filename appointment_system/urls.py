from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("admin-dashboard/", include("admin_dashboard.urls")),
    path(
        "control-panel/",
        RedirectView.as_view(url="/admin-dashboard/", permanent=False),
        name="control_panel",
    ),
    path("accounts/", include("accounts.urls")),
    path("organizer/", include("organizer.urls")),
    path("customer/", include("customer.urls")),
    path("login/", RedirectView.as_view(url="/accounts/login/", permanent=False)),
    path("signup/", RedirectView.as_view(url="/accounts/signup/", permanent=False)),
    path("", include("booking.urls")),
]
