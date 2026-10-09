
from io import BytesIO
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from xml.sax.saxutils import escape

from flask import Blueprint, abort, send_file
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable
)

from database.db import conectar


relatorios_pdf_bp = Blueprint(
    "relatorios_pdf",
    __name__
)

ROXO = colors.HexColor("#7453A6")
ROXO_ESCURO = colors.HexColor("#49336D")
LILAS = colors.HexColor("#F1EBF8")
CINZA = colors.HexColor("#62616B")
BORDA = colors.HexColor("#E6DFED")
BRANCO = colors.white


def texto(valor, vazio="Não informado"):
    if valor is None or str(valor).strip() == "":
        return vazio

    return str(valor)


def seguro(valor, vazio="Não informado"):
    return escape(texto(valor, vazio)).replace(
        "\n", "<br/>"
    )


def data_br(valor):
    if not valor:
        return "Não informada"

    try:
        return date.fromisoformat(
            str(valor)[:10]
        ).strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return str(valor)


def data_hora_br(valor):
    if not valor:
        return "Não informado"

    try:
        return datetime.fromisoformat(
            str(valor)
        ).strftime("%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        return str(valor)


def moeda(valor):
    if valor is None or str(valor).strip() == "":
        return "Não informado"

    try:
        numero = Decimal(str(valor))
        formatado = f"{numero:,.2f}"

        return (
            "R$ "
            + formatado.replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )
    except (InvalidOperation, ValueError):
        return str(valor)


def sim_nao(valor):
    if valor is None:
        return "Não informado"

    return "Sim" if int(valor) == 1 else "Não"


def estilos_pdf():
    return {
        "titulo": ParagraphStyle(
            "TituloRelatorio",
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=23,
            textColor=ROXO_ESCURO,
            spaceAfter=7
        ),
        "subtitulo": ParagraphStyle(
            "SubtituloRelatorio",
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=CINZA,
            spaceAfter=13
        ),
        "secao": ParagraphStyle(
            "SecaoRelatorio",
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=ROXO_ESCURO,
            spaceBefore=14,
            spaceAfter=8
        ),
        "rotulo": ParagraphStyle(
            "RotuloRelatorio",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=ROXO_ESCURO
        ),
        "valor": ParagraphStyle(
            "ValorRelatorio",
            fontName="Helvetica",
            fontSize=9,
            leading=14,
            textColor=colors.HexColor("#33313A")
        ),
        "texto": ParagraphStyle(
            "TextoRelatorio",
            fontName="Helvetica",
            fontSize=9,
            leading=15,
            textColor=colors.HexColor("#33313A"),
            spaceAfter=7
        ),
        "pequeno": ParagraphStyle(
            "PequenoRelatorio",
            fontName="Helvetica",
            fontSize=8,
            leading=12,
            textColor=CINZA
        )
    }


def adicionar_titulo(elementos, estilos, titulo, subtitulo):
    elementos.append(
        Paragraph(seguro(titulo), estilos["titulo"])
    )

    elementos.append(
        Paragraph(seguro(subtitulo), estilos["subtitulo"])
    )

    elementos.append(
        HRFlowable(
            width="100%",
            thickness=1.5,
            color=ROXO,
            spaceAfter=10
        )
    )


def adicionar_secao(elementos, estilos, titulo):
    elementos.append(
        Paragraph(seguro(titulo), estilos["secao"])
    )


def adicionar_campos(elementos, estilos, campos):
    linhas = []

    for rotulo, valor in campos:
        linhas.append([
            Paragraph(
                seguro(rotulo),
                estilos["rotulo"]
            ),
            Paragraph(
                seguro(valor),
                estilos["valor"]
            )
        ])

    if not linhas:
        return

    tabela = Table(
        linhas,
        colWidths=[52 * mm, 128 * mm],
        hAlign="LEFT"
    )

    tabela.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LILAS),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [
                BRANCO,
                LILAS
            ]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 9),
            ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, BORDA)
        ])
    )

    elementos.append(tabela)


def adicionar_texto(elementos, estilos, rotulo, valor):
    bloco = [
        Paragraph(
            seguro(rotulo),
            estilos["rotulo"]
        ),
        Spacer(1, 3),
        Paragraph(
            seguro(valor),
            estilos["texto"]
        ),
        Spacer(1, 6)
    ]

    elementos.append(KeepTogether(bloco))


def adicionar_reclamacao(elementos, estilos, reclamacao):
    adicionar_secao(
        elementos,
        estilos,
        f"Reclame Aqui #{reclamacao['id']}"
    )

    adicionar_campos(
        elementos,
        estilos,
        [
            ("Data de abertura", data_br(
                reclamacao["data_abertura"]
            )),
            ("Cliente", reclamacao["cliente"]),
            ("Loja", reclamacao["local"]),
            ("Status", reclamacao["status_reclamacao"]),
            ("Respondida", sim_nao(
                reclamacao["respondido"]
            )),
            ("Problema resolvido", sim_nao(
                reclamacao["problema_resolvido"]
            )),
            ("Faria negócio novamente", sim_nao(
                reclamacao["faria_negocio_novamente"]
            )),
            ("Nota do atendimento", reclamacao[
                "nota_atendimento"
            ])
        ]
    )

    elementos.append(Spacer(1, 8))

    adicionar_texto(
        elementos,
        estilos,
        "Situação do cliente",
        reclamacao["situacao_cliente"]
    )

    adicionar_texto(
        elementos,
        estilos,
        "Retorno do Call Center",
        reclamacao["retorno_call_center"]
    )


def rodape(canvas, documento):
    canvas.saveState()

    largura, altura = A4

    canvas.setStrokeColor(BORDA)
    canvas.line(
        15 * mm,
        17 * mm,
        largura - 15 * mm,
        17 * mm
    )

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(CINZA)

    canvas.drawString(
        15 * mm,
        12 * mm,
        "Sistema de Controle de Atipicidades"
    )

    canvas.drawRightString(
        largura - 15 * mm,
        12 * mm,
        f"Página {documento.page}"
    )

    canvas.restoreState()


def gerar_documento(elementos):
    memoria = BytesIO()

    documento = SimpleDocTemplate(
        memoria,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=17 * mm,
        bottomMargin=24 * mm,
        title="Relatório de acompanhamento",
        author="Sistema de Controle de Atipicidades"
    )

    documento.build(
        elementos,
        onFirstPage=rodape,
        onLaterPages=rodape
    )

    memoria.seek(0)

    return memoria


def buscar_reclamacoes(conexao, atipicidade_id):
    registros = conexao.execute(
        """
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
        WHERE r.atipicidade_id = ?
        ORDER BY r.data_abertura, r.id
        """,
        (atipicidade_id,)
    ).fetchall()

    resultado = []

    for linha in registros:
        registro = dict(linha)
        registro["cliente"] = registro["cliente_exibicao"]
        registro["local"] = registro["local_exibicao"]
        resultado.append(registro)

    return resultado


@relatorios_pdf_bp.route(
    "/atipicidades/<int:atipicidade_id>/pdf"
)
def pdf_atipicidade(atipicidade_id):
    with conectar() as conexao:
        atipicidade = conexao.execute(
            """
            SELECT *
            FROM atipicidades
            WHERE id = ?
            """,
            (atipicidade_id,)
        ).fetchone()

        if atipicidade is None:
            abort(404)

        atipicidade = dict(atipicidade)

        devolutivas = [
            dict(linha)
            for linha in conexao.execute(
                """
                SELECT *
                FROM devolutivas
                WHERE atipicidade_id = ?
                ORDER BY criado_em, id
                """,
                (atipicidade_id,)
            ).fetchall()
        ]

        historico = [
            dict(linha)
            for linha in conexao.execute(
                """
                SELECT *
                FROM historico_edicoes
                WHERE atipicidade_id = ?
                ORDER BY alterado_em, id
                """,
                (atipicidade_id,)
            ).fetchall()
        ]

        reclamacoes = buscar_reclamacoes(
            conexao,
            atipicidade_id
        )

    estilos = estilos_pdf()
    elementos = []

    adicionar_titulo(
        elementos,
        estilos,
        f"Relatório da Atipicidade #{atipicidade_id}",
        f"Emitido em {datetime.now().strftime('%d/%m/%Y às %H:%M')}"
    )

    adicionar_secao(
        elementos,
        estilos,
        "Informações gerais"
    )

    adicionar_campos(
        elementos,
        estilos,
        [
            ("Data da atipicidade", data_br(
                atipicidade["data_atipicidade"]
            )),
            ("Call Center", atipicidade["call_center"]),
            ("Controle", atipicidade["controle"]),
            ("Cliente", atipicidade["cliente"]),
            ("Data da compra", data_br(
                atipicidade["data_compra"]
            )),
            ("Local / Loja", atipicidade["local"]),
            ("Acessório", atipicidade["acessorio"]),
            ("Prazo de garantias", atipicidade[
                "prazo_garantias"
            ])
        ]
    )

    adicionar_secao(
        elementos,
        estilos,
        "Compra e situação"
    )

    adicionar_campos(
        elementos,
        estilos,
        [
            ("Histórico de compra", moeda(
                atipicidade["historico_compra"]
            )),
            ("Produtos trocados", atipicidade[
                "produtos_trocados"
            ])
        ]
    )

    adicionar_texto(
        elementos,
        estilos,
        "Situação — relato da atipicidade",
        atipicidade["situacao"]
    )

    adicionar_secao(
        elementos,
        estilos,
        "Acompanhamento e resolução"
    )

    adicionar_campos(
        elementos,
        estilos,
        [
            ("Progresso", atipicidade["progresso"]),
            ("Desfecho", atipicidade["desfecho"]),
            ("Data de finalização", data_hora_br(
                atipicidade["finalizado_em"]
            ))
        ]
    )

    adicionar_texto(
        elementos,
        estilos,
        "Resolutiva final",
        atipicidade["resolutiva_final"]
    )

    adicionar_secao(
        elementos,
        estilos,
        f"Devolutivas ({len(devolutivas)})"
    )

    if devolutivas:
        for devolutiva in devolutivas:
            adicionar_texto(
                elementos,
                estilos,
                (
                    f"Devolutiva #{devolutiva['id']} — "
                    f"{data_hora_br(devolutiva['criado_em'])} UTC"
                ),
                devolutiva["texto"]
            )
    else:
        elementos.append(
            Paragraph(
                "Nenhuma devolutiva registrada.",
                estilos["pequeno"]
            )
        )


    adicionar_secao(
        elementos,
        estilos,
        f"Reclame Aqui vinculado ({len(reclamacoes)})"
    )

    if reclamacoes:
        for reclamacao in reclamacoes:
            adicionar_reclamacao(
                elementos,
                estilos,
                reclamacao
            )
    else:
        elementos.append(
            Paragraph(
                "Nenhuma reclamação vinculada a esta atipicidade.",
                estilos["pequeno"]
            )
        )

    memoria = gerar_documento(elementos)

    return send_file(
        memoria,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=(
            f"atipicidade_{atipicidade_id}_completo.pdf"
        )
    )


@relatorios_pdf_bp.route(
    "/reclame-aqui/<int:reclamacao_id>/pdf"
)
def pdf_reclame_aqui(reclamacao_id):
    with conectar() as conexao:
        reclamacao = conexao.execute(
            """
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
            WHERE r.id = ?
            """,
            (reclamacao_id,)
        ).fetchone()

    if reclamacao is None:
        abort(404)

    reclamacao = dict(reclamacao)
    reclamacao["cliente"] = reclamacao["cliente_exibicao"]
    reclamacao["local"] = reclamacao["local_exibicao"]

    estilos = estilos_pdf()
    elementos = []

    adicionar_titulo(
        elementos,
        estilos,
        f"Relatório Reclame Aqui #{reclamacao_id}",
        f"Emitido em {datetime.now().strftime('%d/%m/%Y às %H:%M')}"
    )

    adicionar_secao(
        elementos,
        estilos,
        "Identificação da reclamação"
    )

    adicionar_campos(
        elementos,
        estilos,
        [
            (
                "Atipicidade vinculada",
                (
                    f"#{reclamacao['atipicidade_id']}"
                    if reclamacao["atipicidade_id"]
                    else "Sem vínculo"
                )
            ),
            ("Cliente", reclamacao["cliente"]),
            ("Loja", reclamacao["local"]),
            ("Data de abertura", data_br(
                reclamacao["data_abertura"]
            )),
            ("Status", reclamacao["status_reclamacao"]),
            ("Respondida", sim_nao(
                reclamacao["respondido"]
            ))
        ]
    )

    adicionar_secao(
        elementos,
        estilos,
        "Descrição e atendimento"
    )

    adicionar_texto(
        elementos,
        estilos,
        "Situação do cliente",
        reclamacao["situacao_cliente"]
    )

    adicionar_texto(
        elementos,
        estilos,
        "Retorno do Call Center",
        reclamacao["retorno_call_center"]
    )

    adicionar_secao(
        elementos,
        estilos,
        "Avaliação do consumidor"
    )

    adicionar_campos(
        elementos,
        estilos,
        [
            ("Problema resolvido", sim_nao(
                reclamacao["problema_resolvido"]
            )),
            ("Faria negócio novamente", sim_nao(
                reclamacao["faria_negocio_novamente"]
            )),
            ("Nota do atendimento", reclamacao[
                "nota_atendimento"
            ])
        ]
    )

    adicionar_secao(
        elementos,
        estilos,
        "Informações do registro"
    )

    adicionar_campos(
        elementos,
        estilos,
        [
            ("Criado em", data_hora_br(
                reclamacao["criado_em"]
            )),
            ("Atualizado em", data_hora_br(
                reclamacao["atualizado_em"]
            ))
        ]
    )

    memoria = gerar_documento(elementos)

    return send_file(
        memoria,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=(
            f"reclame_aqui_{reclamacao_id}.pdf"
        )
    )
