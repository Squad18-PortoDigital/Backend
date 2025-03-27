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


class Video(models.Model):
    titulo = models.CharField(max_length=255)
    duracao = models.DurationField(blank=True, null=True)  # Você pode preencher depois
    link = models.URLField()  # URL do S3
    legenda = models.TextField(blank=True, null=True)
    transcricao = models.JSONField(blank=True, null=True)  # Transcrição completa da AWS
    id_quiz = models.IntegerField(blank=True, null=True)  # FK pode vir depois
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.titulo

#talvez o quiz pudesse ter o id da trilha pra facilitar geracao do quiz final
#mudei um pouco a estrutura  se o pessoal do banco n topar refaço

class Quiz(models.Model):
    video = models.OneToOneField(Video, on_delete=models.CASCADE, related_name="quiz")
    perguntas = models.JSONField()
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Quiz para: {self.video.titulo}"
