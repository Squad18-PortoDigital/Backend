from rest_framework import viewsets, permissions
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .permissions import IsAdmin, IsInstrutor, IsAluno, IsAdminOrInstrutor
from .permissions import IsAdminOrInstrutor  

from .models import (
    User,
    Perfil,
    UsuarioPerfil,
    VideoAprendizagem,
    QuizAprendizagem,
    Trilha,
    Curso,
    CursoVideo,
    UsuarioTrilhaAprendizagem,
)
from .serializers import (
    UserSerializer,
    PerfilSerializer,
    UsuarioPerfilSerializer,
    VideoAprendizagemSerializer,
    QuizAprendizagemSerializer,
    TrilhaSerializer,
    CursoSerializer,
    CursoVideoSerializer,
    UsuarioTrilhaAprendizagemSerializer,
    UserCreateSerializer
)
from .utils import upload_video_to_s3, start_transcription_job, generate_quiz_gpt, extrair_transcricao_automatica, obter_duracao_video_youtube, limpar_link_youtube
import json


# ----------------------------------------------------
#  autenticação
# ----------------------------------------------------


class CustomTokenSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        return super().get_token(user)

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user

        data['id_usuario'] = user.id
        data['nome'] = user.nome

        try:
            data['nivel'] = user.perfil_legacy.perfil.nivel
        except:
            data['nivel'] = None

        return data

class CustomTokenView(TokenObtainPairView):
    serializer_class = CustomTokenSerializer

# ----------------------------------------------------
# Usuário
# ----------------------------------------------------
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer


    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsAdminOrInstrutor()]
        if self.action in ['destroy', 'list']:
            return [permissions.IsAdminUser()]
        if self.action in ['retrieve', 'update', 'partial_update']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]


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



# ----------------------------------------------------
# Perfis (níveis e áreas)
# ----------------------------------------------------
class PerfilViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Apenas leitura de níveis/áreas disponíveis
    """
    queryset = Perfil.objects.all()
    serializer_class = PerfilSerializer
    permission_classes = [permissions.IsAdminUser]


# ----------------------------------------------------
# Vínculos usuário ↔ perfil legados
# ----------------------------------------------------
class UsuarioPerfilViewSet(viewsets.ModelViewSet):
    """
    Gerencia quem é ligado a qual Perfil legado.
    """
    queryset = UsuarioPerfil.objects.select_related('perfil').all()
    serializer_class = UsuarioPerfilSerializer
    permission_classes = [permissions.IsAdminUser]

    def destroy(self, request, *args, **kwargs):
        # Poderia impedir exclusão, se desejar:
        raise PermissionDenied("Não é permitido remover vínculos de perfil.")


# ----------------------------------------------------
# Vídeos, quizzes e upload
# ----------------------------------------------------
class VideoViewSet(viewsets.ModelViewSet):
    queryset = VideoAprendizagem.objects.all()
    serializer_class = VideoAprendizagemSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'gerar_quiz']:
            return [IsAuthenticated(), IsAdminOrInstrutor()]
        return [IsAuthenticatedOrReadOnly()]

    def perform_create(self, serializer):
        link = self.request.data.get('link')
        duracao = obter_duracao_video_youtube(link)
        print(f"[DEBUG] Duração obtida: {duracao}")
        serializer.save(duracao=duracao)


    @action(detail=True, methods=['get'], url_path='transcricao')
    def get_transcricao(self, request, pk=None):
        video = self.get_object()
        return Response(video.hql or {})

    @action(detail=True, methods=['get'], url_path='quiz')
    def get_quiz(self, request, pk=None):
        video = self.get_object()
        try:
            quiz = QuizAprendizagem.objects.get(id=video.id)
        except QuizAprendizagem.DoesNotExist:
            return Response({"erro": "Este vídeo ainda não possui quiz."}, status=404)
        return Response({
            "video_id": video.id,
            "titulo": video.titulo,
            "quiz": quiz.responses
        })

    @action(detail=True, methods=['post'], url_path='extrair-transcricao')
    def extrair_transcricao(self, request, pk=None):
        video = self.get_object()
        try:
            texto = extrair_transcricao_automatica(video)
            return Response({
                "mensagem": "Transcrição extraída com sucesso!",
                "transcricao": texto
            }, status=200)
        except Exception as e:
            return Response({"erro": str(e)}, status=500)

    @action(detail=True, methods=['post'], url_path='gerar-quiz')
    def gerar_quiz(self, request, pk=None):
        video = self.get_object()
        if not video.hql:
            return Response({"erro": "Vídeo ainda não possui HQL/transcrição."}, status=400)
        if QuizAprendizagem.objects.filter(id=video.id).exists():
            return Response({"erro": "Este vídeo já possui um quiz."}, status=400)

        try:
            quiz_raw = generate_quiz_gpt(video.hql)
            if quiz_raw.startswith("```"):
                quiz_raw = quiz_raw.strip("`").strip()
                if quiz_raw.startswith("json"):
                    quiz_raw = quiz_raw[4:].strip()
            quiz_json = json.loads(quiz_raw)
        except json.JSONDecodeError:
            return Response(
                {"erro": "OpenAI não retornou JSON válido", "raw": quiz_raw},
                status=500
            )
        except Exception as e:
            return Response(
                {"erro": f"Erro ao gerar quiz: {str(e)}"},
                status=500
            )

        if isinstance(quiz_json, dict):
            questions = quiz_json.get('questions', [])
            responses = quiz_json.get('responses', [])
        else:
            questions = quiz_json
            responses = quiz_json

        quiz = QuizAprendizagem.objects.create(
            id=video.id,
            questions=questions,
            responses=responses,
        )

        return Response({
            "mensagem": "Quiz gerado com sucesso!",
            "quiz": quiz.responses
        }, status=201)



class QuizViewSet(viewsets.ModelViewSet):
    queryset = QuizAprendizagem.objects.all()
    serializer_class = QuizAprendizagemSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdminOrInstrutor()]
        return [IsAuthenticatedOrReadOnly()]


class UploadVideoView(APIView):
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated, IsAdminOrInstrutor]

    def post(self, request):
        video_file = request.FILES.get('video')
        titulo     = request.data.get('titulo', getattr(video_file, 'name', None))

        if not video_file:
            return Response({"error": "Arquivo não enviado."}, status=400)

        filename         = f"videos/{video_file.name}"
        video_url        = upload_video_to_s3(video_file, filename)
        transcricao_json = start_transcription_job(video_url)

        novo_video = VideoAprendizagem.objects.create(
            id=None,  # deixamos o PK ser auto (ou especifique se for fixo)
            titulo=titulo,
            link=video_url,
            hql=transcricao_json.get('results', {}).get('transcripts', [{}])[0].get('transcript', ''),
            created_at=None,
            updated_at=None,
        )

        return Response({
            "id": novo_video.id,
            "titulo": novo_video.titulo,
            "link": novo_video.link,
            "transcricao": (
                transcricao_json['results']['transcripts'][0]['transcript']
                if transcricao_json else "Falha na transcrição"
            )
        })


# ----------------------------------------------------
# Trilhas e módulos
# ----------------------------------------------------
class TrilhaViewSet(viewsets.ModelViewSet):
    queryset = Trilha.objects.all()
    serializer_class = TrilhaSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdminOrInstrutor()]
        return [IsAuthenticatedOrReadOnly()]

    @action(detail=True, methods=['get'], url_path='cursos')
    def listar_cursos(self, request, pk=None):
        trilha = self.get_object()
        cursos = trilha.cursos.all()
        serializer = CursoSerializer(cursos, many=True)
        return Response(serializer.data)

class CursoViewSet(viewsets.ModelViewSet):
    queryset = Curso.objects.all()
    serializer_class = CursoSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdminOrInstrutor()]
        return [IsAuthenticatedOrReadOnly()]
    
    @action(detail=True, methods=['get'], url_path='videos')
    def listar_videos(self, request, pk=None):
        curso = self.get_object()
        # pega os vídeos reais ligados ao curso via relação intermediária
        videos = VideoAprendizagem.objects.filter(cursos_video__curso=curso)
        serializer = VideoAprendizagemSerializer(videos, many=True)
        return Response(serializer.data)




class CursoVideoViewSet(viewsets.ModelViewSet):
    queryset = CursoVideo.objects.all()
    serializer_class = CursoVideoSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdminOrInstrutor()]
        return [IsAuthenticatedOrReadOnly()]



class UsuarioTrilhaViewSet(viewsets.ModelViewSet):
    queryset = UsuarioTrilhaAprendizagem.objects.all()
    serializer_class = UsuarioTrilhaAprendizagemSerializer
    permission_classes = [IsAuthenticated]
