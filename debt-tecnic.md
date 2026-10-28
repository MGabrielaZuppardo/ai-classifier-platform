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
