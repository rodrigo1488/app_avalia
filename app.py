from flask import Flask, request, jsonify, render_template
import sqlite3
from sqlite3 import Error
from datetime import datetime, timezone
import threading
import time
import os

app = Flask(__name__)

# Função para obter conexão com o banco SQLite
def get_db_connection():
    conn = sqlite3.connect('avaliacoes.db', detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn

# Função para inicializar o banco de dados (cria a tabela se não existir)
def init_db():
    try:
        conn = get_db_connection()
        with conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS avaliacao (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nota INTEGER NOT NULL,
                    data TEXT NOT NULL
                )
            ''')
        conn.close()
        print("Banco de dados inicializado com sucesso!")
    except Error as e:
        print(f"Erro ao inicializar o banco de dados: {e}")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/avaliacao', methods=['GET'])
def renderizar_avaliacao():
    return render_template('avaliacao.html')

# Rota para receber a avaliação (requisição POST)
@app.route('/avaliacao', methods=['POST'])
def receber_avaliacao():
    data = request.json
    nota = data.get("nota")

    # Validação da nota
    if nota is None or not isinstance(nota, (int, float)) or not (1 <= nota <= 10):
        return jsonify({"erro": "Nota inválida"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Insere a avaliação com a data atual no formato ISO
        cur.execute(
            "INSERT INTO avaliacao (nota, data) VALUES (?, ?)",
            (nota, datetime.now(timezone.utc).isoformat())
        )
        conn.commit()
        conn.close()
        return jsonify({"mensagem": "Avaliação registrada com sucesso!", "mostrar_modal": True}), 201
    except Exception as e:
        print(f"Erro ao registrar avaliação: {e}")
        return jsonify({"erro": "Erro inesperado ao registrar avaliação"}), 500

@app.route('/avaliacoes', methods=['GET'])
def listar_avaliacoes():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM avaliacao")
        avaliacoes = cur.fetchall()
        conn.close()

        # Calcula as médias por dia da semana
        medias_semana = {i: [] for i in range(7)}
        for a in avaliacoes:
            try:
                data_avaliacao = datetime.fromisoformat(a["data"]).replace(tzinfo=timezone.utc)
                dia_semana = data_avaliacao.weekday()  # 0: segunda, 6: domingo
                medias_semana[dia_semana].append(float(a["nota"]))
            except Exception as e:
                print(f"Erro ao processar avaliação: {e}")

        # Calcula a média para cada dia
        medias_calculadas = {
            i: sum(medias_semana[i]) / len(medias_semana[i]) if medias_semana[i] else 0
            for i in range(7)
        }
        total_avaliacoes = sum(len(medias_semana[i]) for i in range(7))
        media_total = (sum(sum(medias_semana[i]) for i in range(7)) / total_avaliacoes) if total_avaliacoes > 0 else 0

        agora = datetime.now(timezone.utc)
        return render_template("avaliacoes.html", 
            media_dia=medias_calculadas.get(agora.weekday(), 0),
            media_semana=(sum(sum(medias_semana[i]) for i in range(7)) / total_avaliacoes) if total_avaliacoes > 0 else 0,
            media_mes=media_total,
            media_total=media_total,
            media_dom=medias_calculadas.get(6, 0),
            media_seg=medias_calculadas.get(0, 0),
            media_ter=medias_calculadas.get(1, 0),
            media_qua=medias_calculadas.get(2, 0),
            media_qui=medias_calculadas.get(3, 0),
            media_sex=medias_calculadas.get(4, 0),
            media_sab=medias_calculadas.get(5, 0)
        )
    
    except Exception as e:
        print(f"Erro ao buscar avaliações: {e}")
        return jsonify({"erro": "Erro inesperado ao buscar avaliações"}), 500

# Função opcional para atualizar avaliações periodicamente (se necessário)
def atualizar_avaliacoes_periodicamente():
    with app.app_context():
        while True:
            print("Atualizando avaliações...")
            listar_avaliacoes()
            time.sleep(1800)
cert_path = os.path.join(os.getcwd(), 'cert.pem')
key_path = os.path.join(os.getcwd(), 'chave.pem')
if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True, ssl_context=(cert_path, key_path))
