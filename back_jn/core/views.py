#TODO: Separar em arquivos diferentes essa view esta muito grande criar pasta views e separar em arquivos
from rest_framework import viewsets,permissions
from .models import User, Profile, Video, Quiz
from .serializers import UserSerializer, ProfileSerializer, VideoSerializer
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from .utils import upload_video_to_s3, start_transcription_job, generate_quiz_gpt
import json

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
    

#TODO: Adicionar permissões para que o token de usuario seja necessário para acessar os videos
#TODO: Mudar para async para melhorar performance??
class VideoViewSet(viewsets.ModelViewSet):
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(detail=True, methods=['get'], url_path='transcricao')
    def get_transcricao(self, request, pk=None):
        video = self.get_object()
        return Response(video.transcricao)
    
    @action(detail=True, methods=['get'], url_path='quiz')
    def get_quiz(self, request, pk=None):
        video = self.get_object()

        if not hasattr(video, 'quiz'):
            return Response({"erro": "Este vídeo ainda não possui quiz."}, status=404)

        return Response({
            "video_id": video.id,
            "titulo": video.titulo,
            "quiz": video.quiz.perguntas
        })
        
    @action(detail=True, methods=['post'], url_path='gerar-quiz')
    def gerar_quiz(self, request, pk=None):
        video = self.get_object()

        if not video.transcricao:
            return Response({"erro": "Vídeo ainda não possui transcrição."}, status=400)

        # Impedir duplicação
        if hasattr(video, 'quiz'):
            return Response({"erro": "Este vídeo já possui um quiz."}, status=400)

        try:
            quiz_raw = generate_quiz_gpt(
                video.transcricao['results']['transcripts'][0]['transcript']
            )
            #print("Resposta do GPT:", quiz_raw)
            try:
                # As vezes o gpt retorna o json como se fosse markdown tratando esse caso
                if quiz_raw.startswith("```"):
                    quiz_raw = quiz_raw.strip("`").strip()
                    if quiz_raw.startswith("json"):
                        quiz_raw = quiz_raw[4:].strip()
                quiz_json = json.loads(quiz_raw)
            except json.JSONDecodeError:
                return Response({"erro": "OpenAI não retornou um JSON válido", "raw": quiz_raw}, status=500)


        except Exception as e:
            return Response({"erro": f"Erro ao gerar quiz: {str(e)}"}, status=500)

        quiz = Quiz.objects.create(video=video, perguntas=quiz_json)

        return Response({
            "mensagem": "Quiz gerado com sucesso!",
            "quiz": quiz.perguntas
        }, status=201)
    

#TODO: implemnetar logica para que somente admins ou instrutores possam criar videos. Talvez seja interessante guardar o id de quem criou...
#TODO: discutir solucoes mais performaticas para a transcrição de videos, legendas e armazenamento no banco de dados
class UploadVideoView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        video = request.FILES.get('video')
        titulo = request.data.get('titulo', video.name)

        if not video:
            return Response({"error": "Arquivo não enviado."}, status=400)

        filename = f"videos/{video.name}"
        video_url = upload_video_to_s3(video, filename)

        transcricao_json = start_transcription_job(video_url)

        novo_video = Video.objects.create(
            titulo=titulo,
            link=video_url,
            transcricao=transcricao_json
        )

        return Response({
            "id": novo_video.id,
            "titulo": novo_video.titulo,
            "link": novo_video.link,
            "transcricao": transcricao_json['results']['transcripts'][0]['transcript'] if transcricao_json else "Falha na transcrição"
        })
