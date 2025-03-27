from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, ProfileViewSet, UploadVideoView, VideoViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')
router.register(r'profiles', ProfileViewSet, basename='profiles')
router.register(r'videos', VideoViewSet, basename='videos')

urlpatterns = [
    path('', include(router.urls)),  # Incluindo as rotas do DRF
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('upload-video/', UploadVideoView.as_view(), name='upload-video'),
]
    