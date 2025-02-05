from flask import Flask, request, jsonify, render_template,make_response,redirect
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
    empresa_id = request.cookies.get('empresa_id')
    empresa_nome = request.cookies.get('empresa_nome')

    if not empresa_id or not empresa_nome:
        # Redireciona para a página de login se os cookies não forem encontrados
        return redirect('/login')

    # Se os cookies existirem, renderiza a página inicial
    return redirect('/index')


@app.route('/index')
def index():
    return render_template('index.html')

# Tela de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')  # Renderiza a página de login

    if request.method == 'POST':
        # Captura os dados enviados pelo formulário
        email = request.form.get('email')
        senha = request.form.get('senha')

        if not email or not senha:
            return render_template('login.html', error="Email e senha são obrigatórios")

        try:
            # Busca o usuário no banco de dados com base no email
            response = supabase.table('empresa').select("*").eq("email", email).execute()
            if not response.data:
                return render_template('login.html', error="Email ou senha incorretos")

            empresa = response.data[0]  # Obtém o primeiro registro encontrado

            # Verifica se a senha está correta
            if empresa['senha'] != senha:
                return render_template('login.html', error="Email ou senha incorretos")

            # Cria uma resposta com redirecionamento
            response = make_response(redirect('/index'))

            # Define os cookies com os dados do login
            response.set_cookie('empresa_id', str(empresa['id']), httponly=True, max_age=3600)
            response.set_cookie('empresa_nome', empresa['nome'], httponly=True, max_age=3600)

            return response

        except Exception as e:
            print(f"Erro ao realizar login: {e}")
            return render_template('login.html', error="Erro ao processar o login")



# Rota de logout
@app.route('/logout', methods=['GET'])
def logout():
    response = make_response(redirect('/login'))
    response.delete_cookie('empresa_id')
    response.delete_cookie('empresa_nome')
    return response

@app.route('/avaliacao', methods=['GET'])
def renderizar_avaliacao():
    return render_template('avaliacao.html')

@app.route('/getData', methods=['GET'])
def get_data():
    try:
        empresa_id = request.cookies.get('empresa_id')

        if not empresa_id:
            return jsonify({"erro": "Usuário não autenticado"}), 401

        agora = datetime.now(timezone.utc)

        response = supabase.table("avaliacao").select("*").eq("empresa_id", empresa_id).execute()

        if not response.data:
            return jsonify({"labels": [], "values": [], "label": "Sem dados"}), 200

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

        tipo = request.args.get("type")

        if tipo == "dia":
            labels = ["Hoje"]
            values = [medias_calculadas.get(agora.weekday(), 0)]
            label = "Média do Dia"
        elif tipo == "semana":
            labels = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
            values = [medias_calculadas[i] for i in range(7)]
            label = "Média da Semana"
        elif tipo == "mes":
            labels = ["Média do Mês"]
            values = [media_total]
            label = "Média do Mês"
        elif tipo == "total":
            labels = ["Média Geral"]
            values = [media_total]
            label = "Média Geral"
        else:
            return jsonify({"erro": "Tipo inválido"}), 400

        return jsonify({"labels": labels, "values": values, "label": label})

    except Exception as e:
        print(f"Erro: {e}")
        return jsonify({"erro": "Erro interno do servidor"}), 500

# Rota para receber a avaliação (requisição POST)
@app.route('/avaliacao', methods=['POST'])
def receber_avaliacao():
    # Recupera os dados enviados
    data = request.json
    nota = data.get("nota")

    # Recupera o ID da empresa dos cookies
    empresa_id = request.cookies.get('empresa_id')

    # Verifica se a nota e o ID da empresa são válidos
    if not empresa_id:
        return jsonify({"erro": "Usuário não autenticado"}), 401
    if nota is None or not isinstance(nota, (int, float)) or not (1 <= nota <= 10):
        return jsonify({"erro": "Nota inválida"}), 400

    try:
        # Insere a avaliação na tabela 'avaliacao' do Supabase
        response = supabase.table("avaliacao").insert({
            "nota": nota,
            "empresa_id": empresa_id,
            "data": datetime.now(timezone.utc).isoformat()
        }).execute()

        if response.data:
            # Verifica se a nota é menor que 5
            if nota < 5:
                return jsonify({
                    "mensagem": "Avaliação registrada com sucesso!",
                    "mostrar_modal_feedback": True
                }), 201

            return jsonify({
                "mensagem": "Avaliação registrada com sucesso!"
            }), 201

        else:
            return jsonify({"erro": "Erro ao registrar avaliação"}), 500

    except Exception as e:
        print(f"Erro ao registrar avaliação: {e}")
        return jsonify({"erro": "Erro inesperado ao registrar avaliação"}), 500



#rota para enviar o feedback
@app.route('/feedback', methods=['POST'])
def receber_feedback():
    # Recupera os dados enviados
    data = request.json
    feedback = data.get("feedback")

    # Recupera o ID da empresa dos cookies
    empresa_id = request.cookies.get('empresa_id')

    # Verifica se o feedback e o ID da empresa são válidos
    if not empresa_id:
        return jsonify({"erro": "Usuário não autenticado"}), 401
    if not feedback or not isinstance(feedback, str):
        return jsonify({"erro": "Feedback inválido"}), 400

    try:
        # Insere o feedback na tabela 'feedback' do Supabase
        response = supabase.table("feedback").insert({
            "feedback": feedback,
            "empresa_id": empresa_id,
            "data": datetime.now(timezone.utc).isoformat()
        }).execute()

        if response.data:
            return jsonify({"mensagem": "Feedback registrado com sucesso!"}), 201
        else:
            return jsonify({"erro": "Erro ao registrar feedback"}), 500

    except Exception as e:
        print(f"Erro ao registrar feedback: {e}")
        return jsonify({"erro": "Erro inesperado ao registrar feedback"}), 500

#rota para listar os feedbacks
@app.route('/feedbacks', methods=['GET'])
def listar_feedbacks():
    try:
        # Recupera o ID da empresa dos cookies
        empresa_id = request.cookies.get('empresa_id')

        # Verifica se o ID da empresa está presente
        if not empresa_id:
            return jsonify({"erro": "Usuário não autenticado"}), 401

        # Busca os feedbacks da empresa correspondente no Supabase
        response = supabase.table("feedback").select("*").eq("empresa_id", empresa_id).order("data", desc=True).execute()

        if not response.data:
            return jsonify([])  # Retorna uma lista vazia se não houver feedbacks

        feedbacks = response.data
        return jsonify(feedbacks), 200

    except Exception as e:
        print(f"Erro ao buscar feedbacks: {e}")
        return jsonify({"erro": "Erro inesperado ao buscar feedbacks"}), 500


@app.route('/avaliacoes', methods=['GET'])
def listar_avaliacoes():
    try:
        # Recupera o ID da empresa dos cookies
        empresa_id = request.cookies.get('empresa_id')

        # Verifica se o ID da empresa está presente
        if not empresa_id:
            return jsonify({"erro": "Usuário não autenticado"}), 401

        agora = datetime.now(timezone.utc)

        # Busca apenas as avaliações da empresa correspondente
        response = supabase.table("avaliacao").select("*").eq("empresa_id", empresa_id).execute()

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
                # Calcula os dados de cada avaliação
                data_avaliacao = datetime.fromisoformat(a["data"]).replace(tzinfo=timezone.utc)
                dia_semana = data_avaliacao.weekday()
                medias_semana[dia_semana].append(float(a["nota"]))
            except Exception as e:
                print(f"Erro ao processar avaliação: {e}")

        # Calcula as médias semanais e total
        medias_calculadas = {i: sum(medias_semana[i]) / len(medias_semana[i]) if medias_semana[i] else 0 for i in range(7)}
        total_avaliacoes = sum(len(medias_semana[i]) for i in range(7))
        media_total = sum(sum(medias_semana[i]) for i in range(7)) / total_avaliacoes if total_avaliacoes > 0 else 0

        # Renderiza a página com as médias calculadas
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

@app.route('/get_logo_url', methods=['GET'])
def get_logo_url():
    # Recupera o ID da empresa dos cookies
    empresa_id = request.cookies.get('empresa_id')

    if not empresa_id:
        return jsonify({"erro": "Usuário não autenticado"}), 401

    try:
        # Busca o logo da empresa no banco de dados
        response = supabase.table('empresa').select('logo').eq('id', empresa_id).execute()
        if not response.data:
            return jsonify({"erro": "Logo não encontrado"}), 404

        logo_url = response.data[0].get('logo')
        return jsonify({"logo_url": logo_url}), 200

    except Exception as e:
        print(f"Erro ao buscar o logo: {e}")
        return jsonify({"erro": "Erro ao buscar o logo"}), 500


def atualizar_avaliacoes_periodicamente():
    with app.app_context():
        while True:
            print("Atualizando avaliações...")
            listar_avaliacoes()
            time.sleep(1800)

if __name__ == '__main__':

    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
