import boto3
import time
import uuid
import requests
from openai import OpenAI
from django.conf import settings
from datetime import datetime
from .models import UsuarioTrilha, Modulo, ModuloVideo, Video, Vizualizado, AvancoVideo
from django.db.models import Sum
from django.utils.timezone import now
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.colors import black, HexColor
from reportlab.platypus import Paragraph, Frame
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from django.http import FileResponse
from io import BytesIO


def upload_video_to_s3(file, filename):
    s3 = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION_NAME
    )
    s3.upload_fileobj(
        file,
        settings.AWS_STORAGE_BUCKET_NAME,
        filename,
        ExtraArgs={'ContentType': file.content_type}
    )
    return f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{filename}"


def start_transcription_job(media_url):
    transcribe = boto3.client(
        'transcribe',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION_NAME
    )

    job_name = f"transcricao-{uuid.uuid4()}"

    transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': media_url},
        MediaFormat='mp4',
        LanguageCode='pt-BR'
    )

    while True:
        job = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        status = job['TranscriptionJob']['TranscriptionJobStatus']
        if status in ['COMPLETED', 'FAILED']:
            break
        time.sleep(5)

    if status == 'COMPLETED':
        transcript_url = job['TranscriptionJob']['Transcript']['TranscriptFileUri']
        response = requests.get(transcript_url)
        return response.json()
    else:
        return None
    

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def generate_quiz_gpt(transcricao: str) -> str:
    prompt = f"""
Gere 5 perguntas de múltipla escolha sobre o seguinte conteúdo:

{transcricao}

Formato esperado (JSON):

[
  {{
    "pergunta": "string",
    "alternativas": ["a", "b", "c", "d"],
    "correta": "a"
  }},
  ...
]

Responda **somente** com um JSON válido. **Não adicione explicações, títulos, comentários ou texto fora do JSON.**
"""

    response = client.chat.completions.create(
        model="gpt-4o",  # ou "gpt-3.5-turbo", "gpt-4", "gpt-4o-mini" se disponível
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.5
    )

    return response.choices[0].message.content.strip()

def montar_dados_certificado(usuario):
    usuario_trilha = UsuarioTrilha.objects.filter(id_usuario=usuario).first()
    if not usuario_trilha:
        return None

    trilha = usuario_trilha.id_trilha

    nome_curso = trilha.titulo

    nome_aluno = usuario.nome

    modulos_ids = Modulo.objects.filter(id_trilha=trilha.id).values_list('id', flat=True)
    videos_ids = ModuloVideo.objects.filter(id_modulo__in=modulos_ids).values_list('id_video', flat=True)
    carga_horaria = Video.objects.filter(id__in=videos_ids).aggregate(total=Sum('duracao'))['total'] or 0

    data_inicio = Vizualizado.objects.filter(id_usuario=usuario).order_by('created_at').first()
    data_inicio = data_inicio.created_at if data_inicio else None

    data_fim = now()

    return {
        'nome_aluno': nome_aluno,
        'nome_curso': nome_curso,
        'carga_horaria': f"{carga_horaria} horas",
        'data_inicio': data_inicio.strftime('%d/%m/%Y') if data_inicio else "N/A",
        'data_fim': data_fim.strftime('%d/%m/%Y')
    }

def usuario_concluiu_trilha(usuario, trilha):
    modulos_ids = Modulo.objects.filter(trilha=trilha).values_list('id', flat=True)
    videos_ids = ModuloVideo.objects.filter(modulo__in=modulos_ids).values_list('video', flat=True)

    finalizados = AvancoVideo.objects.filter(usuario=usuario, video__in=videos_ids, finalizado=True).count()
    total_videos = len(videos_ids)

    return finalizados == total_videos


def gerar_certificado(nome_aluno, nome_curso, carga_horaria, data_inicio, data_conclusão):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)

    c.setFillColor(HexColor("#efede9"))
    c.rect(0, 0, width, height, fill=1, stroke=0)

    c.setLineWidth(15)
    c.setStrokeColor(HexColor("#85211d"))
    c.rect(40, 20, width - 80, height - 45, fill=0, stroke=1)

    c.setLineWidth(7)
    c.setStrokeColor(HexColor("#85211d"))
    c.rect(60, 40, width - 120, height - 90, fill=0, stroke=1)

    c.setLineWidth(2)
    c.setStrokeColor(HexColor("#85211d"))
    c.rect(69, 50, width - 140, height - 110, fill=0, stroke=1)

    estilo_Certificado_Conclusao = ParagraphStyle(
        name = "Título de conclusão",
        fontName="Helvetica-Bold",
        fontSize = 35,
        alignment = TA_CENTER,
        textColor = HexColor("#85211d")
    )

    Titulo1 = "Certificado de Conclusão".upper()
    paragrafo_conclusao = Paragraph(Titulo1, estilo_Certificado_Conclusao)
    frame_Titulo = Frame(x1= width / 2 - 420, y1= height/2 + 125, width=width, height=50)
    frame_Titulo.addFromList([paragrafo_conclusao], c)

    estilo_texto_afirmacao = ParagraphStyle(
        name = "Texto de afirmação",
        fontName="Helvetica",
        fontSize = 20,
        alignment = TA_CENTER,
    )

    Texto1 = "Certificamos que"
    paragrafo_texto_afirmacao = Paragraph(Texto1, estilo_texto_afirmacao)
    frame_Titulo = Frame(x1= width / 2 - 420, y1= height/2 + 65, width=width, height=50)
    frame_Titulo.addFromList([paragrafo_texto_afirmacao], c)

    estilo_nome_aluno_curso = ParagraphStyle(
        name = "Nome do aluno",
        fontName="Helvetica-Bold",
        fontSize = 35,
        alignment = TA_CENTER,
    )

    paragrafo_nome_aluno = Paragraph(nome_aluno, estilo_nome_aluno_curso)
    frame_Titulo = Frame(x1= width / 2 - 420, y1= height/2 + 35, width=width, height=50, bottomPadding=15)
    frame_Titulo.addFromList([paragrafo_nome_aluno], c)

    texto2 = "concluiu com êxito o curso"
    paragrafo_texto_afirmacao2 = Paragraph(texto2, estilo_texto_afirmacao)
    frame_Titulo = Frame(x1= width / 2 - 420, y1= height/2 - 5, width=width, height=50, topPadding=15, bottomPadding=15)
    frame_Titulo.addFromList([paragrafo_texto_afirmacao2], c)

    paragrafo_nome_curso = Paragraph(nome_curso, estilo_nome_aluno_curso)
    frame_Titulo = Frame(x1= width / 2 - 420, y1= height/2 - 35, width=width, height=50, topPadding=15)
    frame_Titulo.addFromList([paragrafo_nome_curso], c)

    estilo_justificado = ParagraphStyle(
    name="Justificado",
    fontName="Helvetica",
    fontSize=16,
    leading=16,
    alignment=TA_JUSTIFY
)
    
    texto3 = (
    f"Promovido por Jotanunes Construtora, com carga horária de {carga_horaria}. "
    f"Durante o período de {data_inicio} a {data_conclusão}, foram abordados conteúdos fundamentais para o "
    f"desenvolvimento na área de {nome_curso}.")
    paragrafo = Paragraph(texto3, estilo_justificado)
    frame_descricao = Frame(x1=100, y1=height/2 - 130, width=width - 200, height=80, showBoundary=0)
    frame_descricao.addFromList([paragrafo], c)

    texto4 = (
    "Este certificado é conferido em reconhecimento à "
    "<br/> dedicação e ao cumprimento dos requisitos estabelecidos.")
    paragrafo2 = Paragraph(texto4, estilo_justificado)
    frame2 = Frame(x1= 100, y1=height/2 - 220, width=width - 200, height=80, showBoundary=0)
    frame2.addFromList([paragrafo2], c)

    c.save()

    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"{nome_aluno}_{nome_curso}.pdf")