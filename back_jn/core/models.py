from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserManager(BaseUserManager):
    def create_user(self, username, email, cpf, password=None):
        if not email:
            raise ValueError("O email é obrigatório")
        if not cpf:
            raise ValueError("O CPF é obrigatório")
        
        user = self.model(username=username, email=self.normalize_email(email), cpf=cpf)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, cpf, password):
        user = self.create_user(username, email, cpf, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    cpf = models.CharField(max_length=14, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'  # Login será pelo email
    REQUIRED_FIELDS = ['username', 'cpf']

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
