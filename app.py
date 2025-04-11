from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv
import PyPDF2
from io import BytesIO

# Inicializa o Flask
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Permite requisições de qualquer origem

# Carrega as variáveis de ambiente
load_dotenv()
CHATBASE_API_KEY = os.getenv("CHATBASE_API_KEY")
CHATBASE_CHATBOT_ID = os.getenv("CHATBASE_CHATBOT_ID")

# Configurações da API do Chatbase
CHATBASE_API_URL = "https://www.chatbase.co/api/v1/chat"
CHATBASE_HEADERS = {
    "Authorization": f"Bearer {CHATBASE_API_KEY}",
    "Content-Type": "application/json"
}

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

    # Envia o conteúdo do arquivo como uma mensagem para o Chatbase
    try:
        response = requests.post(CHATBASE_API_URL, headers=CHATBASE_HEADERS, json={
            "chatbotId": CHATBASE_CHATBOT_ID,
            "messages": [
                {"role": "user", "content": f"Analise o seguinte documento:\n\n{file_content}"}
            ],
            "conversationId": request.form.get('conversationId', None)  # Mantém o contexto da conversa
        })
        response.raise_for_status()
        data = response.json()
        bot_message = data["response"]

        return jsonify({"message": bot_message})
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Erro ao se comunicar com o Chatbase: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)