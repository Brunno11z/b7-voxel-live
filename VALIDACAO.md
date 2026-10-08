# Validação da entrega

## Executado neste ambiente

- Python **3.12.14**, Linux, pygame-ce **2.5.8**, renderização SDL em modo headless.
- **34 testes automatizados aprovados**, na suíte atualizada.
- Importação e uso de classes reais de **TikTokLive 7.0.1** para normalizar mensagens sintéticas de presente/curtida.
- `compileall` para os arquivos Python e verificação sintática do JavaScript com `node --check`.
- Aplicativo principal iniciado com FastAPI/Uvicorn e loop pygame reais.
- Execução de 120 frames de uma partida de demonstração e geração de captura.
- Quatro cenas adicionais renderizadas: início, construção, diamante com ataque e defesa em 100%.
- Inspeção visual das capturas do jogo e comparação da composição com os quadros do vídeo.
- Pacotes principais disponíveis em wheels compatíveis com **Windows x64 / CPython 3.12**.
- Resolução limpa das dependências e constraints com `pip --dry-run --ignore-installed`, sem conflito.

## Mecânicas cobertas pela suíte

1. Contagem real de blocos, progresso, materiais e contorno irregular.
2. Ataques ZAP, TNT, BLACK HOLE e TORNADO com quantidade exata e suporte preservado.
3. Dez ações com multiplicação de presentes e deduplicação.
4. Combo acumulado 1 → 2 → 5 e finais repetidos sem recontagem.
5. Estratégia de combo sem ID de grupo, processado somente no final.
6. Cancelamento e reinício integral do tempo de defesa.
7. Regra alternativa de defesa sem cancelamento.
8. Uma vitória por rodada e novo ciclo após comemoração.
9. Filas de blocos extras nas duas políticas.
10. Meta com pausa ou reinício automático e limite opcional de placar negativo.
11. Construção independente da taxa de atualização.
12. Isolamento entre Teste/Live e vínculo por ID.
13. Curtidas por limiar, comentário normalizado e cooldown.
14. Mil ações intercaladas preservando os invariantes da grade.
15. Produtores concorrentes submetendo eventos a uma única fila de jogo.
16. Persistência e releitura de configurações.
17. Caminhada, salto, queda e ausência de interseção do personagem com blocos.
18. API local, rejeição de mutações sem sessão/origem, controle e WebSocket.
19. Normalização de objetos reais da biblioteca de eventos.
20. Mensagens de erro sem exposição de chave/URL.
21. Reconexão **com transporte simulado**, oito tentativas e esperas limitadas.
22. Falha de foto simulada sem bloquear o jogo.

## Painel: teste adicional de JavaScript + servidor real

Executado com DOM de teste (jsdom), API local real, WebSocket real e janela pygame headless:

- Carregamento inicial de configurações.
- Navegação pelas quatro áreas.
- Botão Iniciar alterando a partida real.
- Botão CHICKEN aplicando construção ao jogo real.
- Estado recebido por WebSocket.
- Salvamento automático da meta.
- Inclusão, gravação e remoção de vínculo de presente.
- Nenhum erro de JavaScript reportado nessa execução.

Este teste **não substitui a inspeção visual em um navegador**. O Chromium local não pôde iniciar devido à restrição de sockets deste ambiente. Por isso não há captura de navegador nem alegação de revisão visual completa do painel. A folha de estilos foi implementada para desktop, notebook e tablet.

## Não validado aqui

- Conexão de ponta a ponta com chave Euler real e conta transmitindo.
- Entrega efetiva de presentes, seguidores e outros eventos em uma live real.
- Reconexão contra os serviços reais, limites do plano ou variações de payload de uma conta específica.
- Instalação/execução dos arquivos .bat em Windows físico.
- DPAPI em um usuário Windows real.
- Benchmark de 60 FPS em Ryzen 5 5600GT ou teste de longa duração nesse hardware.
- Reprodução por alto-falantes e captura final no OBS/TikTok LIVE Studio.

A renderização dos sprites e as regras não visíveis no vídeo são aproximações próprias documentadas em `REFERENCIA.md`. Os testes passaram com três avisos de descontinuação de dependências (Starlette/httpx e APIs legadas de websockets); não houve falha de teste.

## Reproduzir

No Windows, execute `testar.bat` após a instalação.

Para gerar as capturas offline:

```text
.venv\Scripts\python.exe tools\render_previews.py
```

Os arquivos em `previews/` são capturas do renderer implementado, não ilustrações promocionais.

## Verificação da atualização 2.5D

Os 34 testes passaram após a troca do personagem. Dois novos testes verificam descrições/quantidades/vínculos e poses distintas da malha articulada. As quatro capturas foram geradas novamente pelo renderer 2.5D. A prévia do personagem também foi inspecionada em poses de repouso, caminhada, salto, construção e comemoração. O teste DOM + API + WebSocket do painel foi repetido com sucesso. As limitações de Windows físico, captura de navegador e live real continuam válidas.

## Revisão 2.1 — layout dos presentes

Revisão exclusivamente visual: painel inferior substituído por duas colunas laterais transparentes, com ícones, nomes e valores. As quatro capturas foram regeneradas e a cena de construção foi inspecionada. Não houve mudança de lógica de jogo; a suíte de 34 testes descrita acima corresponde à revisão 2.5D anterior.
