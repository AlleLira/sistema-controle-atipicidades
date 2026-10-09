
from datetime import date, datetime

from flask import (
    Blueprint,
    render_template,
    request,
    abort,
    send_file
)

from reportlab.platypus import Paragraph

from database.db import conectar
from relatorios_pdf import (
    estilos_pdf,
    adicionar_titulo,
    adicionar_secao,
    adicionar_campos,
    adicionar_texto,
    adicionar_reclamacao,
    gerar_documento,
    data_br,
    moeda
)


central_relatorios_bp = Blueprint(
    "central_relatorios",
    __name__,
    url_prefix="/relatorios"
)

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

STATUS = (
    "Em aberto",
    "Aguardando resposta",
    "Respondida",
    "Aguardando avaliação",
    "Finalizada"
)


def obter_filtros():
    return {
        chave: request.args.get(chave, "").strip()
        for chave in (
            "tipo",
            "data_inicio",
            "data_fim",
            "loja",
            "progresso",
            "desfecho",
            "status",
            "respondido"
        )
    }


def validar_filtros(filtros):
    if filtros["tipo"] not in (
        "atipicidades",
        "reclame_aqui",
        "geral"
    ):
        abort(400, "Tipo de relatório inválido.")

    for campo in ("data_inicio", "data_fim"):
        if filtros[campo]:
            try:
                date.fromisoformat(filtros[campo])
            except ValueError:
                abort(400, "Data inválida.")

    if (
        filtros["data_inicio"]
        and filtros["data_fim"]
        and filtros["data_inicio"] > filtros["data_fim"]
    ):
        abort(400, "O período informado é inválido.")

    if filtros["progresso"] and filtros["progresso"] not in PROGRESSOS:
        abort(400, "Progresso inválido.")

    if filtros["desfecho"] and filtros["desfecho"] not in DESFECHOS:
        abort(400, "Desfecho inválido.")

    if filtros["status"] and filtros["status"] not in STATUS:
        abort(400, "Status inválido.")

    if filtros["respondido"] not in ("", "0", "1"):
        abort(400, "Filtro de resposta inválido.")


def consultar_atipicidades(conexao, filtros):
    consulta = """
        SELECT *
        FROM atipicidades
        WHERE 1 = 1
    """

    parametros = []

    if filtros["data_inicio"]:
        consulta += " AND data_atipicidade >= ?"
        parametros.append(filtros["data_inicio"])

    if filtros["data_fim"]:
        consulta += " AND data_atipicidade <= ?"
        parametros.append(filtros["data_fim"])

    if filtros["loja"]:
        consulta += " AND TRIM(COALESCE(local, '')) = ?"
        parametros.append(filtros["loja"])

    if filtros["progresso"]:
        consulta += " AND progresso = ?"
        parametros.append(filtros["progresso"])

    if filtros["desfecho"]:
        consulta += " AND desfecho = ?"
        parametros.append(filtros["desfecho"])

    consulta += " ORDER BY data_atipicidade DESC, id DESC"

    return [
        dict(linha)
        for linha in conexao.execute(
            consulta,
            parametros
        ).fetchall()
    ]


def consultar_reclamacoes(conexao, filtros, ids=None):
    consulta = """
        SELECT
            r.*,
            COALESCE(
                NULLIF(TRIM(r.cliente), ''),
                a.cliente
            ) AS cliente_exibicao,
            COALESCE(
                NULLIF(TRIM(r.local), ''),
                a.local
            ) AS local_exibicao
        FROM reclame_aqui AS r
        LEFT JOIN atipicidades AS a
            ON a.id = r.atipicidade_id
        WHERE 1 = 1
    """

    parametros = []

    if ids is not None:
        if not ids:
            return []

        marcadores = ",".join("?" for _ in ids)
        consulta += f" AND r.atipicidade_id IN ({marcadores})"
        parametros.extend(ids)

    if filtros["data_inicio"]:
        consulta += " AND r.data_abertura >= ?"
        parametros.append(filtros["data_inicio"])

    if filtros["data_fim"]:
        consulta += " AND r.data_abertura <= ?"
        parametros.append(filtros["data_fim"])

    if filtros["loja"]:
        consulta += """
            AND COALESCE(
                NULLIF(TRIM(r.local), ''),
                NULLIF(TRIM(a.local), ''),
                'Não informada'
            ) = ?
        """
        parametros.append(filtros["loja"])

    if filtros["status"]:
        consulta += " AND r.status_reclamacao = ?"
        parametros.append(filtros["status"])

    if filtros["respondido"] != "":
        consulta += " AND r.respondido = ?"
        parametros.append(int(filtros["respondido"]))

    consulta += " ORDER BY r.data_abertura DESC, r.id DESC"

    registros = []

    for linha in conexao.execute(
        consulta,
        parametros
    ).fetchall():
        registro = dict(linha)
        registro["cliente"] = registro["cliente_exibicao"]
        registro["local"] = registro["local_exibicao"]
        registros.append(registro)

    return registros


@central_relatorios_bp.route("/")
def pagina():
    with conectar() as conexao:
        lojas = [
            linha["loja"]
            for linha in conexao.execute(
                """
                SELECT loja
                FROM (
                    SELECT TRIM(local) AS loja
                    FROM atipicidades
                    UNION
                    SELECT TRIM(local) AS loja
                    FROM reclame_aqui
                )
                WHERE loja IS NOT NULL
                  AND loja != ''
                ORDER BY loja COLLATE NOCASE
                """
            ).fetchall()
        ]

    if "Não informada" not in lojas:
        lojas.append("Não informada")

    return render_template(
        "central_relatorios.html",
        lojas=lojas,
        progressos=PROGRESSOS,
        desfechos=DESFECHOS,
        status_opcoes=STATUS
    )


@central_relatorios_bp.route("/gerar")
def gerar():
    filtros = obter_filtros()
    validar_filtros(filtros)

    tipo = filtros["tipo"]

    with conectar() as conexao:
        atipicidades = (
            consultar_atipicidades(conexao, filtros)
            if tipo in ("atipicidades", "geral")
            else []
        )

        if tipo == "reclame_aqui":
            reclamacoes = consultar_reclamacoes(
                conexao,
                filtros
            )
        elif tipo == "geral":
            reclamacoes = consultar_reclamacoes(
                conexao,
                filtros
            )
        else:
            reclamacoes = []

        if tipo == "geral":
            ids = [item["id"] for item in atipicidades]
            vinculadas = consultar_reclamacoes(
                conexao,
                {
                    **filtros,
                    "data_inicio": "",
                    "data_fim": "",
                    "status": "",
                    "respondido": "",
                    "loja": ""
                },
                ids
            )

            existentes = {
                item["id"] for item in reclamacoes
            }

            for item in vinculadas:
                if item["id"] not in existentes:
                    reclamacoes.append(item)
                    existentes.add(item["id"])

    estilos = estilos_pdf()
    elementos = []

    titulos = {
        "atipicidades": "Relatório de Atipicidades",
        "reclame_aqui": "Relatório Reclame Aqui",
        "geral": "Relatório Geral de Acompanhamento"
    }

    adicionar_titulo(
        elementos,
        estilos,
        titulos[tipo],
        f"Emitido em {datetime.now().strftime('%d/%m/%Y às %H:%M')}"
    )

    periodo = (
        f"{data_br(filtros['data_inicio']) if filtros['data_inicio'] else 'Início'}"
        f" até "
        f"{data_br(filtros['data_fim']) if filtros['data_fim'] else 'Hoje'}"
    )

    adicionar_secao(
        elementos,
        estilos,
        "Resumo do relatório"
    )

    resumo = [("Período selecionado", periodo)]

    if filtros["loja"]:
        resumo.append(("Loja", filtros["loja"]))

    if tipo in ("atipicidades", "geral"):
        resumo.append((
            "Total de atipicidades",
            len(atipicidades)
        ))

        resumo.append((
            "Em aberto",
            sum(
                item["progresso"] == "Aberta"
                for item in atipicidades
            )
        ))

        resumo.append((
            "Aguardando loja",
            sum(
                item["progresso"] == "Aguardando loja"
                for item in atipicidades
            )
        ))

        resumo.append((
            "Finalizadas",
            sum(
                item["progresso"] == "Finalizado"
                for item in atipicidades
            )
        ))

    if tipo in ("reclame_aqui", "geral"):
        resumo.append((
            "Total de reclamações",
            len(reclamacoes)
        ))

        resumo.append((
            "Reclamações respondidas",
            sum(
                item["respondido"] == 1
                for item in reclamacoes
            )
        ))

        resumo.append((
            "Problemas resolvidos",
            sum(
                item["problema_resolvido"] == 1
                for item in reclamacoes
            )
        ))

    adicionar_campos(
        elementos,
        estilos,
        resumo
    )

    if tipo in ("atipicidades", "geral"):
        adicionar_secao(
            elementos,
            estilos,
            "Atipicidades"
        )

        if not atipicidades:
            elementos.append(
                Paragraph(
                    "Nenhuma atipicidade encontrada.",
                    estilos["texto"]
                )
            )

        for item in atipicidades:
            adicionar_secao(
                elementos,
                estilos,
                f"Atipicidade #{item['id']}"
            )

            adicionar_campos(
                elementos,
                estilos,
                [
                    ("Data", data_br(
                        item["data_atipicidade"]
                    )),
                    ("Cliente", item["cliente"]),
                    ("Loja", item["local"]),
                    ("Controle", item["controle"]),
                    ("Call Center", item["call_center"]),
                    ("Progresso", item["progresso"]),
                    ("Desfecho", item["desfecho"]),
                    ("Histórico de compra", moeda(
                        item["historico_compra"]
                    )),
                    ("Produtos trocados", item[
                        "produtos_trocados"
                    ])
                ]
            )

            adicionar_texto(
                elementos,
                estilos,
                "Situação",
                item["situacao"]
            )

            adicionar_texto(
                elementos,
                estilos,
                "Resolutiva final",
                item["resolutiva_final"]
            )

    if tipo in ("reclame_aqui", "geral"):
        adicionar_secao(
            elementos,
            estilos,
            "Reclamações do Reclame Aqui"
        )

        if not reclamacoes:
            elementos.append(
                Paragraph(
                    "Nenhuma reclamação encontrada.",
                    estilos["texto"]
                )
            )

        for item in reclamacoes:
            adicionar_reclamacao(
                elementos,
                estilos,
                item
            )

    memoria = gerar_documento(elementos)

    return send_file(
        memoria,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"relatorio_{tipo}.pdf"
    )
