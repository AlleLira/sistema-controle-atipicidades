
from datetime import date

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort
)

from database.db import conectar


reclame_aqui_bp = Blueprint(
    "reclame_aqui",
    __name__,
    url_prefix="/reclame-aqui"
)


STATUS = (
    "Em aberto",
    "Aguardando resposta",
    "Respondida",
    "Aguardando avaliação",
    "Finalizada"
)


def obter_atipicidade(conexao, identificador):
    return conexao.execute(
        """
        SELECT id, cliente, local, data_atipicidade
        FROM atipicidades
        WHERE id = ?
        """,
        (identificador,)
    ).fetchone()


def ler_dados():
    return {
        "atipicidade_id": request.form.get(
            "atipicidade_id", ""
        ).strip(),
        "cliente": request.form.get(
            "cliente", ""
        ).strip(),
        "local": request.form.get(
            "local", ""
        ).strip(),
        "data_abertura": request.form.get(
            "data_abertura", ""
        ).strip(),
        "situacao_cliente": request.form.get(
            "situacao_cliente", ""
        ).strip(),
        "respondido": request.form.get(
            "respondido", ""
        ).strip(),
        "retorno_call_center": request.form.get(
            "retorno_call_center", ""
        ).strip(),
        "status_reclamacao": request.form.get(
            "status_reclamacao", ""
        ).strip(),
        "problema_resolvido": request.form.get(
            "problema_resolvido", ""
        ).strip(),
        "faria_negocio_novamente": request.form.get(
            "faria_negocio_novamente", ""
        ).strip(),
        "nota_atendimento": request.form.get(
            "nota_atendimento", ""
        ).strip()
    }


def validar_dados(dados):
    if dados["atipicidade_id"]:
        try:
            identificador = int(dados["atipicidade_id"])

            if identificador <= 0:
                raise ValueError

        except ValueError:
            return "Informe um ID de atipicidade válido."

    try:
        date.fromisoformat(dados["data_abertura"])
    except ValueError:
        return "Informe uma data de abertura válida."

    if dados["status_reclamacao"] not in STATUS:
        return "Selecione um status válido."

    for campo in (
        "respondido",
        "problema_resolvido",
        "faria_negocio_novamente"
    ):
        if dados[campo] not in ("", "0", "1"):
            return "Informe respostas válidas."

    if dados["respondido"] == "":
        return "Informe se a reclamação foi respondida."

    if dados["nota_atendimento"]:
        try:
            nota = int(dados["nota_atendimento"])
        except ValueError:
            return "Informe uma nota válida."

        if not 0 <= nota <= 10:
            return "A nota deve estar entre 0 e 10."

    return None


def converter_opcional(valor):
    if valor == "":
        return None

    return int(valor)


def verificar_vinculo(conexao, dados):
    identificador = converter_opcional(
        dados["atipicidade_id"]
    )

    if identificador is None:
        return None, None

    atipicidade = obter_atipicidade(
        conexao,
        identificador
    )

    if atipicidade is None:
        return None, "A atipicidade informada não existe."

    return identificador, None


def dados_para_formulario(registro):
    return {
        chave: (
            "" if registro[chave] is None
            else str(registro[chave])
        )
        for chave in (
            "atipicidade_id",
            "cliente",
            "local",
            "data_abertura",
            "situacao_cliente",
            "respondido",
            "retorno_call_center",
            "status_reclamacao",
            "problema_resolvido",
            "faria_negocio_novamente",
            "nota_atendimento"
        )
    }


@reclame_aqui_bp.route("/")
def listar():
    busca = request.args.get(
        "busca", ""
    ).strip()

    consulta = """
        SELECT
            r.id,
            r.atipicidade_id,
            r.data_abertura,
            r.respondido,
            r.status_reclamacao,
            COALESCE(
                NULLIF(TRIM(r.cliente), ''),
                a.cliente
            ) AS cliente,
            COALESCE(
                NULLIF(TRIM(r.local), ''),
                a.local
            ) AS local
        FROM reclame_aqui AS r
        LEFT JOIN atipicidades AS a
            ON a.id = r.atipicidade_id
        WHERE 1 = 1
    """

    parametros = []

    if busca:
        condicoes = [
            "COALESCE(NULLIF(TRIM(r.cliente), ''), a.cliente) LIKE ?",
            "COALESCE(NULLIF(TRIM(r.local), ''), a.local) LIKE ?"
        ]

        parametros.extend([
            f"%{busca}%",
            f"%{busca}%"
        ])

        if busca.isdigit():
            condicoes.extend([
                "r.id = ?",
                "r.atipicidade_id = ?"
            ])

            parametros.extend([
                int(busca),
                int(busca)
            ])

        consulta += (
            " AND (" + " OR ".join(condicoes) + ")"
        )

    consulta += """
        ORDER BY r.data_abertura DESC, r.id DESC
    """

    with conectar() as conexao:
        registros = conexao.execute(
            consulta,
            parametros
        ).fetchall()

    return render_template(
        "reclame_aqui_lista.html",
        registros=registros,
        busca=busca
    )


@reclame_aqui_bp.route("/indicadores")
def indicadores():
    data_inicio = request.args.get(
        "data_inicio", ""
    ).strip()

    data_fim = request.args.get(
        "data_fim", ""
    ).strip()

    loja = request.args.get(
        "loja", ""
    ).strip()

    status = request.args.get(
        "status", ""
    ).strip()

    try:
        if data_inicio:
            date.fromisoformat(data_inicio)

        if data_fim:
            date.fromisoformat(data_fim)
    except ValueError:
        flash("Informe datas válidas.", "erro")
        return redirect(url_for("reclame_aqui.indicadores"))

    if data_inicio and data_fim and data_inicio > data_fim:
        flash(
            "A data inicial não pode ser maior que a data final.",
            "erro"
        )
        return redirect(url_for("reclame_aqui.indicadores"))

    if status and status not in STATUS:
        abort(400, "Status inválido.")

    expressao_loja = """
        COALESCE(
            NULLIF(TRIM(r.local), ''),
            NULLIF(TRIM(a.local), ''),
            'Não informada'
        )
    """

    with conectar() as conexao:
        lojas_disponiveis = [
            linha["loja"]
            for linha in conexao.execute(
                f"""
                SELECT DISTINCT
                    {expressao_loja} AS loja
                FROM reclame_aqui AS r
                LEFT JOIN atipicidades AS a
                    ON a.id = r.atipicidade_id
                ORDER BY loja COLLATE NOCASE
                """
            ).fetchall()
        ]

        condicoes = ["1 = 1"]
        parametros = []

        if data_inicio:
            condicoes.append("r.data_abertura >= ?")
            parametros.append(data_inicio)

        if data_fim:
            condicoes.append("r.data_abertura <= ?")
            parametros.append(data_fim)

        if loja:
            condicoes.append(
                f"{expressao_loja} = ?"
            )
            parametros.append(loja)

        if status:
            condicoes.append(
                "r.status_reclamacao = ?"
            )
            parametros.append(status)

        consulta = f"""
            SELECT
                r.id,
                r.data_abertura,
                r.respondido,
                r.status_reclamacao,
                r.problema_resolvido,
                r.faria_negocio_novamente,
                r.nota_atendimento,
                {expressao_loja} AS local
            FROM reclame_aqui AS r
            LEFT JOIN atipicidades AS a
                ON a.id = r.atipicidade_id
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

    respondidas = sum(
        registro["respondido"] == 1
        for registro in registros
    )

    pendentes_resposta = total - respondidas

    avaliadas_resolucao = [
        registro
        for registro in registros
        if registro["problema_resolvido"] in (0, 1)
    ]

    resolvidas = sum(
        registro["problema_resolvido"] == 1
        for registro in avaliadas_resolucao
    )

    taxa_resolucao = (
        resolvidas * 100 / len(avaliadas_resolucao)
        if avaliadas_resolucao else None
    )

    taxa_resposta = (
        respondidas * 100 / total
        if total else None
    )

    notas = [
        registro["nota_atendimento"]
        for registro in registros
        if registro["nota_atendimento"] is not None
    ]

    nota_media = (
        sum(notas) / len(notas)
        if notas else None
    )

    avaliadas_negocio = [
        registro
        for registro in registros
        if registro["faria_negocio_novamente"] in (0, 1)
    ]

    fariam_negocio = sum(
        registro["faria_negocio_novamente"] == 1
        for registro in avaliadas_negocio
    )

    taxa_negocio = (
        fariam_negocio * 100 / len(avaliadas_negocio)
        if avaliadas_negocio else None
    )

    por_status = {
        nome: 0
        for nome in STATUS
    }

    por_loja = {}
    por_mes = {}

    for registro in registros:
        nome_status = registro["status_reclamacao"]

        if nome_status in por_status:
            por_status[nome_status] += 1

        nome_loja = registro["local"] or "Não informada"

        por_loja[nome_loja] = (
            por_loja.get(nome_loja, 0) + 1
        )

        if registro["data_abertura"]:
            mes = registro["data_abertura"][:7]

            por_mes[mes] = (
                por_mes.get(mes, 0) + 1
            )

    lojas_ordenadas = sorted(
        por_loja.items(),
        key=lambda item: (
            -item[1],
            item[0].lower()
        )
    )

    meses_ordenados = sorted(por_mes)

    return render_template(
        "reclame_aqui_indicadores.html",
        total=total,
        respondidas=respondidas,
        pendentes_resposta=pendentes_resposta,
        resolvidas=resolvidas,
        avaliacoes_resolucao=len(avaliadas_resolucao),
        taxa_resolucao=taxa_resolucao,
        taxa_resposta=taxa_resposta,
        nota_media=nota_media,
        quantidade_notas=len(notas),
        fariam_negocio=fariam_negocio,
        avaliacoes_negocio=len(avaliadas_negocio),
        taxa_negocio=taxa_negocio,
        status_labels=list(por_status.keys()),
        status_valores=list(por_status.values()),
        lojas_labels=[
            nome
            for nome, quantidade in lojas_ordenadas
        ],
        lojas_valores=[
            quantidade
            for nome, quantidade in lojas_ordenadas
        ],
        meses_labels=meses_ordenados,
        meses_valores=[
            por_mes[mes]
            for mes in meses_ordenados
        ],
        lojas_disponiveis=lojas_disponiveis,
        status_opcoes=STATUS,
        data_inicio=data_inicio,
        data_fim=data_fim,
        loja_filtro=loja,
        status_filtro=status
    )


@reclame_aqui_bp.route(
    "/novo",
    methods=["GET", "POST"]
)
def novo():
    if request.method == "POST":
        dados = ler_dados()
        erro = validar_dados(dados)

        if erro:
            flash(erro, "erro")

            return render_template(
                "reclame_aqui_form.html",
                dados=dados,
                hoje=date.today().isoformat(),
                status_opcoes=STATUS
            ), 400

        with conectar() as conexao:
            atipicidade_id, erro = verificar_vinculo(
                conexao,
                dados
            )

            if erro:
                flash(erro, "erro")

                return render_template(
                    "reclame_aqui_form.html",
                    dados=dados,
                    hoje=date.today().isoformat(),
                    status_opcoes=STATUS
                ), 400

            cursor = conexao.execute(
                """
                INSERT INTO reclame_aqui (
                    atipicidade_id,
                    cliente,
                    local,
                    data_abertura,
                    situacao_cliente,
                    respondido,
                    retorno_call_center,
                    status_reclamacao,
                    problema_resolvido,
                    faria_negocio_novamente,
                    nota_atendimento
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    atipicidade_id,
                    dados["cliente"] or None,
                    dados["local"] or None,
                    dados["data_abertura"],
                    dados["situacao_cliente"] or None,
                    int(dados["respondido"]),
                    dados["retorno_call_center"] or None,
                    dados["status_reclamacao"],
                    converter_opcional(
                        dados["problema_resolvido"]
                    ),
                    converter_opcional(
                        dados["faria_negocio_novamente"]
                    ),
                    converter_opcional(
                        dados["nota_atendimento"]
                    )
                )
            )

            novo_id = cursor.lastrowid

        flash(
            f"Reclamação #{novo_id} cadastrada!",
            "sucesso"
        )

        return redirect(
            url_for(
                "reclame_aqui.detalhes",
                reclamacao_id=novo_id
            )
        )

    dados = {
        "atipicidade_id": request.args.get(
            "atipicidade_id", ""
        ),
        "cliente": "",
        "local": "",
        "data_abertura": date.today().isoformat(),
        "situacao_cliente": "",
        "respondido": "",
        "retorno_call_center": "",
        "status_reclamacao": "Em aberto",
        "problema_resolvido": "",
        "faria_negocio_novamente": "",
        "nota_atendimento": ""
    }

    return render_template(
        "reclame_aqui_form.html",
        dados=dados,
        hoje=date.today().isoformat(),
        status_opcoes=STATUS
    )


@reclame_aqui_bp.route("/<int:reclamacao_id>")
def detalhes(reclamacao_id):
    with conectar() as conexao:
        registro = conexao.execute(
            """
            SELECT
                r.id,
                r.atipicidade_id,
                r.data_abertura,
                r.situacao_cliente,
                r.respondido,
                r.retorno_call_center,
                r.status_reclamacao,
                r.problema_resolvido,
                r.faria_negocio_novamente,
                r.nota_atendimento,
                r.criado_em,
                r.atualizado_em,
                COALESCE(
                    NULLIF(TRIM(r.cliente), ''),
                    a.cliente
                ) AS cliente,
                COALESCE(
                    NULLIF(TRIM(r.local), ''),
                    a.local
                ) AS local,
                a.data_atipicidade,
                a.progresso
            FROM reclame_aqui AS r
            LEFT JOIN atipicidades AS a
                ON a.id = r.atipicidade_id
            WHERE r.id = ?
            """,
            (reclamacao_id,)
        ).fetchone()

    if registro is None:
        abort(404)

    return render_template(
        "reclame_aqui_detalhes.html",
        registro=registro
    )


@reclame_aqui_bp.route(
    "/<int:reclamacao_id>/editar",
    methods=["GET", "POST"]
)
def editar(reclamacao_id):
    with conectar() as conexao:
        registro = conexao.execute(
            """
            SELECT *
            FROM reclame_aqui
            WHERE id = ?
            """,
            (reclamacao_id,)
        ).fetchone()

    if registro is None:
        abort(404)

    if request.method == "POST":
        dados = ler_dados()
        erro = validar_dados(dados)

        if erro:
            flash(erro, "erro")

            return render_template(
                "reclame_aqui_form.html",
                dados=dados,
                hoje=date.today().isoformat(),
                status_opcoes=STATUS,
                reclamacao_id=reclamacao_id
            ), 400

        with conectar() as conexao:
            atipicidade_id, erro = verificar_vinculo(
                conexao,
                dados
            )

            if erro:
                flash(erro, "erro")

                return render_template(
                    "reclame_aqui_form.html",
                    dados=dados,
                    hoje=date.today().isoformat(),
                    status_opcoes=STATUS,
                    reclamacao_id=reclamacao_id
                ), 400

            conexao.execute(
                """
                UPDATE reclame_aqui
                SET
                    atipicidade_id = ?,
                    cliente = ?,
                    local = ?,
                    data_abertura = ?,
                    situacao_cliente = ?,
                    respondido = ?,
                    retorno_call_center = ?,
                    status_reclamacao = ?,
                    problema_resolvido = ?,
                    faria_negocio_novamente = ?,
                    nota_atendimento = ?,
                    atualizado_em = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    atipicidade_id,
                    dados["cliente"] or None,
                    dados["local"] or None,
                    dados["data_abertura"],
                    dados["situacao_cliente"] or None,
                    int(dados["respondido"]),
                    dados["retorno_call_center"] or None,
                    dados["status_reclamacao"],
                    converter_opcional(
                        dados["problema_resolvido"]
                    ),
                    converter_opcional(
                        dados["faria_negocio_novamente"]
                    ),
                    converter_opcional(
                        dados["nota_atendimento"]
                    ),
                    reclamacao_id
                )
            )

        flash(
            "Reclamação atualizada com sucesso!",
            "sucesso"
        )

        return redirect(
            url_for(
                "reclame_aqui.detalhes",
                reclamacao_id=reclamacao_id
            )
        )

    dados = dados_para_formulario(registro)

    return render_template(
        "reclame_aqui_form.html",
        dados=dados,
        hoje=date.today().isoformat(),
        status_opcoes=STATUS,
        reclamacao_id=reclamacao_id
    )
