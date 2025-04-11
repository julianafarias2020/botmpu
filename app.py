from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv
import PyPDF2
from io import BytesIO
import unicodedata

# Inicializa o Flask
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Permite requisições de qualquer origem

# Carrega as variáveis de ambiente
load_dotenv()
CHATBASE_API_KEY = os.getenv("CHATBASE_API_KEY")
CHATBASE_CHATBOT_ID = os.getenv("CHATBASE_CHATBOT_ID")

# Verifica se as variáveis de ambiente estão definidas
if not CHATBASE_API_KEY or not CHATBASE_CHATBOT_ID:
    raise ValueError("CHATBASE_API_KEY ou CHATBASE_CHATBOT_ID não estão definidos nas variáveis de ambiente.")

# Configurações da API do Chatbase
CHATBASE_API_URL = "https://www.chatbase.co/api/v1/chat"
CHATBASE_HEADERS = {
    "Authorization": f"Bearer {CHATBASE_API_KEY}",
    "Content-Type": "application/json"
}

# Função para normalizar texto (remove caracteres inválidos)
def normalize_text(text):
    # Normaliza o texto para remover caracteres especiais e codificações inválidas
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    # Remove caracteres de controle
    return ''.join(char for char in text if char.isprintable())

# Função para dividir texto longo em partes menores
def split_text(text, max_length=500):
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400

    # Lê o conteúdo do arquivo
    try:
        if file.filename.endswith('.pdf'):
            # Processa PDF
            pdf_reader = PyPDF2.PdfReader(BytesIO(file.read()))
            file_content = ""
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    file_content += text + "\n"
                else:
                    file_content += "[Página sem texto legível]\n"
        elif file.filename.endswith('.txt'):
            # Processa TXT
            file_content = file.read().decode('utf-8')
        else:
            return jsonify({"error": "Formato de arquivo não suportado. Envie um arquivo .pdf ou .txt."}), 400
    except Exception as e:
        return jsonify({"error": f"Erro ao processar o arquivo: {str(e)}"}), 400

    # Normaliza o texto para remover caracteres inválidos
    file_content = normalize_text(file_content)

    # Divide o texto em partes menores para evitar limites de tamanho
    text_parts = split_text(file_content, max_length=500)
    bot_message = ""

    # Envia cada parte do texto como uma mensagem para o Chatbase
    for part in text_parts:
        payload = {
            "chatbotId": CHATBASE_CHATBOT_ID,
            "messages": [
                {"role": "user", "content": f"Analise o seguinte documento (parte):\n\n{part}"}
            ],
            "conversationId": request.form.get('conversationId', None)  # Mantém o contexto da conversa
        }
        try:
            response = requests.post(CHATBASE_API_URL, headers=CHATBASE_HEADERS, json=payload)
            response.raise_for_status()
            data = response.json()
            bot_message += data["response"] + "\n"
        except requests.exceptions.RequestException as e:
            error_message = f"Erro ao se comunicar com o Chatbase: {str(e)}"
            if response:
                error_message += f"\nResposta do Chatbase: {response.text}"
                error_message += f"\nPayload enviado: {payload}"
            return jsonify({"error": error_message}), 500

    return jsonify({"message": bot_message.strip()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
