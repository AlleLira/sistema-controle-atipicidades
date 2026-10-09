
from database.db import conectar


def inicializar_reclame_aqui():
    with conectar() as conexao:
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS reclame_aqui (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                atipicidade_id INTEGER,
                cliente TEXT,
                local TEXT,
                data_abertura TEXT NOT NULL,
                situacao_cliente TEXT,
                respondido INTEGER NOT NULL DEFAULT 0,
                retorno_call_center TEXT,
                status_reclamacao TEXT NOT NULL
                    DEFAULT 'Em aberto',
                problema_resolvido INTEGER,
                faria_negocio_novamente INTEGER,
                nota_atendimento INTEGER,
                criado_em TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (atipicidade_id)
                    REFERENCES atipicidades(id)
            )
            """
        )

        colunas = {
            coluna["name"]: coluna
            for coluna in conexao.execute(
                "PRAGMA table_info(reclame_aqui)"
            ).fetchall()
        }

        if (
            "atipicidade_id" in colunas
            and colunas["atipicidade_id"]["notnull"] == 1
        ):
            raise RuntimeError(
                "A tabela reclame_aqui utiliza uma estrutura antiga. "
                "É necessária uma migração segura antes de cadastrar "
                "reclamações independentes. Nenhum registro foi excluído."
            )

        conexao.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_reclame_aqui_atipicidade
            ON reclame_aqui(atipicidade_id)
            """
        )

        conexao.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_reclame_aqui_data
            ON reclame_aqui(data_abertura)
            """
        )
