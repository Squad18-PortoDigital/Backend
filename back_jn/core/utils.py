import boto3
import time
import uuid
import requests
from openai import OpenAI
from django.conf import settings
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable

from urllib.parse import urlparse, parse_qs

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



from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi

def extrair_video_id(link):
    parsed = urlparse(link)
    if 'youtube' in parsed.netloc and parsed.path == '/watch':
        return parse_qs(parsed.query).get('v', [None])[0]
    if 'youtu.be' in parsed.netloc:
        return parsed.path.strip('/').split('?')[0]
    if 'youtube' in parsed.netloc and parsed.path.startswith('/embed/'):
        return parsed.path.split('/embed/')[-1].split('?')[0]
    return None

def extrair_transcricao_automatica(video):
    video_id = extrair_video_id(video.link)
    if not video_id:
        raise ValueError("Link inválido do YouTube")

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['pt', 'pt-BR', 'en'])
        texto = " ".join([item['text'] for item in transcript])
        video.hql = texto
        video.save()
        return texto
    except Exception as e:
        raise Exception(f"Erro ao obter transcrição: {e}")




