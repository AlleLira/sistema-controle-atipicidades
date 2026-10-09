
# Contexto de Negócio e Requisitos

## Sistema de Controle de Atipicidades

**Tipo de projeto:** Aplicação local de gestão e acompanhamento operacional  
**Áreas relacionadas:** Auditoria, Análise de Dados e Business Intelligence  
**Tecnologias:** Python, Flask, SQLite e SQL  
**Status:** Funcional, com melhorias planejadas

---

## 1. Contexto de negócio

O Sistema de Controle de Atipicidades surgiu da identificação de uma necessidade real no acompanhamento de ocorrências operacionais relacionadas a processos de auditoria, atendimento e tratativas de clientes.

A gestão dessas ocorrências exige organização das informações, acompanhamento das tratativas, registro de devolutivas e monitoramento dos resultados.

Nesse contexto, surgiu a oportunidade de transformar uma necessidade operacional em uma solução tecnológica, aplicando conhecimentos de desenvolvimento de software, banco de dados, automação e análise de dados.

O projeto foi estruturado para centralizar informações, facilitar o acompanhamento das ocorrências e disponibilizar indicadores para análise gerencial.

## 2. Problema identificado

O cenário que motivou o desenvolvimento envolve desafios como:

- Necessidade de centralizar informações sobre ocorrências e tratativas.
- Dificuldade de acompanhar o progresso e os desfechos dos casos.
- Necessidade de preservar o histórico de devolutivas e alterações.
- Demanda por consultas e filtros para identificar pendências.
- Necessidade de consolidar indicadores gerenciais.
- Geração de relatórios para acompanhamento das informações.

## 3. Solução proposta

Desenvolvimento de uma aplicação local utilizando Python, Flask e SQLite, com funcionalidades de cadastro, consulta, atualização e acompanhamento de atipicidades.

A solução também contempla um módulo de reclamações, indicadores gerenciais e geração automatizada de relatórios PDF.

O projeto foi organizado de forma modular, permitindo futuras evoluções, incluindo a integração do banco de dados ao Power BI.

## 4. Objetivos

### 4.1. Objetivo geral

Transformar uma necessidade operacional em uma aplicação funcional, capaz de estruturar informações, melhorar a rastreabilidade dos registros e facilitar o acompanhamento das ocorrências e seus resultados.

### 4.2. Objetivos específicos

- Centralizar o cadastro das atipicidades.
- Padronizar as informações registradas.
- Permitir consultas e atualizações.
- Registrar devolutivas relacionadas às ocorrências.
- Preservar o histórico de alterações.
- Acompanhar o progresso e o desfecho dos casos.
- Gerenciar reclamações de consumidores.
- Disponibilizar indicadores gerenciais.
- Automatizar a geração de relatórios PDF.
- Preparar os dados para futuras análises no Power BI.

## 5. Escopo funcional

### 5.1. Controle de Atipicidades

- Cadastro de ocorrências.
- Consulta e aplicação de filtros.
- Atualização de registros.
- Acompanhamento de progresso.
- Classificação dos desfechos.
- Registro e edição de devolutivas.
- Histórico de alterações.

### 5.2. Reclame Aqui

- Cadastro de reclamações.
- Vinculação opcional a atipicidades.
- Acompanhamento de respostas e status.
- Registro de resolução.
- Avaliação de atendimento.
- Indicadores específicos.

### 5.3. Indicadores gerenciais

- Quantidade de ocorrências.
- Distribuição por progresso e desfecho.
- Taxa de finalização.
- Acompanhamento de pendências.
- Tempo médio de resolução.
- Análises por loja e período.
- Indicadores de respostas e resolução de reclamações.
- Avaliações de satisfação.

### 5.4. Relatórios

- Relatórios PDF individuais.
- Relatórios consolidados de atipicidades.
- Relatórios consolidados do Reclame Aqui.
- Relatório geral de acompanhamento.
- Aplicação de filtros.

## 6. Requisitos funcionais

| Código | Requisito | Status |
|---|---|---|
| RF01 | Cadastrar atipicidades | Implementado |
| RF02 | Consultar e filtrar ocorrências | Implementado |
| RF03 | Atualizar informações das atipicidades | Implementado |
| RF04 | Registrar devolutivas | Implementado |
| RF05 | Editar devolutivas | Implementado |
| RF06 | Registrar histórico de alterações | Implementado |
| RF07 | Acompanhar progresso e desfecho | Implementado |
| RF08 | Cadastrar reclamações | Implementado |
| RF09 | Vincular reclamações a atipicidades | Implementado |
| RF10 | Consultar e atualizar reclamações | Implementado |
| RF11 | Visualizar indicadores gerenciais | Implementado |
| RF12 | Gerar relatórios PDF individuais | Implementado |
| RF13 | Gerar relatórios PDF consolidados | Implementado |
| RF14 | Executar a aplicação localmente no Windows | Implementado |
| RF15 | Integrar os dados ao Power BI | Planejado |

## 7. Regras de negócio

### 7.1. Progresso das atipicidades

Os registros podem apresentar os seguintes estados:

- **Aberta:** ocorrência registrada e ainda em acompanhamento.
- **Aguardando loja:** ocorrência pendente de retorno ou tratativa.
- **Finalizado:** ocorrência com acompanhamento concluído.

### 7.2. Desfechos

Os desfechos disponíveis são:

- Pendente.
- Troca.
- Estorno.
- Negado.

### 7.3. Devolutivas

Uma atipicidade pode possuir múltiplas devolutivas.

As devolutivas são armazenadas separadamente e associadas à ocorrência correspondente.

### 7.4. Histórico de alterações

As edições realizadas nos registros são armazenadas para permitir a rastreabilidade das modificações.

O histórico de alterações permanece disponível na aplicação, mas não integra os relatórios PDF.

### 7.5. Reclamações

Uma reclamação pode existir independentemente ou estar vinculada a uma atipicidade cadastrada.

O sistema permite acompanhar seu status, resposta, resolução e avaliação.

### 7.6. Persistência dos dados

As informações são armazenadas em um banco SQLite local.

O banco é inicializado automaticamente quando necessário.

## 8. Requisitos não funcionais

| Código | Requisito | Descrição |
|---|---|---|
| RNF01 | Execução local | A aplicação funciona localmente |
| RNF02 | Persistência | Armazenamento de dados em SQLite |
| RNF03 | Interface | Navegação por páginas web |
| RNF04 | Modularidade | Separação dos principais módulos |
| RNF05 | Portabilidade | Empacotamento para Windows |
| RNF06 | Manutenibilidade | Código versionado com Git |
| RNF07 | Distribuição | Compilação automatizada com GitHub Actions |

## 9. Evoluções planejadas

- Integração do banco de dados ao Power BI.
- Ampliação dos indicadores gerenciais.
- Implementação de rotinas de backup e recuperação.
- Melhorias de segurança e distribuição.
- Expansão da documentação técnica.

## 10. Considerações sobre o portfólio

Este projeto foi desenvolvido a partir da identificação de uma necessidade operacional real.

Sua apresentação pública tem como objetivo demonstrar a aplicação prática de conhecimentos em desenvolvimento de software, automação, modelagem de dados e análise de informações.

As capturas de tela utilizadas no portfólio apresentam dados fictícios, criados exclusivamente para demonstração.

O projeto não deve divulgar informações confidenciais, dados reais de clientes ou processos internos protegidos.

---

**Autoria:** Alessandra Lira  
**GitHub:** https://github.com/AlleLira  
**LinkedIn:** https://www.linkedin.com/in/alessandra-lira-oliveira/
