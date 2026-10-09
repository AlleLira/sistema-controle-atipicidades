
import os
import sqlite3
import sys
from pathlib import Path


def obter_diretorio_dados():
    caminho_configurado = os.environ.get(
        "ATIPICIDADES_DATA_DIR",
        ""
    ).strip()

    if caminho_configurado:
        return Path(caminho_configurado).expanduser().resolve()

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "data"

    return Path(__file__).resolve().parent.parent / "data"


DATA_DIR = obter_diretorio_dados()
DB_PATH = DATA_DIR / "atipicidades.db"


def conectar():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    conexao = sqlite3.connect(
        DB_PATH,
        timeout=30
    )

    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    conexao.execute("PRAGMA busy_timeout = 30000")

    return conexao


def inicializar_banco():
    with conectar() as conexao:
        conexao.executescript(
            """
            CREATE TABLE IF NOT EXISTS atipicidades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_atipicidade TEXT NOT NULL,
                call_center TEXT,
                controle TEXT,
                cliente TEXT NOT NULL,
                data_compra TEXT,
                acessorio TEXT,
                historico_compra TEXT,
                local TEXT,
                produtos_trocados TEXT,
                prazo_garantias TEXT,
                progresso TEXT NOT NULL
                    DEFAULT 'Aberta'
                    CHECK (
                        progresso IN (
                            'Aberta',
                            'Aguardando loja',
                            'Finalizado'
                        )
                    ),
                desfecho TEXT NOT NULL
                    DEFAULT 'Pendente'
                    CHECK (
                        desfecho IN (
                            'Pendente',
                            'Troca',
                            'Estorno',
                            'Negado'
                        )
                    ),
                resolutiva_final TEXT,
                situacao TEXT,
                criado_em TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                finalizado_em TEXT
            );

            CREATE TABLE IF NOT EXISTS devolutivas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                atipicidade_id INTEGER NOT NULL,
                texto TEXT NOT NULL,
                criado_em TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (atipicidade_id)
                    REFERENCES atipicidades(id)
            );

            CREATE TABLE IF NOT EXISTS historico_edicoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                atipicidade_id INTEGER NOT NULL,
                devolutiva_id INTEGER,
                campo TEXT NOT NULL,
                valor_anterior TEXT,
                valor_novo TEXT,
                alterado_em TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (atipicidade_id)
                    REFERENCES atipicidades(id),
                FOREIGN KEY (devolutiva_id)
                    REFERENCES devolutivas(id)
            );

            CREATE INDEX IF NOT EXISTS
                idx_atipicidades_cliente
            ON atipicidades(cliente);

            CREATE INDEX IF NOT EXISTS
                idx_atipicidades_controle
            ON atipicidades(controle);

            CREATE INDEX IF NOT EXISTS
                idx_devolutivas_atipicidade
            ON devolutivas(atipicidade_id);
            """
        )

        colunas = {
            coluna["name"]
            for coluna in conexao.execute(
                "PRAGMA table_info(atipicidades)"
            ).fetchall()
        }

        if "desfecho" not in colunas:
            conexao.execute(
                """
                ALTER TABLE atipicidades
                ADD COLUMN desfecho TEXT NOT NULL
                    DEFAULT 'Pendente'
                    CHECK (
                        desfecho IN (
                            'Pendente',
                            'Troca',
                            'Estorno',
                            'Negado'
                        )
                    )
                """
            )

        if "finalizado_em" not in colunas:
            conexao.execute(
                """
                ALTER TABLE atipicidades
                ADD COLUMN finalizado_em TEXT
                """
            )

        conexao.execute(
            """
            UPDATE atipicidades
            SET finalizado_em = COALESCE(
                atualizado_em,
                criado_em
            )
            WHERE progresso = 'Finalizado'
              AND finalizado_em IS NULL
            """
        )

        conexao.commit()
