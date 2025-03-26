from rest_framework import viewsets,permissions
from .models import User, Profile
from .serializers import UserSerializer, ProfileSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response

"""Usuario, perfil e permissões"""
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action in ['create', 'destroy', 'list']:
            return [permissions.IsAdminUser()]
        if self.action in ['retrieve', 'update', 'partial_update']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]

    from rest_framework.exceptions import PermissionDenied

    def update(self, request, *args, **kwargs):
        if not request.user.is_staff and int(kwargs['pk']) != request.user.id:
            raise PermissionDenied("Você só pode atualizar seus próprios dados.")
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not request.user.is_staff and int(kwargs['pk']) != request.user.id:
            raise PermissionDenied("Você só pode atualizar seus próprios dados.")
        return super().partial_update(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'], url_path='me', permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    

class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAdminUser]

    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied("Perfis não podem ser excluídos.")
    


