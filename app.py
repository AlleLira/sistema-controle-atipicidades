import sys
from pathlib import Path

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

from flask import Flask, render_template, request, redirect, url_for, flash, abort

from database.db import inicializar_banco, conectar
from database.reclame_aqui_db import inicializar_reclame_aqui
from reclame_aqui import reclame_aqui_bp
from central_relatorios import central_relatorios_bp
from relatorios_pdf import relatorios_pdf_bp


if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static")
)
app.config["SECRET_KEY"] = "desenvolvimento-local"

inicializar_banco()
inicializar_reclame_aqui()
app.register_blueprint(reclame_aqui_bp)
app.register_blueprint(relatorios_pdf_bp)
app.register_blueprint(central_relatorios_bp)


CAMPOS = [
    "data_atipicidade",
    "call_center",
    "controle",
    "cliente",
    "data_compra",
    "acessorio",
    "historico_compra",
    "local",
    "produtos_trocados",
    "prazo_garantias",
    "progresso",
    "desfecho",
    "resolutiva_final",
    "situacao"
]

PROGRESSOS = (
    "Aberta",
    "Aguardando loja",
    "Finalizado"
)

DESFECHOS = (
    "Pendente",
    "Troca",
    "Estorno",
    "Negado"
)

NOMES_CAMPOS = {
    "data_atipicidade": "Data da Atipicidade",
    "call_center": "Call Center",
    "controle": "Controle",
    "cliente": "Cliente",
    "data_compra": "Data da Compra",
    "acessorio": "Acessório",
    "historico_compra": "Histórico de Compra",
    "local": "Local",
    "produtos_trocados": "Produtos Trocados",
    "prazo_garantias": "Prazo de Garantias",
    "progresso": "Progresso",
    "desfecho": "Desfecho",
    "resolutiva_final": "Resolutiva Final",
    "situacao": "Situação",
    "devolutiva": "Devolutiva no Grupo"
}


def agora_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


@app.template_filter("moeda")
def formatar_moeda(valor):
    if valor is None or valor == "":
        return "—"

    try:
        numero = Decimal(str(valor))
        resultado = f"{numero:,.2f}"
        return (
            "R$ "
            + resultado.replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )
    except (InvalidOperation, ValueError):
        return str(valor)


@app.template_filter("data_br")
def formatar_data(valor):
    if not valor:
        return "—"

    try:
        return date.fromisoformat(valor).strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return valor


@app.template_filter("data_hora_br")
def formatar_data_hora(valor):
    if not valor:
        return "—"

    try:
        return datetime.fromisoformat(valor).strftime("%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        return valor


def ler_formulario():
    return {
        campo: request.form.get(campo, "").strip()
        for campo in CAMPOS
    }


def validar_dados(dados):
    if not dados["cliente"] or not dados["data_atipicidade"]:
        return "Informe o cliente e a data da atipicidade."

    if dados["progresso"] not in PROGRESSOS:
        return "Selecione um progresso válido."

    if dados["desfecho"] not in DESFECHOS:
        return "Selecione um desfecho válido."

    try:
        date.fromisoformat(dados["data_atipicidade"])

        if dados["data_compra"]:
            date.fromisoformat(dados["data_compra"])
    except ValueError:
        return "Informe datas válidas."

    if dados["historico_compra"]:
        try:
            valor = Decimal(dados["historico_compra"])

            if not valor.is_finite() or valor < 0:
                return "Informe um Histórico de Compra válido."

            if valor.as_tuple().exponent < -2:
                return "Use no máximo duas casas decimais."

            dados["historico_compra"] = str(
                valor.quantize(Decimal("0.01"))
            )
        except (InvalidOperation, ValueError):
            return "Informe um Histórico de Compra válido."

    return None


def buscar_atipicidade(conexao, identificador):
    registro = conexao.execute(
        "SELECT * FROM atipicidades WHERE id = ?",
        (identificador,)
    ).fetchone()

    if registro is None:
        abort(404)

    return registro


@app.route("/")
def inicio():
    with conectar() as conexao:
        total = conexao.execute(
            "SELECT COUNT(*) FROM atipicidades"
        ).fetchone()[0]

        abertas = conexao.execute(
            "SELECT COUNT(*) FROM atipicidades WHERE progresso = ?",
            ("Aberta",)
        ).fetchone()[0]

        aguardando = conexao.execute(
            "SELECT COUNT(*) FROM atipicidades WHERE progresso = ?",
            ("Aguardando loja",)
        ).fetchone()[0]

        finalizadas = conexao.execute(
            "SELECT COUNT(*) FROM atipicidades WHERE progresso = ?",
            ("Finalizado",)
        ).fetchone()[0]

    return render_template(
        "index.html",
        indicadores={
            "total": total,
            "abertas": abertas,
            "aguardando_loja": aguardando,
            "finalizadas": finalizadas
        }
    )


@app.route("/atipicidades/nova", methods=["GET", "POST"])
def nova_atipicidade():
    if request.method == "POST":
        dados = ler_formulario()
        devolutiva = request.form.get("devolutiva", "").strip()
        erro = validar_dados(dados)

        if erro:
            flash(erro, "erro")
            return render_template(
                "nova_atipicidade.html",
                hoje=date.today().isoformat(),
                dados={**dados, "devolutiva": devolutiva}
            ), 400

        finalizado_em = None

        if dados["progresso"] == "Finalizado":
            finalizado_em = agora_utc()

        with conectar() as conexao:
            cursor = conexao.execute(
                """
                INSERT INTO atipicidades (
                    data_atipicidade,
                    call_center,
                    controle,
                    cliente,
                    data_compra,
                    acessorio,
                    historico_compra,
                    local,
                    produtos_trocados,
                    prazo_garantias,
                    progresso,
                    desfecho,
                    resolutiva_final,
                    situacao,
                    finalizado_em
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    *(dados[campo] or None for campo in CAMPOS),
                    finalizado_em
                )
            )

            identificador = cursor.lastrowid

            if devolutiva:
                conexao.execute(
                    """
                    INSERT INTO devolutivas (atipicidade_id, texto)
                    VALUES (?, ?)
                    """,
                    (identificador, devolutiva)
                )

        flash(
            f"Atipicidade #{identificador} cadastrada com sucesso!",
            "sucesso"
        )

        return redirect(url_for("inicio"))

    return render_template(
        "nova_atipicidade.html",
        hoje=date.today().isoformat(),
        dados={}
    )


@app.route("/atipicidades")
def consultar_atipicidades():
    filtros = {
        nome: request.args.get(nome, "").strip()
        for nome in (
            "cliente",
            "controle",
            "local",
            "progresso",
            "desfecho",
            "data_inicio",
            "data_fim"
        )
    }

    consulta = """
        SELECT
            a.id,
            a.data_atipicidade,
            a.cliente,
            a.controle,
            a.local,
            a.progresso,
            a.desfecho,
            (
                SELECT COUNT(*)
                FROM reclame_aqui AS r
                WHERE r.atipicidade_id = a.id
            ) AS total_reclamacoes
        FROM atipicidades AS a
        WHERE 1 = 1
    """

    parametros = []

    for nome in ("cliente", "controle", "local"):
        if filtros[nome]:
            consulta += f" AND a.{nome} LIKE ?"
            parametros.append(f"%{filtros[nome]}%")

    for nome in ("progresso", "desfecho"):
        if filtros[nome]:
            consulta += f" AND a.{nome} = ?"
            parametros.append(filtros[nome])

    if filtros["data_inicio"]:
        consulta += " AND a.data_atipicidade >= ?"
        parametros.append(filtros["data_inicio"])

    if filtros["data_fim"]:
        consulta += " AND a.data_atipicidade <= ?"
        parametros.append(filtros["data_fim"])

    consulta += """
        ORDER BY a.data_atipicidade DESC, a.id DESC
    """

    with conectar() as conexao:
        registros = conexao.execute(
            consulta,
            parametros
        ).fetchall()

    return render_template(
        "consultar.html",
        registros=registros
    )


@app.route("/atipicidades/<int:atipicidade_id>")
def detalhes_atipicidade(atipicidade_id):
    with conectar() as conexao:
        atipicidade = buscar_atipicidade(
            conexao,
            atipicidade_id
        )

        devolutivas = conexao.execute(
            """
            SELECT *
            FROM devolutivas
            WHERE atipicidade_id = ?
            ORDER BY criado_em DESC, id DESC
            """,
            (atipicidade_id,)
        ).fetchall()

        reclamacoes = conexao.execute(
            """
            SELECT
                id,
                data_abertura,
                status_reclamacao,
                respondido,
                problema_resolvido
            FROM reclame_aqui
            WHERE atipicidade_id = ?
            ORDER BY data_abertura DESC, id DESC
            """,
            (atipicidade_id,)
        ).fetchall()

        historico = conexao.execute(
            """
            SELECT *
            FROM historico_edicoes
            WHERE atipicidade_id = ?
            ORDER BY alterado_em DESC, id DESC
            """,
            (atipicidade_id,)
        ).fetchall()

    return render_template(
        "detalhes.html",
        atipicidade=atipicidade,
        devolutivas=devolutivas,
        reclamacoes=reclamacoes,
        historico=historico,
        nomes_campos=NOMES_CAMPOS
    )


@app.route(
    "/atipicidades/<int:atipicidade_id>/editar",
    methods=["GET", "POST"]
)
def editar_atipicidade(atipicidade_id):
    with conectar() as conexao:
        registro = buscar_atipicidade(
            conexao,
            atipicidade_id
        )
        dados_atuais = dict(registro)

    if request.method == "POST":
        dados = ler_formulario()
        erro = validar_dados(dados)

        if erro:
            flash(erro, "erro")
            return render_template(
                "editar_atipicidade.html",
                atipicidade_id=atipicidade_id,
                dados=dados
            ), 400

        alteracoes = []

        for campo in CAMPOS:
            anterior = dados_atuais[campo] or ""
            novo = dados[campo] or ""

            if campo == "historico_compra" and anterior:
                try:
                    anterior = str(
                        Decimal(str(anterior)).quantize(
                            Decimal("0.01")
                        )
                    )
                except InvalidOperation:
                    pass

            if str(anterior) != str(novo):
                alteracoes.append((
                    campo,
                    str(anterior),
                    str(novo)
                ))

        if not alteracoes:
            flash(
                "Nenhuma alteração identificada.",
                "sucesso"
            )
            return redirect(
                url_for(
                    "detalhes_atipicidade",
                    atipicidade_id=atipicidade_id
                )
            )

        momento = agora_utc()
        finalizado_em = dados_atuais["finalizado_em"]

        if dados["progresso"] == "Finalizado":
            if dados_atuais["progresso"] != "Finalizado":
                finalizado_em = momento
        else:
            finalizado_em = None

        with conectar() as conexao:
            atribuicoes = ", ".join(
                f"{campo} = ?"
                for campo in CAMPOS
            )

            conexao.execute(
                f"""
                UPDATE atipicidades
                SET
                    {atribuicoes},
                    atualizado_em = ?,
                    finalizado_em = ?
                WHERE id = ?
                """,
                [
                    *(dados[campo] or None for campo in CAMPOS),
                    momento,
                    finalizado_em,
                    atipicidade_id
                ]
            )

            for campo, anterior, novo in alteracoes:
                conexao.execute(
                    """
                    INSERT INTO historico_edicoes (
                        atipicidade_id,
                        campo,
                        valor_anterior,
                        valor_novo,
                        alterado_em
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        atipicidade_id,
                        campo,
                        anterior,
                        novo,
                        momento
                    )
                )

        flash(
            f"{len(alteracoes)} campo(s) atualizado(s) com sucesso!",
            "sucesso"
        )

        return redirect(
            url_for(
                "detalhes_atipicidade",
                atipicidade_id=atipicidade_id
            )
        )

    return render_template(
        "editar_atipicidade.html",
        atipicidade_id=atipicidade_id,
        dados=dados_atuais
    )


@app.route(
    "/atipicidades/<int:atipicidade_id>/devolutivas",
    methods=["POST"]
)
def adicionar_devolutiva(atipicidade_id):
    texto = request.form.get("texto", "").strip()

    with conectar() as conexao:
        buscar_atipicidade(
            conexao,
            atipicidade_id
        )

        if texto:
            conexao.execute(
                """
                INSERT INTO devolutivas (
                    atipicidade_id,
                    texto
                )
                VALUES (?, ?)
                """,
                (atipicidade_id, texto)
            )

    if texto:
        flash(
            "Devolutiva registrada com sucesso!",
            "sucesso"
        )
    else:
        flash(
            "A devolutiva não pode estar vazia.",
            "erro"
        )

    return redirect(
        url_for(
            "detalhes_atipicidade",
            atipicidade_id=atipicidade_id
        )
    )


@app.route(
    "/atipicidades/<int:atipicidade_id>/devolutivas/"
    "<int:devolutiva_id>/editar",
    methods=["POST"]
)
def editar_devolutiva(atipicidade_id, devolutiva_id):
    novo_texto = request.form.get("texto", "").strip()

    with conectar() as conexao:
        buscar_atipicidade(
            conexao,
            atipicidade_id
        )

        devolutiva = conexao.execute(
            """
            SELECT *
            FROM devolutivas
            WHERE id = ?
              AND atipicidade_id = ?
            """,
            (
                devolutiva_id,
                atipicidade_id
            )
        ).fetchone()

        if devolutiva is None:
            abort(404)

        if novo_texto and novo_texto != devolutiva["texto"]:
            momento = agora_utc()

            conexao.execute(
                """
                INSERT INTO historico_edicoes (
                    atipicidade_id,
                    devolutiva_id,
                    campo,
                    valor_anterior,
                    valor_novo,
                    alterado_em
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    atipicidade_id,
                    devolutiva_id,
                    "devolutiva",
                    devolutiva["texto"],
                    novo_texto,
                    momento
                )
            )

            conexao.execute(
                """
                UPDATE devolutivas
                SET
                    texto = ?,
                    atualizado_em = ?
                WHERE id = ?
                  AND atipicidade_id = ?
                """,
                (
                    novo_texto,
                    momento,
                    devolutiva_id,
                    atipicidade_id
                )
            )

            flash(
                "Devolutiva atualizada com sucesso!",
                "sucesso"
            )

        elif not novo_texto:
            flash(
                "A devolutiva não pode ficar vazia.",
                "erro"
            )
        else:
            flash(
                "Nenhuma alteração identificada.",
                "sucesso"
            )

    return redirect(
        url_for(
            "detalhes_atipicidade",
            atipicidade_id=atipicidade_id
        )
    )


@app.route("/indicadores")
def indicadores():
    hoje = date.today()

    data_inicio = request.args.get(
        "data_inicio", ""
    ).strip()

    data_fim = request.args.get(
        "data_fim", ""
    ).strip()

    progresso = request.args.get(
        "progresso", ""
    ).strip()

    desfecho = request.args.get(
        "desfecho", ""
    ).strip()

    lojas_solicitadas = request.args.getlist("lojas")
    lojas_enviadas = "lojas_enviadas" in request.args

    try:
        if data_inicio:
            date.fromisoformat(data_inicio)

        if data_fim:
            date.fromisoformat(data_fim)
    except ValueError:
        flash(
            "Informe datas válidas.",
            "erro"
        )
        return redirect(url_for("indicadores"))

    if data_inicio and data_fim and data_inicio > data_fim:
        flash(
            "A data inicial não pode ser maior que a data final.",
            "erro"
        )
        return redirect(url_for("indicadores"))

    if progresso and progresso not in PROGRESSOS:
        abort(400, "Progresso inválido.")

    if desfecho and desfecho not in DESFECHOS:
        abort(400, "Desfecho inválido.")

    with conectar() as conexao:
        lojas_disponiveis = [
            linha["loja"]
            for linha in conexao.execute(
                """
                SELECT DISTINCT TRIM(local) AS loja
                FROM atipicidades
                WHERE local IS NOT NULL
                  AND TRIM(local) != ''
                ORDER BY loja COLLATE NOCASE
                """
            ).fetchall()
        ]

        if lojas_enviadas:
            lojas_selecionadas = [
                loja
                for loja in lojas_disponiveis
                if loja in lojas_solicitadas
            ]
        else:
            lojas_selecionadas = lojas_disponiveis[:]

        condicoes = ["1 = 1"]
        parametros = []

        if data_inicio:
            condicoes.append("data_atipicidade >= ?")
            parametros.append(data_inicio)

        if data_fim:
            condicoes.append("data_atipicidade <= ?")
            parametros.append(data_fim)

        if progresso:
            condicoes.append("progresso = ?")
            parametros.append(progresso)

        if desfecho:
            condicoes.append("desfecho = ?")
            parametros.append(desfecho)

        if lojas_enviadas:
            if lojas_selecionadas:
                marcadores = ",".join(
                    "?" for _ in lojas_selecionadas
                )

                condicoes.append(
                    f"TRIM(local) IN ({marcadores})"
                )
                parametros.extend(lojas_selecionadas)
            else:
                condicoes.append("1 = 0")

        consulta = """
            SELECT
                id,
                data_atipicidade,
                local,
                progresso,
                desfecho,
                finalizado_em
            FROM atipicidades
            WHERE
        """

        consulta += " AND ".join(condicoes)

        registros = [
            dict(linha)
            for linha in conexao.execute(
                consulta,
                parametros
            ).fetchall()
        ]

    total = len(registros)

    abertas = sum(
        registro["progresso"] == "Aberta"
        for registro in registros
    )

    aguardando = sum(
        registro["progresso"] == "Aguardando loja"
        for registro in registros
    )

    finalizadas_lista = [
        registro
        for registro in registros
        if registro["progresso"] == "Finalizado"
    ]

    finalizadas = len(finalizadas_lista)

    taxa_finalizacao = (
        finalizadas * 100 / total
        if total else 0
    )

    desfechos = {
        nome: 0
        for nome in DESFECHOS
    }

    desfechos_finalizados = {
        nome: 0
        for nome in DESFECHOS
    }

    atrasadas = 0
    tempos_resolucao = []
    meses = {}
    por_loja = {}
    finalizacoes_mensais = {}
    total_sem_loja = 0

    for registro in registros:
        nome_desfecho = registro["desfecho"]

        if nome_desfecho in desfechos:
            desfechos[nome_desfecho] += 1

        if (
            registro["progresso"] == "Finalizado"
            and nome_desfecho in desfechos_finalizados
        ):
            desfechos_finalizados[nome_desfecho] += 1

        try:
            abertura = date.fromisoformat(
                registro["data_atipicidade"]
            )
        except (ValueError, TypeError):
            continue

        mes_abertura = abertura.strftime("%Y-%m")

        meses[mes_abertura] = (
            meses.get(mes_abertura, 0) + 1
        )

        loja = (
            (registro["local"] or "").strip()
            or "Não informada"
        )

        if loja == "Não informada":
            total_sem_loja += 1

        por_loja[loja] = (
            por_loja.get(loja, 0) + 1
        )

        if (
            registro["progresso"] != "Finalizado"
            and (hoje - abertura).days > 3
        ):
            atrasadas += 1

        if (
            registro["progresso"] == "Finalizado"
            and registro["finalizado_em"]
        ):
            try:
                fechamento = datetime.fromisoformat(
                    registro["finalizado_em"]
                ).date()

                dias = (fechamento - abertura).days

                if dias >= 0:
                    tempos_resolucao.append(dias)

                mes_finalizacao = fechamento.strftime(
                    "%Y-%m"
                )

                finalizacoes_mensais[mes_finalizacao] = (
                    finalizacoes_mensais.get(
                        mes_finalizacao, 0
                    ) + 1
                )
            except (ValueError, TypeError):
                pass

    media_resolucao = (
        sum(tempos_resolucao) / len(tempos_resolucao)
        if tempos_resolucao
        else None
    )

    meses_ordenados = sorted(meses)
    finalizacoes_ordenadas = sorted(
        finalizacoes_mensais
    )

    lojas_ordenadas = sorted(
        por_loja.items(),
        key=lambda item: (
            -item[1],
            item[0].lower()
        )
    )

    return render_template(
        "indicadores.html",
        total=total,
        abertas=abertas,
        aguardando=aguardando,
        finalizadas=finalizadas,
        atrasadas=atrasadas,
        taxa_finalizacao=taxa_finalizacao,
        media_resolucao=media_resolucao,
        casos_com_tempo=len(tempos_resolucao),
        desfechos=desfechos,
        desfechos_finalizados=desfechos_finalizados,
        lojas_disponiveis=lojas_disponiveis,
        lojas_selecionadas=lojas_selecionadas,
        data_inicio=data_inicio,
        data_fim=data_fim,
        progresso_filtro=progresso,
        desfecho_filtro=desfecho,
        meses_labels=meses_ordenados,
        meses_valores=[
            meses[mes]
            for mes in meses_ordenados
        ],
        lojas_labels=[
            loja
            for loja, quantidade in lojas_ordenadas
        ],
        lojas_valores=[
            quantidade
            for loja, quantidade in lojas_ordenadas
        ],
        finalizacoes_labels=finalizacoes_ordenadas,
        finalizacoes_valores=[
            finalizacoes_mensais[mes]
            for mes in finalizacoes_ordenadas
        ],
        total_sem_loja=total_sem_loja
    )


if __name__ == "__main__":
    app.run(
        debug=True,
        port=5000
    )
