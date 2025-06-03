from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet,
    PerfilViewSet,
    UsuarioPerfilViewSet,
    VideoViewSet,
    QuizViewSet,
    TrilhaViewSet,
    CursoViewSet,
    CursoVideoViewSet,
    UsuarioTrilhaViewSet,
    UploadVideoView,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import CustomTokenView


router = DefaultRouter()
router.register(r'usuarios', UserViewSet, basename='usuario')
router.register(r'perfis', PerfilViewSet, basename='perfil')
router.register(r'usuario-perfis', UsuarioPerfilViewSet, basename='usuario-perfil')
router.register(r'videos', VideoViewSet, basename='video')
router.register(r'quizzes', QuizViewSet, basename='quiz')
router.register(r'trilhas', TrilhaViewSet, basename='trilha')
router.register(r'cursos', CursoViewSet, basename='curso')
router.register(r'curso-videos', CursoVideoViewSet, basename='cursovideo')
router.register(r'usuario-trilhas', UsuarioTrilhaViewSet, basename='usuariotrilha')

urlpatterns = [
    path('', include(router.urls)),
    path('login/', CustomTokenView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('upload-video/', UploadVideoView.as_view(), name='upload-video'),
]
