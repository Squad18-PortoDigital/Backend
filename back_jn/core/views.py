from rest_framework import viewsets
from .models import User, Profile
from .serializers import UserSerializer, ProfileSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action in ['create', 'list', 'retrieve']:  # Permite listar usuários e ver detalhes sem login
            return [AllowAny()]
        return [IsAuthenticated()]

class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
