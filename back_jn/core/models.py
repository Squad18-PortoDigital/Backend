from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserManager(BaseUserManager):
    def create_user(self, username, matricula, password=None):
        if not matricula:
            raise ValueError("A matrícula é obrigatória")

        user = self.model(username=username, matricula=matricula)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, matricula, password):
        user = self.create_user(username, matricula, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=150, unique=True)
    matricula = models.CharField(max_length=20, unique=True)  # Matricula substituindo CPF/ Perguntar tamanho da matricula/ 
    email = models.EmailField(unique=True, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'matricula'  # Agora o login será pela matrícula
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.username




class Profile(models.Model):
    LEVEL_CHOICES = [
        ('admin', 'Administrador'),
        ('instrutor', 'Instrutor'),
        ('aluno', 'Aluno'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='aluno')
    area = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.level}"

# Criar automaticamente um perfil ao criar um usuário
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
