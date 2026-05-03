from django.urls import path

from .views import (
    login_view,
    logout_view,
    role_redirect,
    signup_view,
    update_user,
    otp_verify,
    resend_otp,
)

urlpatterns = [
    path("login/", login_view, name="login"),
    path("signup/", signup_view, name="signup"),
    path("redirect/", role_redirect, name="role_redirect"),
    path("logout/", logout_view, name="logout"),
    path("control-panel/users/<int:user_id>/", update_user, name="control_panel_update_user"),
    path("otp/verify/", otp_verify, name="otp_verify"),
    path("otp/resend/", resend_otp, name="resend_otp"),
]
