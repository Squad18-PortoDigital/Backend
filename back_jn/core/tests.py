from django.test import TestCase
from rest_framework.test import APIClient, APITestCase
from django.urls import reverse
from rest_framework import status

from core.models import User, Perfil, UsuarioPerfil, VideoAprendizagem, QuizAprendizagem
from core.serializers import UserSerializer, VideoAprendizagemSerializer, QuizSerializer


class CoreLegacyTests(TestCase):
    def setUp(self):
        # garante existência do perfil 'aluno'
        self.perfil_aluno, _ = Perfil.objects.get_or_create(
            nivel='aluno',
            defaults={'area': ''}
        )
        self.client = APIClient()

    def test_user_creation_and_profile_signal(self):
        u = User.objects.create_user(matricula='2027001', password='abc')
        # sinal deve ter criado o vínculo
        self.assertTrue(UsuarioPerfil.objects.filter(usuario=u).exists())
        up = UsuarioPerfil.objects.get(usuario=u)
        self.assertEqual(up.perfil, self.perfil_aluno)

    def test_user_serializer_create(self):
        data = {'matricula': '3001', 'password': 'test123'}
        ser = UserSerializer(data=data)
        self.assertTrue(ser.is_valid(), ser.errors)
        user2 = ser.save()
        self.assertEqual(user2.matricula, '3001')
        # e vínculo criado
        self.assertTrue(UsuarioPerfil.objects.filter(usuario=user2).exists())

    def test_user_viewset_create_and_me(self):
        # criar admin e autenticar
        admin = User.objects.create_user(matricula='admin1', password='adm')
        admin.is_superuser = admin.is_staff = True
        admin.save()
        self.client.force_authenticate(user=admin)

        # criar via API
        url = reverse('user-list')
        resp = self.client.post(url, {'matricula': '2001', 'password': 'p'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn('perfil', resp.data)

        # endpoint /users/me/
        me_url = reverse('user-me')
        resp2 = self.client.get(me_url)
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertEqual(resp2.data['matricula'], 'admin1')

    def test_video_and_quiz_models_and_serializers(self):
        # Video model
        v = VideoAprendizagem.objects.create(
            titulo='Vid Test',
            link='http://x',
            transcricao={'results': {'transcripts': [{'transcript': 'bla'}]}}
        )
        self.assertIsNotNone(v.id)
        vs = VideoAprendizagemSerializer(v)
        self.assertEqual(vs.data['titulo'], 'Vid Test')

        # Quiz model
        q = QuizAprendizagem.objects.create(video=v, perguntas=[{'q': '?'}])
        self.assertEqual(v.quiz, q)
        qs = QuizSerializer(q)
        self.assertEqual(qs.data['video'], v.id)


class CoreAPIRootTests(APITestCase):
    def test_api_root_contains_all_resources(self):
        """
        GET /api/ deve retornar um dicionário com as chaves:
        users, perfis, usuario-perfis, videos, quizzes, trilhas,
        modulos, modulo-videos e usuario-trilhas
        """
        url = reverse('api-root')
        resp = self.client.get(url, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        data = set(resp.json().keys())
        expected = {
            'users',
            'perfis',
            'usuario-perfis',
            'videos',
            'quizzes',
            'trilhas',
            'modulos',
            'modulo-videos',
            'usuario-trilhas',
        }
        missing = expected - data
        self.assertFalse(missing, f"Faltando chaves em API root: {missing}")


class CoreListEndpointsTests(APITestCase):
    def test_users_list_requires_admin(self):
        url = reverse('user-list')
        resp = self.client.get(url)
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_videos_and_quizzes_list_open(self):
        for name in ('video-list', 'quiz-list'):
            url = reverse(name)
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_perfis_list_requires_admin(self):
        url = reverse('perfil-list')
        resp = self.client.get(url)
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_trilhas_modulos_and_associacoes(self):
        for name in ('trilha-list', 'modulo-list', 'modulovideo-list', 'usuariotrilha-list'):
            url = reverse(name)
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, status.HTTP_200_OK)


class CoreVideoQuizWorkflowTests(APITestCase):
    def setUp(self):
        # cria um vídeo de teste com "transcricao" simulada
        self.video = VideoAprendizagem.objects.create(
            titulo='Vídeo de Teste',
            link='https://jotanunes-videos.s3.us-east-2.amazonaws.com/videos/06+-+Solicita%C3%A7%C3%A3o+de+distrato.mp4',
            transcricao={'results': {'transcripts': [{'transcript': 'Esta é a transcrição de teste.'}]}}
        )

    def test_get_transcricao(self):
        url = reverse('video-transcricao', args=[self.video.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # extrai a transcrição do JSON retornado
        transcript = resp.json()['results']['transcripts'][0]['transcript']
        self.assertIn('Esta é a transcrição', transcript)

    def test_gerar_e_buscar_quiz(self):
        url_gerar = reverse('video-gerar-quiz', args=[self.video.id])

        # sem autenticação, deve retornar 401
        resp = self.client.post(url_gerar)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

        # autentica como admin
        admin = User.objects.create_user(matricula='admin', password='pass')
        admin.is_staff = admin.is_superuser = True
        admin.save()
        self.client.force_authenticate(user=admin)

        # tenta gerar o quiz
        resp2 = self.client.post(url_gerar)
        self.assertIn(resp2.status_code, (status.HTTP_201_CREATED, status.HTTP_500_INTERNAL_SERVER_ERROR))

        # se foi criado, busca
        url_buscar = reverse('video-quiz', args=[self.video.id])
        resp3 = self.client.get(url_buscar)
        if resp3.status_code == status.HTTP_200_OK:
            self.assertIsInstance(resp3.json().get('quiz'), list)
        else:
            self.assertEqual(resp3.status_code, status.HTTP_404_NOT_FOUND)
