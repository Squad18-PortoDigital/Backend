from rest_framework.permissions import BasePermission, SAFE_METHODS

def get_user_nivel(user):
    """
    Retorna o nível do perfil vinculado ao usuário, ou None se não tiver perfil.
    """
    if hasattr(user, 'perfil_legacy') and hasattr(user.perfil_legacy, 'perfil'):
        return user.perfil_legacy.perfil.nivel
    return None


class IsAdmin(BasePermission):
    """
    Permite acesso apenas a usuários com perfil admin.
    """
    def has_permission(self, request, view):
        return get_user_nivel(request.user) == 'admin' or request.user.is_superuser


class IsInstrutor(BasePermission):
    """
    Permite acesso apenas a usuários com perfil instrutor.
    """
    def has_permission(self, request, view):
        return get_user_nivel(request.user) == 'instrutor'


class IsAluno(BasePermission):
    """
    Permite acesso apenas a usuários com perfil aluno.
    """
    def has_permission(self, request, view):
        return get_user_nivel(request.user) == 'aluno'


class IsAdminOrInstrutor(BasePermission):
    """
    Permite acesso a admins ou instrutores.
    """
    def has_permission(self, request, view):
        nivel = get_user_nivel(request.user)
        return nivel in ['admin', 'instrutor'] or request.user.is_superuser


class IsAdminOrReadOnly(BasePermission):
    """
    Apenas admins podem editar, outros só leitura (GET, HEAD, OPTIONS).
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return get_user_nivel(request.user) == 'admin' or request.user.is_superuser
