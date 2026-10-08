# B7 VOXEL LIVE — 2.5D

Jogo de construção interativa em Python para Windows, com painel local e conector TikTokLive + Euler. O vídeo fornecido orientou o enquadramento vertical, os blocos, a câmera, as ações e o ciclo de defesa. Os desenhos, texturas e sons deste projeto são novos: não são arquivos extraídos do jogo do vídeo.

## Comece aqui

1. Extraia **toda a pasta** do ZIP para um local gravável, por exemplo `Documentos\B7_Voxel_Live`. Não execute de dentro do ZIP ou de `Arquivos de Programas`.
2. Instale **Python 3.12 de 64 bits**, com **Python Launcher**. O instalador oficial 3.12.10 está em https://www.python.org/downloads/release/python-31210/ .
3. Abra **instalar.bat**. A primeira instalação precisa de internet para baixar as dependências. Se houver erro, a janela permanece aberta com o motivo.
4. Abra **iniciar.bat**. Serão abertas a janela **B7 VOXEL LIVE** e a página http://127.0.0.1:5000 .
5. Clique em **Iniciar jogo**. O projeto começa no modo **Teste offline** e não exige chave para jogar ou experimentar os efeitos.
6. Entre em **Testes** e clique nos presentes para construir e destruir. Informe nome, quantidade e, opcionalmente, URL HTTPS de uma foto.

Mantenha a janela do jogo aberta. Fechar a janela ou pressionar Esc encerra também o servidor local. A barra de espaço alterna pausa. Abrir outra aba do painel reutiliza a mesma partida. A porta 5000 impede duas instâncias do aplicativo.

## Conectar sua live

1. Inicie uma live no TikTok e obtenha sua chave no painel da Euler Stream.
2. Em **Início**, informe somente o `@usuario`, sem URL, e a chave.
3. Clique em **Conectar**. Isso seleciona o modo **Live real**. A partida precisa estar iniciada para aplicar as interações.
4. Em **Interações**, crie os vínculos entre presentes reais e ações.
5. Prefira o **ID** do presente. Sem ID, o app compara o nome completo, sem diferenciar maiúsculas/minúsculas.
6. Os presentes efetivamente recebidos aparecem em **Presentes detectados nesta sessão**. Clique em Vincular e escolha a ação.

**Não há IDs inventados ou associações prontas.** Os nomes BUILD, CHICKEN etc. são ações internas. Para usar Rosa como BUILD, por exemplo, cadastre o ID verdadeiro da Rosa recebido na sua live. Sem vínculo, o presente aparece no diagnóstico e não altera a construção.

As duas colunas laterais mostram ícone, nome curto e valor de cada ação, sem cartões nem fundo. As descrições completas permanecem no painel e nos testes. No aviso do participante, o ícone real do presente é usado quando disponível; caso contrário aparece o ícone da ação.

### Como a chave é usada

A implementação segue o mecanismo publicado pela Euler para Python: `WebDefaults.tiktok_sign_api_key` é configurado **antes** de criar `TikTokLiveClient(unique_id=...)`. O conector recebe presentes, curtidas, comentários, seguidores e compartilhamentos da biblioteca **TikTokLive 7.0.1**, mantida pela comunidade. Nenhum endpoint oficial do TikTok foi inventado.

A conexão precisa de **chave Euler + @ de uma conta transmitindo**, internet e acesso disponível na conta/plano Euler. O conector faz até oito tentativas, com esperas progressivas limitadas a 60 segundos. Após o limite, use Conectar novamente. Não existe autenticação simulada: o modo Teste é claramente separado da live.

A chave enviada pelo campo de senha é salva em `config/euler.secret`, usando **DPAPI do usuário atual no Windows**. Ela não está no JavaScript estático, não é retornada pelas rotas de estado e não é registrada em mensagens de erro. O campo fica vazio depois de conectar; deixá-lo vazio reutiliza a chave salva. O segredo de um usuário Windows não pode ser simplesmente copiado para outro usuário.

Opcionalmente, defina a variável de ambiente `EULER_API_KEY`. Ela tem precedência sobre a chave salva. `.env.example` é apenas referência; arquivos `.env` não são carregados automaticamente.

## Regras da partida

A grade padrão tem **14 colunas × 30 linhas = 420 blocos**. A construção inicial é vazia e cresce a 3,5 blocos por segundo. A superfície fica irregular, com preferência por vales e diferença limitada durante a construção. Cada coluna tem suporte contínuo até o chão.

As três faixas de altura são pedra, ouro e diamante. A porcentagem sempre deriva dos blocos existentes; não é uma barra de tempo. Blocos destruídos reduzem o progresso. A câmera sobe suavemente e a interface permanece fixa.

| Ação | Valor inicial por presente | Comportamento |
|---|---:|---|
| BUILD | +8 blocos | Construção com brilho |
| CHICKEN | +16 blocos | Galinha passando pela estrutura |
| PHOENIX | +36 blocos | Fênix e partículas douradas |
| SKY WHALE | +60 blocos | Baleia no céu |
| WIN | +1 vitória | Ajuste do placar |
| ZAP | −3 blocos | Raio na superfície |
| TNT | −8 blocos | Carga piscando e onda de explosão |
| BLACK HOLE | −12 blocos | Vórtice e fragmentos |
| TORNADO | −18 blocos | Tornado percorrendo colunas |
| LOSE | −1 vitória | Ajuste do placar |

Quantidades são editáveis em **Interações → Força das ações**. Ataques removem blocos da superfície próxima ao impacto. Não criam uma grade cheia de blocos flutuantes. O dano é limitado aos blocos existentes. O resultado contábil entra no processamento do evento; a animação visual continua por aproximadamente dois segundos.

O personagem se move automaticamente, com gravidade, pulos, colisões e recuperação quando um bloco surge abaixo dele. A movimentação está separada da taxa de quadros por passos de simulação de 1/120 s.

### Defesa e rodadas

- Em 100%, a partida entra em defesa por **10 segundos**, configuráveis.
- Por padrão, perder qualquer bloco cancela a defesa. Chegar a 100% novamente inicia o tempo completo.
- Se desativar “Cancelar defesa ao perder blocos”, o cronômetro continua; ainda é necessário estar em 100% quando acabar para receber a vitória.
- Uma defesa concluída concede **uma** vitória e inicia uma comemoração de três segundos.
- Depois, a construção recomeça. O placar continua até a meta.
- A meta padrão é 10 vitórias. Ao atingi-la, o app pode pausar ou reiniciar automaticamente com placar zero.
- Valores negativos são permitidos inicialmente, como na referência.

Presentes de construção que excedem a grade viram **blocos pendentes**. Escolha uma política:

- **Reparar assim que houver espaço:** aplica até oito blocos pendentes por passo de simulação após a destruição.
- **Guardar para a próxima rodada:** só aplica os extras após uma rodada concluída.

A fila de blocos extras tem limite de 1.000.000. Reiniciar manualmente limpa construção e blocos pendentes; “Zerar partida” limpa também vitórias. Mudar o número de linhas/colunas reinicia a construção.

Durante **pausa, comemoração ou meta concluída**, novas interações não alteram a partida e não são guardadas para depois. O diagnóstico informa esse estado. Os combos seguem registrados para não reaplicar presentes antigos ao retomar. Mantenha o jogo iniciado durante sua live.

## Combos e outras interações

Para presentes com grupo de combo, o app aplica a diferença entre o total recebido e o total já processado. Exemplo: 1 → 2 → 5 → final 5 corresponde a **cinco** presentes. Uma mensagem final repetida não aplica tudo novamente.

A deduplicação usa IDs de mensagens e grupos, escopo de sala/usuário/presente e retenção limitada. Quando a mensagem não fornece grupo estável, o conector espera o final do combo e usa o ID da mensagem. Sem identificadores estáveis no provedor não é possível garantir deduplicação de mensagens diferentes que representem o mesmo evento; por isso esse caso precisa ser acompanhado em uma live real.

Curtidas, seguidores, comentários e compartilhamentos começam desativados. Cada regra permite escolher ação, quantidade e intervalo por participante. Comentários usam correspondência exata de palavra/frase normalizada. Não executam código. Curtidas são acumuladas por participante até o limiar; curtidas recebidas dentro de um cooldown ativo são ignoradas. Eventos indisponíveis no provedor não são sintetizados.

## Painel e transmissão

- **Início:** conexão, modo, iniciar/pausar e nova rodada.
- **Jogo:** grade, velocidade, defesa, meta, extras, resolução, câmera, áudio e partículas.
- **Interações:** vínculos e regras.
- **Testes:** os dez efeitos, combos, eventos sociais e interrupção da conexão.

Configurações são salvas automaticamente em `config/settings.json` e validadas no servidor. Valores inválidos não substituem o arquivo anterior. O placar e a construção ficam em memória e começam do zero ao abrir novamente.

Capture a janela **B7 VOXEL LIVE** no OBS ou TikTok LIVE Studio. Ela é renderizada em pygame, não dentro do painel. Blocos, nuvens, chão e árvore têm faces com profundidade e iluminação. O personagem usa uma malha de cubos articulados com ordenação de profundidade, projetada em uma câmera lateral fixa. A física continua em um plano 2D, caracterizando o jogo 2.5D.

O canvas lógico é 720 × 1280; as saídas são 540 × 960, 720 × 1280 e 1080 × 1920. A janela padrão é 720 × 1280; em notebook baixo use 540 × 960 ou redimensione. A proporção é mantida com barras laterais se necessário. A resolução 1080 × 1920 escala o mesmo canvas.

Ative “Janela sem bordas” se desejar; Esc fecha o aplicativo. O painel nunca aparece na captura do jogo. Sons saem pelo dispositivo de áudio padrão do Windows e podem ser capturados pelo áudio do sistema.

## Arquivos do projeto

- `main.py`: instância única, loop principal, servidor e janela.
- `configuration.py`: modelo e gravação das configurações.
- `runtime.py`: fila de comandos, eventos e snapshots.
- `game/model.py`: grade e máquina de estados.
- `game/actor.py`: movimento e colisão.
- `game/voxel_character.py`: geometria articulada, pele pixelada e projeção do personagem.
- `game/presentation.py`: descrições e associação visual dos presentes.
- `game/render.py`: desenho, câmera, efeitos, sons e avisos.
- `services/tiktok_service.py`: conector e normalização real.
- `services/events.py`: vínculos, combos e regras comuns a teste/live.
- `services/avatars.py`: fotos em segundo plano com cache limitado.
- `services/secrets.py`: armazenamento da chave.
- `panel/`: FastAPI, HTML, CSS e JavaScript locais.
- `assets/`: 86 arquivos iniciais de gráficos, fonte e sons.
- `tools/make_assets.py`: fonte reproduzível dos desenhos e sons.
- `tools/render_previews.py`: capturas do jogo sem live.
- `previews/`: imagens renderizadas do projeto, não mockups.
- `tests/`: testes automatizados.
- `constraints.txt`: versões transitivas verificadas neste ambiente.

A rede roda fora do thread principal do pygame. Avatares são baixados em fila separada, limitados a 2 MB e tamanhos pequenos. Falhas usam a foto padrão. Efeitos, partículas, avisos, cache de texto, fotos, deduplicação e filas têm limites.

## Testes e limitações de validação

Execute `testar.bat` para instalar a dependência de teste e rodar a suíte. Consulte **VALIDACAO.md** para o resultado desta entrega e os pontos que dependem de teste no seu computador.

A integração real está implementada, mas **não foi validada com uma chave Euler e uma live ativa**. Não inclua sua chave no ZIP que compartilhar. Não foi possível executar um Windows físico nem medir um Ryzen 5 5600GT neste ambiente; 60 FPS é o alvo, não um benchmark desse hardware.

Os assets e algumas animações são aproximações próprias da referência, não uma reprodução pixel a pixel. As regras invisíveis do vídeo foram definidas explicitamente em `REFERENCIA.md`.

## Se algo não abrir

- “Python 3.12 não encontrado”: instale a versão e o Launcher. Não use 3.14 por substituição silenciosa.
- “Porta 5000 ocupada”: uma instância já está aberta ou outro programa usa essa porta. Feche o processo anterior.
- Painel não abriu automaticamente: acesse http://127.0.0.1:5000 enquanto a janela do jogo estiver aberta.
- Presente sem efeito: confira modo Live, partida iniciada e ID/nome vinculado. Abra Diagnóstico.
- Simulação sem efeito: selecione Teste, inicie a partida e confira se a regra social está ativada.
- Chave/assinatura: confira conta, plano, limites e validade da chave Euler. Verifique se o usuário está ao vivo.
- Foto não carregou: o jogo usa a imagem padrão. Só aceita HTTPS público; endereços locais e redirecionamentos são recusados.
- Sem áudio: confira dispositivo padrão, volume geral e volume dos efeitos.

## Fontes técnicas

- Euler, configuração Python: https://www.eulerstream.com/docs/api-key-usage/python
- Euler, bibliotecas: https://www.eulerstream.com/docs/libraries
- TikTokLive, código/documentação de eventos e combos: https://github.com/isaackogan/TikTokLive
- pygame-ce: https://pyga.me/docs/

Consulte `CREDITOS.md` e `licenses/` para os assets, fonte e licenças de dependências.

## Atualização 2.0 — solicitada após a primeira entrega

- Personagem maior, com cabeça, torso, braços e pernas formados por cubos 3D articulados. Referência: personagem de camisa ciano, calça azul e cabelo castanho enviado pelo usuário.
- Blocos com frente texturizada, face superior iluminada e lateral sombreada; faces internas ocultas.
- Árvore, solo e nuvens com profundidade.
- Presentes nas laterais no estilo da referência: ícone, nome curto e valor. Descrições completas no painel.
- Nome do presente configurado e seu ícone recebido na live, com indicação explícita quando ainda não há vínculo.
- Mesmas descrições no painel e nos botões de teste.
- Construção, combos, defesa, vitórias e integração Euler mantidos.

Extraia a atualização em uma pasta nova. Para preservar suas configurações pessoais, copie `config/settings.json` da instalação anterior. A chave protegida `config/euler.secret` pode ser copiada apenas para uso pelo mesmo usuário Windows. Não envie esse arquivo a outras pessoas.

### Revisão 2.1 — presentes laterais

A pedido do usuário, o quadro inferior foi removido. Os presentes voltaram às duas colunas transparentes nas bordas, com ícone, nome curto e +/− quantidade, como na captura enviada. Personagem, geometria 2.5D, efeitos, regras e controles foram preservados.
