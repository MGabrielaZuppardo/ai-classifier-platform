# Débito técnico e pendências

Itens adiados de propósito para não travar o desenvolvimento. Cada item tem um gatilho: o que deve acontecer para que ele volte a ser prioridade.

## DT-001: Dataset externo de outro domínio

- **Status:** pendente
- **Contexto:** a especificação prevê um terceiro dataset, de outro domínio (por exemplo espécies de plantas ou animais), para testar a adaptação do pipeline. O MVP começa apenas com o CIFAR-10.
- **Decisão pendente:** escolher o dataset (domínio, licença, tamanho, número de classes) e a forma de ingestão (zip por pasta ou CSV).
- **Gatilho:** se a falta dessa escolha começar a travar o desenvolvimento (por exemplo ao fechar o adaptador genérico de datasets ou os testes de upload), sinalizar para fechar a pendência. Antes da Fase 3 terminar, o pipeline precisa ter sido exercitado com ao menos um dataset enviado por upload, mesmo que seja um subconjunto do CIFAR-10 empacotado como zip.
- **Critério de pronto:** dataset escolhido, adaptador funcionando e resultado registrado no protocolo de avaliação, com o aviso de que o desempenho precisa ser medido de novo no novo domínio.
- **Referência:** README, seção "Estratégia de Deep Learning".

## DT-002: Classificação multi-label

- **Status:** adiado. O MVP é single-label (decisão confirmada).
- **Contexto:** o README assume classificação single-label. Suportar multi-label muda a função de perda (BCE em vez de cross-entropy), as métricas (F1 por rótulo, mAP, limiar por classe), o formato do CSV e a camada final do modelo.
- **Recomendação registrada:** MVP em single-label. Multi-label entra depois, com o formato do CSV já pensado para comportar vários rótulos por imagem.
- **Referência:** README, seção "Escopo do MVP".

## DT-003: Limpeza de refresh tokens expirados e revogados

- **Status:** pendente
- **Contexto:** a tabela `refresh_tokens` guarda um registro por rotação (um por uso do refresh). Registros expirados, usados ou revogados não são removidos.
- **Decisão pendente:** rotina periódica (comando ou tarefa agendada) que apague os expirados há mais de N dias. Manter por um tempo os registros usados serve para detectar reutilização, então a janela de retenção deve ser pelo menos a validade do token (30 dias).
- **Gatilho:** quando o worker/agendador existir (etapa de treinamento assíncrono) ou a tabela passar de algumas centenas de milhares de linhas.
- **Critério de pronto:** rotina agendada, com teste de integração que confirme que só os registros vencidos e fora da janela são apagados.

## DT-004: Validar o cabeçalho `Origin` em `/refresh` e `/logout`

- **Status:** pendente
- **Contexto:** hoje a proteção contra CSRF nessas rotas depende de `SameSite=Strict` e de front e API ficarem no mesmo site. Validar `Origin` é defesa em profundidade para navegadores antigos ou configurações atípicas.
- **Decisão pendente:** lista de origens permitidas por configuração (`APP_ALLOWED_ORIGINS`) e comportamento quando o cabeçalho está ausente.
- **Gatilho:** antes da publicação (Fase 6) ou quando front e API passarem a ficar em sites diferentes.
- **Critério de pronto:** requisição com `Origin` não permitido recebe 403, com testes.

## DT-005: Callback do GitHub devolve o access token no corpo

- **Status:** pendente
- **Contexto:** sem front, o callback responde JSON com o access token. O desenho final é redirecionar ao front com o cookie de refresh já definido, e o front chamar `POST /api/v1/auth/refresh` para obter o access token, que fica só em memória.
- **Gatilho:** início do esqueleto do frontend Angular.
- **Critério de pronto:** callback redireciona para a URL do front (configurável) sem expor token na URL nem no corpo.

## DT-006: Validar o login com um GitHub real

- **Status:** pendente
- **Contexto:** o adaptador do Authlib só foi exercitado com um GitHub simulado. Falta registrar um OAuth App (um por ambiente, com a URL de retorno correta) e testar à mão o fluxo completo: autorização com PKCE, leitura do e-mail primário verificado e a regra de 7 dias.
- **Gatilho:** antes da primeira entrega em staging.
- **Critério de pronto:** login real funcionando em desenvolvimento e registrado como validado.

## DT-007: Calibrar o limiar de duplicatas perceptuais

- **Status:** pendente (entra com o módulo de datasets)
- **Contexto:** a decisão foi usar hash exato (SHA-256) mais hash perceptual, com distância de Hamming em torno de 4 de 64 bits como ponto de partida. O valor precisa ser calibrado com amostras reais.
- **Critério de pronto:** limiar escolhido com base em exemplos de duplicatas e de imagens distintas, e registrado na documentação.
