from flask import Flask, request, jsonify, render_template
from supabase import create_client
from datetime import datetime, timezone, timedelta
import threading
import time
import os

app = Flask(__name__)

supabase_url = 'https://xgzjguuqunjyurydwiyc.supabase.co'
supabase_key = os.getenv(
    'SUPABASE_KEY',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhnempndXVxdW5qeXVyeWR3aXljIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzgzODEwMDUsImV4cCI6MjA1Mzk1NzAwNX0.6cnkhfclCUq774qVLYq-FQA7As8mLzf7etTdREkWozQ'
)
supabase = create_client(supabase_url, supabase_key)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/avaliacao', methods=['GET'])
def renderizar_avaliacao():
    return render_template('avaliacao.html')

# Rota para receber a avaliação (requisição POST)
@app.route('/avaliacao', methods=['POST'])
def receber_avaliacao():
    # Recupera os dados enviados
    data = request.json
    nota = data.get("nota")

    # Verifica se a nota é válida
    if nota is None or not isinstance(nota, (int, float)) or not (1 <= nota <= 10):
        return jsonify({"erro": "Nota inválida"}), 400

    try:
        # Insere a avaliação na tabela 'avaliacao' do Supabase
        response = supabase.table("avaliacao").insert({
            "nota": nota,
            "data": datetime.now(timezone.utc).isoformat()
        }).execute()

        # Se a inserção for bem-sucedida, retorna uma resposta JSON
        if response.data:
            return jsonify({"mensagem": "Avaliação registrada com sucesso!", "mostrar_modal": True}), 201
        else:
            return jsonify({"erro": "Erro ao registrar avaliação"}), 500

    except Exception as e:
        print(f"Erro ao registrar avaliação: {e}")
        return jsonify({"erro": "Erro inesperado ao registrar avaliação"}), 500



@app.route('/avaliacoes', methods=['GET'])
def listar_avaliacoes():
    try:
        agora = datetime.now(timezone.utc)
        response = supabase.table("avaliacao").select("*").execute()

        if not response.data:
            return render_template("avaliacoes.html", 
                media_dia=0, 
                media_semana=0, 
                media_mes=0, 
                media_total=0, 
                media_dom=0, media_seg=0, media_ter=0, media_qua=0, media_qui=0, media_sex=0, media_sab=0
            )

        avaliacoes = response.data
        medias_semana = {i: [] for i in range(7)}
        
        for a in avaliacoes:
            try:
                data_avaliacao = datetime.fromisoformat(a["data"]).replace(tzinfo=timezone.utc)
                dia_semana = data_avaliacao.weekday()
                medias_semana[dia_semana].append(float(a["nota"]))
            except Exception as e:
                print(f"Erro ao processar avaliação: {e}")
        
        medias_calculadas = {i: sum(medias_semana[i]) / len(medias_semana[i]) if medias_semana[i] else 0 for i in range(7)}
        total_avaliacoes = sum(len(medias_semana[i]) for i in range(7))
        media_total = sum(sum(medias_semana[i]) for i in range(7)) / total_avaliacoes if total_avaliacoes > 0 else 0

        return render_template("avaliacoes.html", 
            media_dia=medias_calculadas.get(agora.weekday(), 0),
            media_semana=sum(sum(medias_semana[i]) for i in range(7)) / total_avaliacoes if total_avaliacoes > 0 else 0,
            media_mes=media_total,
            media_total=media_total,
            media_dom=medias_calculadas[6], media_seg=medias_calculadas[0], media_ter=medias_calculadas[1],
            media_qua=medias_calculadas[2], media_qui=medias_calculadas[3], media_sex=medias_calculadas[4], media_sab=medias_calculadas[5]
        )
    
    except Exception as e:
        print(f"Erro ao buscar avaliações: {e}")
        return jsonify({"erro": "Erro inesperado ao buscar avaliações"}), 500

def atualizar_avaliacoes_periodicamente():
    with app.app_context():
        while True:
            print("Atualizando avaliações...")
            listar_avaliacoes()
            time.sleep(1800)

if __name__ == '__main__':

    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
