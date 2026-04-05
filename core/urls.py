from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    UserViewSet, FinancialRecordViewSet, DashboardSummaryView, 
    LoginAPIView, RequestPasswordResetAPIView, ResetPasswordAPIView,
    SignupAPIView, VerifyOTPAPIView, ResendOTPAPIView
)
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'records', FinancialRecordViewSet)

urlpatterns = [
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('', include(router.urls)),
    path('auth/signup/', SignupAPIView.as_view(), name='signup'),
    path('auth/verify-otp/', VerifyOTPAPIView.as_view(), name='verify_otp'),
    path('auth/resend-otp/', ResendOTPAPIView.as_view(), name='resend_otp'),
    path('auth/login/', LoginAPIView.as_view(), name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/password-reset/', RequestPasswordResetAPIView.as_view(), name='password_reset_request'),
    path('auth/password-reset-confirm/', ResetPasswordAPIView.as_view(), name='password_reset_confirm'),
    path('dashboard/summary/', DashboardSummaryView.as_view(), name='dashboard_summary'),
]
