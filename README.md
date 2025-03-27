# Plataforma de Treinamento JotaNunes

## 🏗️ Sobre o projeto

Este é o backend da **Plataforma de Treinamento JotaNunes**, desenvolvido com Django REST Framework, integrado com AWS e OpenAI para funcionalidades como:

- Upload e transcrição de vídeos
- Geração automática de quizzes com IA
- Autenticação via matrícula/senha com JWT
- Controle de usuários e perfis (admin, instrutor, aluno)

---

## 🚀 Requisitos

- Python 3.11+
- pip
- Git

---

## ⚙️ Instalação local

### 1. Clone o repositório

```bash
cd seu-projeto
```

### 2. Crie e ative o ambiente virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

---

## 🧱 Migrações e dados iniciais

### 1. Aplique as migrações

```bash
python manage.py migrate
```

### 2. Carregue os dados de exemplo

```bash
python manage.py loaddata initial_data.json
```

---

## 🧪 Testando a API

### 🔐 Autenticação

- Faça login com `POST /api/token/` usando matrícula e senha
- Copie o `access` token e use como Bearer Token

### 🔁 Endpoints úteis

| Recurso                        | Método | Endpoint                            |
|-------------------------------|--------|-------------------------------------|
| Login com matrícula e senha   | POST   | `/api/token/`                       |
| Ver usuário logado            | GET    | `/api/users/me/`                   |
| Criar usuário (admin)         | POST   | `/api/users/`                       |
| Atualizar próprio usuário     | PATCH  | `/api/users/<id>/`                 |
| Upload vídeo para S3          | POST   | `/api/upload-video/`               |
| Ver transcrição               | GET    | `/api/videos/<id>/transcricao/`    |
| Gerar quiz com IA (admin)     | POST   | `/api/videos/<id>/gerar-quiz/`     |
| Ver quiz                      | GET    | `/api/videos/<id>/quiz/`           |
| Criar perfil (admin)          | POST   | `/api/profiles/`                   |
| Listar perfis (admin)         | GET    | `/api/profiles/`                   |
| Atualizar perfil (admin)      | PATCH  | `/api/profiles/<id>/`              |
| Tentar excluir perfil         | DELETE | `/api/profiles/<id>/` (403 bloqueado) |


---

## 💡 Outros

- Usuários são criados pelo admin
- Login é feito com **matrícula e senha**

---

## 🤖 IA usada

- `AWS Transcribe` para extrair falas de vídeos
- `GPT-4o mini` da OpenAI para gerar quizzes