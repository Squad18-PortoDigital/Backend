from rest_framework import serializers
from django.conf import settings
from .models import (
    User, Perfil, UsuarioPerfil,
    Trilha, Curso, VideoAprendizagem, QuizAprendizagem,
    CursoVideo, UsuarioTrilhaAprendizagem,
    Certificado,
    ConquistaModule, ConquistaQuiz, ConquistaTrilha, Ponto,
    Recompensa, Resgate,
    AvancoVideo, TentativaQuiz, HistoricoTentativa, Visualizado,
)

# ─── Usuário  ─────────────────────────────────────────────────────────────
class UserCreateSerializer(serializers.ModelSerializer):
    nivel = serializers.CharField(write_only=True)
    area = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['id', 'matricula', 'nome' ,'password', 'nivel', 'area']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        nivel = validated_data.pop('nivel')
        area = validated_data.pop('area', '')

        pwd = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(pwd)
        user.save()

        perfil, _ = Perfil.objects.get_or_create(nivel=nivel, area=area)
        UsuarioPerfil.objects.create(usuario=user, perfil=perfil)

        return user

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    nivel = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'matricula','nome', 'password', 'token',
            'nivel', 
            'is_active', 'is_staff', 'is_superuser',
            'last_login', 'created_at', 'updated_at',
        ]

    def create(self, validated_data):
        pwd = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(pwd)
        user.save()
        return user
    
    def get_nivel(self, obj):
        try:
            return obj.perfil_legacy.perfil.nivel
        except:
            return None

class PerfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Perfil
        fields = ['id', 'nivel', 'area']

class UsuarioPerfilSerializer(serializers.ModelSerializer):
    usuario = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    perfil = serializers.PrimaryKeyRelatedField(queryset=Perfil.objects.all())

    class Meta:
        model = UsuarioPerfil
        fields = ['id', 'usuario', 'perfil']

# ─── Vídeos e Quizzes  ────────────────────────────────────────────────────
class QuizSerializer(serializers.ModelSerializer):
    video = serializers.PrimaryKeyRelatedField(queryset=VideoAprendizagem.objects.all())

    class Meta:
        model = QuizAprendizagem
        fields = ['video', 'perguntas', 'criado_em']

# ─── Aprendizagem ───────────────────────────────────────────────────────────────
class TrilhaSerializer(serializers.ModelSerializer):
    duracao_total = serializers.SerializerMethodField()
    jcoins = serializers.SerializerMethodField()
    criador_nome = serializers.CharField(source='criador.nome', read_only=True)

    class Meta:
        model = Trilha
        fields = ['id', 'titulo', 'created_at', 'updated_at', 'criador', 'duracao_total', 'jcoins', 'criador_nome']

    def get_duracao_total(self, obj):
        return obj.duracao_total

    def get_jcoins(self, obj):
        return obj.jcoins


class CursoSerializer(serializers.ModelSerializer):
    trilha = TrilhaSerializer(read_only=True)
    idtrilha = serializers.PrimaryKeyRelatedField(write_only=True, source='trilha', queryset=Trilha.objects.all())

    class Meta:
        model = Curso
        fields = ['id', 'titulo', 'descricao', 'idtrilha', 'trilha', 'created_at', 'updated_at']

class VideoAprendizagemSerializer(serializers.ModelSerializer):
    curso_id = serializers.PrimaryKeyRelatedField(
        write_only=True, queryset=Curso.objects.all(), required=False
    )
    duracao = serializers.DurationField(read_only=True)

    class Meta:
        model = VideoAprendizagem
        fields = ['id', 'titulo', 'descricao', 'link', 'curso_id', 'duracao']
        read_only_fields = ['duracao']

    def create(self, validated_data):
        curso = validated_data.pop('curso_id', None)
        video = VideoAprendizagem.objects.create(**validated_data)
        if curso:
            CursoVideo.objects.create(curso=curso, video=video)
        return video
    
class QuizAprendizagemSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizAprendizagem
        fields = ['id', 'questions', 'responses']

class CursoVideoSerializer(serializers.ModelSerializer):
    curso = serializers.PrimaryKeyRelatedField(queryset=Curso.objects.all())
    video = serializers.PrimaryKeyRelatedField(queryset=VideoAprendizagem.objects.all())

    class Meta:
        model = CursoVideo
        fields = ['id', 'curso', 'video']

class UsuarioTrilhaAprendizagemSerializer(serializers.ModelSerializer):
    usuario = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    trilha = serializers.PrimaryKeyRelatedField(queryset=Trilha.objects.all())

    class Meta:
        model = UsuarioTrilhaAprendizagem
        fields = ['id', 'usuario', 'trilha', 'inscrito_em']

# ─── Certificado ────────────────────────────────────────────────────────────────
class CertificadoSerializer(serializers.ModelSerializer):
    usuario = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Certificado
        fields = ['id', 'token', 'usuario', 'created_at', 'updated_at']

# ─── Gamific ───────────────────────────────────────────────────────────────────
class ConquistaModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConquistaModule
        fields = ['id', 'idcurso', 'pontuacao', 'tipo', 'descricao']

class ConquistaQuizSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConquistaQuiz
        fields = ['id', 'idquiz', 'pontuacao', 'tipo', 'descricao']

class ConquistaTrilhaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConquistaTrilha
        fields = ['id', 'idtrilha', 'pontuacao', 'tipo', 'descricao']

class PontoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ponto
        fields = ['id', 'idusuario', 'qtd']

# ─── Prêmios ───────────────────────────────────────────────────────────────────
class RecompensaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recompensa
        fields = ['id', 'valor', 'descricao']

class ResgateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resgate
        fields = ['id', 'idusuario', 'idrecompensa', 'dataresgate']

# ─── Progresso ─────────────────────────────────────────────────────────────────
class AvancoVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvancoVideo
        fields = ['idusuario', 'idvideo', 'momentoatual', 'finalizado']

class TentativaQuizSerializer(serializers.ModelSerializer):
    class Meta:
        model = TentativaQuiz
        fields = ['id', 'idusuario', 'idquiz', 'tentativaatual', 'pontuacao', 'tempotentativa']

class HistoricoTentativaSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistoricoTentativa
        fields = ['id', 'idtentativaquiz', 'pontuacao', 'tempotentativa']

class VisualizadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visualizado
        fields = ['idusuario', 'idvideo', 'created_at']
