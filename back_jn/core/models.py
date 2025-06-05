import sys
import uuid
from django.utils import timezone
from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta

# detecta se estamos rodando "manage.py test"
TESTING = 'test' in sys.argv

def generate_user_token():
    # usa uuid4 para gerar um token hexadecimal único
    return uuid.uuid4().hex

#
# ─── USUÁRIO (schema: usuario) ────────────────────────────────────────────
#
class UserManager(BaseUserManager):
    def create_user(self, matricula, password=None):
        if not matricula:
            raise ValueError("A matrícula é obrigatória")
        user = self.model(
            matricula=matricula,
            token=generate_user_token()
        )
        if password:
            user.set_password(password)
        user.is_active = True
        user.save(using=self._db)
        return user

    def create_superuser(self, matricula, password):
        user = self.create_user(matricula, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user



class User(AbstractBaseUser, PermissionsMixin):
    id          = models.AutoField(primary_key=True, db_column='id')
    matricula   = models.CharField(max_length=255, unique=True, db_column='matricula')
    nome = models.CharField(max_length=255, db_column='nome', null=True, blank=True)
    password    = models.TextField(db_column='senha')
    token       = models.CharField(
        max_length=64,
        default=generate_user_token,
        editable=False,
        db_column='token'
    )
    created_at  = models.DateTimeField(
        auto_now_add=True,
        db_column='createdat'
    )
    updated_at  = models.DateTimeField(
        auto_now=True,
        db_column='updatedat'
    )
    last_login  = models.DateTimeField(
        blank=True,
        null=True,
        db_column='last_login'
    )
    # Flags do PermissionsMixin:
    is_active   = models.BooleanField(default=True, db_column='is_active')
    is_staff    = models.BooleanField(default=False, db_column='is_staff')
    is_superuser= models.BooleanField(default=False, db_column='is_superuser')


    objects = UserManager()

    USERNAME_FIELD = 'matricula'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'usuarios' if TESTING else '"usuario"."usuarios"'
        managed  = TESTING

    def __str__(self):
        return self.matricula
    
LEVEL_CHOICES = [
    ('admin',     'Administrador'),
    ('instrutor', 'Instrutor'),
    ('aluno',     'Aluno'),
]

class Perfil(models.Model):
    id    = models.AutoField(primary_key=True, db_column='id')
    nivel = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        db_column='nivel'
    )
    area  = models.TextField(
        null=True,
        blank=True,
        db_column='area'
    )

    class Meta:
        db_table = 'perfis' if TESTING else '"usuario"."perfis"'
        managed  = TESTING

    def __str__(self):
        # mostra o label legível em vez do código
        return self.get_nivel_display()


class UsuarioPerfil(models.Model):
    id       = models.AutoField(primary_key=True, db_column='id')
    usuario  = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column='idusuario',
        related_name='perfil_legacy'
    )
    perfil   = models.ForeignKey(
        Perfil,
        on_delete=models.CASCADE,
        db_column='idperfil',
        related_name='vinculos'
    )

    class Meta:
        db_table = 'usuarioperfil' if TESTING else '"usuario"."usuarioperfil"'
        managed  = TESTING

    def __str__(self):
        return f"{self.usuario.matricula} → {self.perfil.get_nivel_display()}"

#@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def criar_usuario_perfil_legacy(sender, instance, created, **kwargs):
    if created:
        perfil_default = Perfil.objects.filter(nivel='aluno').first()

        if perfil_default:
            UsuarioPerfil.objects.create(usuario=instance, perfil=perfil_default)
        else:
            # Caso ainda não exista nenhum perfil aluno, cria um genérico
            perfil_default = Perfil.objects.create(nivel='aluno', area='')
            UsuarioPerfil.objects.create(usuario=instance, perfil=perfil_default)


#
# ─── APRENDIZAGEM (schema: aprendizagem) ────────────────────────────────────────
#
class Trilha(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    titulo     = models.TextField(db_column='titulo')
    created_at = models.DateTimeField(db_column='createdat')
    updated_at = models.DateTimeField(db_column='updatedat')
    criador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='criador'
    )

    @property
    def duracao_total(self):
        videos = VideoAprendizagem.objects.filter(cursos_video__curso__trilha=self).distinct()
        total = timedelta()
        for video in videos:
            if video.duracao:
                total += video.duracao
        return int(total.total_seconds() // 60)  # em minutos
    
    @property
    def jcoins(self):
        return self.duracao_total
    
    class Meta:
        db_table = 'trilhas' if TESTING else '"aprendizagem"."trilhas"'
        managed  = TESTING

    def __str__(self):
        return self.titulo


class Curso(models.Model):
    id         = models.AutoField(primary_key=True, db_column='id')
    titulo     = models.TextField(db_column='titulo')
    descricao  = models.TextField(db_column='descricao', blank=True, null=True)
    trilha     = models.ForeignKey(
        Trilha, on_delete=models.CASCADE,
        related_name='cursos', db_column='idtrilha'
    )
    created_at = models.DateTimeField(db_column='createdat')
    updated_at = models.DateTimeField(db_column='updatedat')

    class Meta:
        db_table = 'cursos' if TESTING else '"aprendizagem"."cursos"'
        managed  = TESTING

    def __str__(self):
        return f"{self.trilha.titulo} • {self.titulo}"


class VideoAprendizagem(models.Model):
    id          = models.AutoField(primary_key=True, db_column='id')
    titulo      = models.TextField(db_column='titulo')
    descricao   = models.TextField(db_column='descricao', blank=True, null=True)
    link        = models.TextField(db_column='link')
    legenda     = models.TextField(db_column='legenda', blank=True, null=True)
    duracao     = models.DurationField(db_column='duracao', blank=True, null=True)
    hql         = models.TextField(db_column='hql', blank=True, null=True)
    created_at  = models.DateTimeField(db_column='createdat')
    updated_at  = models.DateTimeField(db_column='updatedat')

    class Meta:
        db_table = 'videos' if TESTING else '"aprendizagem"."videos"'
        managed  = TESTING

    def __str__(self):
        return self.titulo


class QuizAprendizagem(models.Model):
    id         = models.IntegerField(primary_key=True, db_column='id')
    questions  = models.JSONField(db_column='questions')
    responses  = models.JSONField(db_column='responses')

    class Meta:
        db_table = 'quizzes' if TESTING else '"aprendizagem"."quizzes"'
        managed  = TESTING

    def __str__(self):
        return f"Quiz #{self.id}"


class CursoVideo(models.Model):
    id      = models.AutoField(primary_key=True, db_column='id')
    curso  = models.ForeignKey(
        Curso, on_delete=models.CASCADE,
        related_name='videos', db_column='idcurso'
    )
    video   = models.ForeignKey(
        VideoAprendizagem, on_delete=models.CASCADE,
        related_name='cursos_video', db_column='idvideo'
    )

    class Meta:
        db_table = 'cursovideo' if TESTING else '"aprendizagem"."cursovideo"'
        managed  = TESTING
        unique_together = (('curso', 'video'),)

    def __str__(self):
        return f"{self.curso.titulo} → {self.video.titulo}"


class UsuarioTrilhaAprendizagem(models.Model):
    id         = models.IntegerField(primary_key=True, db_column='id')
    usuario    = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='trilhas_usuario', db_column='idusuario'
    )
    trilha     = models.ForeignKey(
        Trilha, on_delete=models.CASCADE,
        related_name='usuarios_trilha', db_column='idtrilha'
    )
    inscrito_em = models.DateTimeField(db_column='inscritoem')

    class Meta:
        db_table = 'usuariotrilha' if TESTING else '"aprendizagem"."usuariotrilha"'
        managed  = TESTING
        unique_together = (('usuario', 'trilha'),)

    def __str__(self):
        return f"{self.usuario} inscrito em {self.trilha}"


#
# ─── CERTIFICADO (schema: certificado) ─────────────────────────────────────────
#
class Certificado(models.Model):
    id         = models.IntegerField(primary_key=True, db_column='id')
    token      = models.TextField(db_column='token')
    usuario    = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        db_column='idusuario'
    )
    created_at = models.DateTimeField(db_column='createdat')
    updated_at = models.DateTimeField(db_column='updatedat')

    class Meta:
        db_table = 'certificados' if TESTING else '"certificado"."certificados"'
        managed  = TESTING

    def __str__(self):
        return f"Certificado {self.id} de {self.usuario}"


#
# ─── GAMIFIC (schema: gamific) ────────────────────────────────────────────────
#
class ConquistaModule(models.Model):
    id         = models.IntegerField(primary_key=True, db_column='id')
    idcurso   = models.IntegerField(db_column='idcurso')
    pontuacao  = models.IntegerField(db_column='pontuacao')
    tipo       = models.TextField(db_column='tipo')
    descricao  = models.TextField(db_column='descricao')

    class Meta:
        db_table = 'conquistas_module' if TESTING else '"gamific"."conquistas_module"'
        managed  = TESTING


class ConquistaQuiz(models.Model):
    id         = models.IntegerField(primary_key=True, db_column='id')
    idquiz     = models.IntegerField(db_column='idquiz')
    pontuacao  = models.IntegerField(db_column='pontuacao')
    tipo       = models.TextField(db_column='tipo')
    descricao  = models.TextField(db_column='descricao')

    class Meta:
        db_table = 'conquistas_quiz' if TESTING else '"gamific"."conquistas_quiz"'
        managed  = TESTING


class ConquistaTrilha(models.Model):
    id         = models.IntegerField(primary_key=True, db_column='id')
    idtrilha   = models.IntegerField(db_column='idtrilha')
    pontuacao  = models.IntegerField(db_column='pontuacao')
    tipo       = models.TextField(db_column='tipo')
    descricao  = models.TextField(db_column='descricao')

    class Meta:
        db_table = 'conquistas_trilhas' if TESTING else '"gamific"."conquistas_trilhas"'
        managed  = TESTING


class Ponto(models.Model):
    id         = models.IntegerField(primary_key=True, db_column='id')
    idusuario  = models.IntegerField(db_column='idusuario')
    qtd        = models.IntegerField(db_column='qtd')

    class Meta:
        db_table = 'pontos' if TESTING else '"gamific"."pontos"'
        managed  = TESTING


#
# ─── PREMIOS (schema: premios) ────────────────────────────────────────────────
#
class Recompensa(models.Model):
    id         = models.IntegerField(primary_key=True, db_column='id')
    valor      = models.IntegerField(db_column='valor')
    descricao  = models.TextField(db_column='descricao')

    class Meta:
        db_table = 'recompensas' if TESTING else '"premios"."recompensas"'
        managed  = TESTING

    def __str__(self):
        return f"{self.descricao} ({self.valor})"


class Resgate(models.Model):
    id           = models.IntegerField(primary_key=True, db_column='id')
    idusuario    = models.IntegerField(db_column='idusuario')
    idrecompensa = models.IntegerField(db_column='idrecompensa')
    dataresgate  = models.DateTimeField(db_column='dataresgate')

    class Meta:
        db_table = 'resgates' if TESTING else '"premios"."resgates"'
        managed  = TESTING


#
# ─── PROGRESSO (schema: progresso) ────────────────────────────────────────────
#
class AvancoVideo(models.Model):
    idusuario    = models.IntegerField(db_column='idusuario')
    idvideo      = models.IntegerField(db_column='idvideo')
    momentoatual = models.DurationField(db_column='momentoatual')
    finalizado   = models.BooleanField(db_column='finalizado')

    class Meta:
        db_table = 'avancosvideo' if TESTING else '"progresso"."avancosvideo"'
        managed  = TESTING


class TentativaQuiz(models.Model):
    id            = models.IntegerField(primary_key=True, db_column='id')
    idusuario     = models.IntegerField(db_column='idusuario')
    idquiz        = models.IntegerField(db_column='idquiz')
    tentativaatual= models.IntegerField(db_column='tentativaatual')
    pontuacao     = models.DecimalField(max_digits=10, decimal_places=2, db_column='pontuacao')
    tempotentativa= models.DurationField(db_column='tempotentativa')

    class Meta:
        db_table = 'tentativasquizzes' if TESTING else '"progresso"."tentativasquizzes"'
        managed  = TESTING


class HistoricoTentativa(models.Model):
    id                = models.IntegerField(primary_key=True, db_column='id')
    idtentativaquiz   = models.IntegerField(db_column='idtentativaquiz')
    pontuacao         = models.DecimalField(max_digits=10, decimal_places=2, db_column='pontuacao')
    tempotentativa    = models.DurationField(db_column='tempotentativa')

    class Meta:
        db_table = 'historicotentativas' if TESTING else '"progresso"."historicotentativas"'
        managed  = TESTING


class Visualizado(models.Model):
    idusuario    = models.IntegerField(db_column='idusuario')
    idvideo      = models.IntegerField(db_column='idvideo')
    created_at   = models.DateTimeField(db_column='createdat')

    class Meta:
        db_table = 'visualizados' if TESTING else '"progresso"."visualizados"'
        managed  = TESTING