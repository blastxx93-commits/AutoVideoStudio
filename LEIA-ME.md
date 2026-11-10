# AutoVideo Studio

Programa para o seu PC: você coloca **título + roteiro**, escolhe as opções e recebe o vídeo pronto (com thumbnail, legenda .srt e relatório de revisão) na pasta que escolher.

## Instalação (uma vez só)
1. Instale o **Python 3.11 ou 3.12** (python.org). Na instalação, marque **"Add python.exe to PATH"**.
2. Extraia este .zip numa pasta (ex: `C:\AutoVideoStudio`). Evite a Área de Trabalho sincronizada com o OneDrive.
3. Dê dois cliques em **INSTALAR.bat**. Ele instala as bibliotecas e o FFmpeg e cria o atalho **AutoVideo Studio** na Área de Trabalho e no menu Iniciar.
4. Abra pelo ícone **AutoVideo Studio**. O programa abre na própria janela, sem navegador e sem a janela preta. Para fechar, feche a janela ou use **⏻ Sair do programa**. Os vídeos que já estão sendo gerados continuam até terminar.
   - O **ABRIR.bat** continua funcionando: ele abre no navegador e mostra a janela preta com os detalhes, o que ajuda a descobrir erros.

## Novo vídeo em etapas
O **Novo vídeo** agora é uma lista de etapas em ordem: título (com o perfil do canal ao lado) e depois **1 Roteiro → 2 Narração → 3 Cenas → 4 Edição e animação → 5 Legenda → 6 Trilha → 7 Revisão → 8 Thumb → 9 Descrição e SEO → 10 Exportar**. Cada etapa mostra um resumo do que está escolhido. Clique em **Editar ▼** para abrir e em **✓ Confirmar e ir para a próxima →** para seguir. Os campos de texto têm o botão **✓ Confirmar** ao lado (o Enter também funciona).

## Dobra para outro idioma
No menu **🌍 Dobra de canais**, cole o link do vídeo de referência e clique em *Buscar vídeo e transcrição*. Depois escolha o idioma, a duração e o **ângulo da nova versão** (automático, outro ponto de vista, bastidores e investigação, mistérios, consequências e legado, contexto histórico, lado humano ou linha do tempo invertida).
A dobra **não traduz** o vídeo:
1. O Claude extrai só a **estrutura** do canal: tipo de gancho, blocos e % de tempo, frequência das viradas, ritmo e tipo de final.
2. Escreve um roteiro **novo**, pelo ângulo escolhido, com detalhes que não estão no original e no jeito de falar do idioma.
3. Confere a **originalidade**. Se a semelhança passar de 30%, reescreve sozinho, até 2 vezes. A nota aparece no resultado.
O botão **🌍 Adaptar** do Buscador de Nichos leva o link direto para cá. No fim, **Usar este roteiro e título** leva tudo para o Novo vídeo, já na etapa de Narração. Na Fila, a aba *Links para dobra* faz o mesmo para vários vídeos.

## Fila de vídeos
Menu **📋 Fila de vídeos**: adicione vídeos pelo botão **➕ Adicionar à fila** no Novo vídeo, ou vários de uma vez (roteiros prontos, temas para a IA escrever ou links para adaptar). Clique em **▶️ Iniciar fila** e o programa produz um atrás do outro. Deixe o PC ligado e a janela preta aberta. Dá para reordenar, pausar depois do vídeo atual, repetir os que deram erro e escolher se cada vídeo espera a sua revisão ou é exportado direto.

## Primeiro uso
1. Vá em **APIs e configurações** e cole suas chaves:
   - **IA de texto** (recomendado): Claude, OpenAI, Gemini, DeepSeek, OpenRouter ou Ollama (grátis/local). Ela divide o roteiro em cenas e escreve o prompt de cada imagem. Custa centavos por vídeo.
   - **ElevenLabs** e/ou **Fish Audio** para a narração.
   - **Pexels** e **Pixabay** (grátis) para o modo banco de imagens/clipes.
   - Geradores de imagem: **Pollinations** (Flux grátis, sem chave), Replicate, fal.ai, Together, Black Forest Labs, OpenAI, Google Imagen, ou qualquer API no padrão OpenAI (gerador personalizado).
2. Clique em **Salvar configurações**.
3. Em **Novo vídeo**, preencha as abas e clique em **GERAR VÍDEO**. Dá para montar o próximo enquanto o primeiro renderiza.
4. Salve as opções de cada canal em **Perfis de canal** (Máfia, Mitologia, Carros…) para carregar tudo com um clique.

> Meta AI e Google Flow não oferecem API pública de imagens. Do Google, use **Google Imagen**, que é o mesmo modelo de imagem do Flow, acessado pela chave do Gemini.

## Gerar roteiro com IA (Claude + skills)
Na aba **📝 Roteiro**, escolha **✨ Gerar roteiro com IA**. Informe o tema, o idioma (8 opções), a duração, o estilo e, se quiser, cole a transcrição de um vídeo de referência para adaptar sem copiar. O roteirista entrega 8 a 12 títulos (os 2 melhores marcados com ⭐), o roteiro pronto para narrar e as notas de estrutura e fontes. Depois você edita, pede ajustes ("mais tenso", "encurte para 8 min") e clica em **Usar este roteiro**.
- Usa a IA de texto configurada. O recomendado é o **Claude** (chave da Anthropic): o modelo do roteirista é configurável e por padrão é um modelo mais forte que o usado nos prompts das imagens. Com o Claude ou o Gemini, ele também pode **pesquisar fatos na web** antes de escrever.
- **Skills:** guias em Markdown que o roteirista sempre segue. Já vêm duas: `documentario-dark-edicao-titulos` (a sua) e `roteiro-narrado-retencao`. Importe outras (.md ou .zip de skill) em *Gerenciar skills do roteirista*.
- A API do Claude é cobrada por uso, separada da assinatura do claude.ai.

## O que cada aba faz
| Aba | Opções |
|---|---|
| Roteiro | título, roteiro, duração média das cenas |
| Visual | **barra de mistura**: escolha a % de cenas do banco e de IA (ex: 70% banco / 30% IA), intercalado, em blocos ou aleatório; se o banco não achar nada para uma cena, ela vira IA. IA (gerador + estilo: cinematográfico, stickman, webdoc, documentário dark, anime, 3D, pintura a óleo, noir, personalizado) ou Banco (Pexels, Pixabay, pasta do seu PC; clipes, fotos ou misto) |
| Narração | ElevenLabs / Fish Audio, lista de vozes, ID manual, modelo, velocidade, amostra |
| Legendas | liga/desliga, 6 estilos (clássica, amarela, caixa TV, karaokê, impacto central, cinema), .srt |
| Edição | **templates do vídeo** (12 estilos: Pergaminho Solar, Neo-Brutal, Cobalto Executivo, Pôster Vermelho, Laranja Industrial, Cápsula Doce, Linha Única, Grade Azul, Dossiê Noir, Arquivo Sépia, Cinema Épico ou nenhum); cada um tem abertura com título, encerramento, moldura, cor e legenda combinando, e tudo pode ser ligado ou desligado. Também tem movimento (zoom in/out, pans, aleatório), intensidade, 12 transições, efeitos sonoros, música com ducking |
| Revisão | imagens repetidas, corrompidas, tela preta/branca, narração cortada/silêncio, áudio estourado/baixo, legendas; correção automática; revisão opcional com IA de visão |
| Thumbnail | gerador próprio, texto automático ou seu, descrição da imagem |
| Exportar | pasta de saída, **resolução 1080p ou 2K (1440p)**, assistir e aprovar antes |

## BUSCADOR DE NICHOS
Encontra canais pequenos (ex: menos de 1.000 inscritos) com vídeos recentes cheios de views, que são o sinal de um nicho aquecido agora.
1. Crie a chave grátis: console.cloud.google.com → novo projeto → "APIs e serviços" → ativar **YouTube Data API v3** → Credenciais → **Criar chave de API**. Cole em APIs e configurações.
2. Escolha os nichos prontos (dark, true crime, máfia, mitologia, sobrevivência, história…) ou digite seus termos.
3. Ajuste os filtros: máximo de inscritos, mínimo de views, últimos X dias, região (Brasil, Portugal, EUA, Reino Unido, Austrália, Espanha, México, Alemanha, Polônia, República Tcheca, Dinamarca, Noruega ou mundo; os nichos prontos são pesquisados automaticamente no idioma do país), duração e idade do canal.
4. Resultado: ranking dos nichos com mais oportunidade, tabela de vídeos/canais com **multiplicador** (views ÷ inscritos) e views/dia, links, planilha CSV e análise por IA com padrões de título e 10 ideias.

### Chegar cedo (nichos nascendo)
- **⚡ Modo chegar cedo**: vídeos das últimas 72 horas, canais que começaram a postar há até 1 mês, até 20 mil inscritos.
- **Nota "Chegou cedo" (0–100)**: soma velocidade (views por hora), tamanho do vídeo comparado ao canal, idade real do canal (data do 1º vídeo, não da criação da conta), poucos vídeos, aceleração (vídeos novos rendendo mais que os antigos) e % das views que vieram na última semana.
- **Sinais**: 🔥 Explodindo · 🌱 Bem no início · 🚀 Acelerando · ⭐ Fora da curva · 📡 Crescendo no radar.
- **Concorrência no meu idioma**: pesquisa o mesmo assunto no idioma para onde você vai levar o canal (🟢 livre, 🟡 pouca, 🔴 já tem gente) e ajusta a nota.
- **📡 Radar**: siga os canais promissores e clique em "Atualizar radar" nos próximos dias. O programa mostra quantos inscritos e views cada canal ganha por dia. Todo canal que aparece numa busca também é guardado, então numa busca futura ele já mostra o crescimento.
- **Analisar canal:** cole o link/@ do canal (ou clique num canal do resultado). Mostra inscritos, views, tendência, frequência de postagem, vídeos que viralizaram (3x+ a mediana), shorts x longos, melhor duração, dia e horário, padrões de título, palavras e tags mais usadas, receita estimada e uma análise estratégica por IA com plano para competir e 10 títulos. Custa só ~5 unidades de cota.
- A cota grátis é de 10.000 unidades/dia, e cada termo pesquisado gasta ~104. Dá umas 90 buscas de termo por dia.

## Revisar antes de exportar
Com a opção **"Assistir e aprovar antes de exportar"** ligada (aba Exportar, ligada por padrão), o vídeo pronto aparece na tela com player, thumbnail, duração e relatório do agente de revisão. Nada vai para a sua pasta até você clicar em **APROVAR E EXPORTAR**. Também dá para abrir em 1080p no player do PC, ajustar as opções e gerar de novo, ou descartar. Os vídeos esperando aprovação aparecem com 👀 em **Trabalhos**.

## Descrição, hashtags e palavras-chave
Na aba **📣 Descrição & SEO** (ligada por padrão), o programa:
1. Pesquisa o que as pessoas **realmente digitam** na busca do YouTube sobre o assunto (sugestões de busca da plataforma, grátis e sem chave).
2. Escreve a descrição com gancho nas 2 primeiras linhas, resumo com as buscas reais, **capítulos com minutagem** e o seu texto fixo (redes sociais etc.).
3. Escolhe as **hashtags** (de 3 a 15; as 3 primeiras aparecem acima do título) e de 20 a 30 **palavras-chave** dentro do limite de 500 letras do YouTube. As que são buscas reais aparecem marcadas com 🔥.
4. Opcional: mede cada hashtag na API do YouTube (quantos vídeos saíram nos últimos 30 dias e quantas views os melhores tiveram).
Na tela de revisão dá para editar a descrição ou gerar outra versão. Na exportação vão juntos `descricao.txt`, `hashtags.txt` e `palavras_chave.txt`. Também dá para gerar só a descrição, sem fazer o vídeo.

## Trilha sonora
Aba **🎵 Trilha sonora**: automático (a IA escolhe o clima pelo roteiro), tema fixo (som ambiente, relaxante, animado, reflexivo, dramático, suspense/dark, épico, misterioso, inspirador, triste, tensão/ação), arquivo/pasta específica, ou sem música.
A Biblioteca de Áudio do YouTube não tem API, então você baixa as faixas no YouTube Studio (filtrando por *Humor*) e importa uma vez na **Biblioteca de trilhas**, escolhendo o tema. Se a faixa pedir atribuição, cole o texto na importação: ele entra sozinho na descrição dos vídeos que usarem a música.

## Abrir projeto (dentro da Fila de vídeos)
A **📋 Fila de vídeos** mostra todos os seus vídeos (os da fila e os gerados direto pelo botão Gerar vídeo) em cartões, com status, porcentagem, tempo gasto e tempo restante, as 5 etapas (Roteiro, Narração, Imagens, Montagem, Finalização) e os números (duração, cenas prontas, mistura IA/banco). Cada cartão tem os botões **🗂️ Abrir o projeto**, **⏸ Pausar / ▶ Retomar**, **📋 Ver log** e **📂 Abrir a pasta**.
**Abrir o projeto** mostra no topo da Fila todas as cenas do vídeo: a imagem ou clipe de cada uma, a narração, a fonte, o tempo e os avisos. Com o vídeo pronto, dá para trocar qualquer cena (outra imagem de IA com o prompt editado, outra do banco ou um arquivo seu) e clicar em **🎬 Remontar vídeo**: só as cenas trocadas são refeitas.

## Exemplos antes de escolher
Ao escolher movimento, transição, estilo de legenda ou template, aparece um exemplo na hora: um mini-vídeo em loop, ou uma imagem no caso da legenda. Os exemplos usam cenas de exemplo desenhadas pelo programa. No template, o botão "▶ Ver exemplo em vídeo" monta 7 segundos com abertura, cenas, legenda e encerramento, usando o seu título. Os exemplos ficam guardados e só demoram na primeira vez.

## Publicar e agendar no YouTube
Menu **📤 Publicar no YouTube**:
1. **Contas conectadas:** siga o passo a passo para criar a chave OAuth (client_secret.json, tipo *App para computador*) no Google Cloud, envie o arquivo e clique em **Conectar canal**. Dá para conectar vários canais.
2. **Enviar / agendar:** escolha o vídeo pronto. Título, descrição, tags, thumbnail e legenda já vêm preenchidos. Depois escolha o canal, a categoria, o idioma e se é público, não listado, privado ou **agendado** (o YouTube publica sozinho na data, mesmo com o PC desligado).
3. **Envios e agendados:** acompanhe o progresso e abra o link de cada vídeo.

⚠️ **Importante:** pela regra do YouTube, vídeos enviados por projetos do Google Cloud **não auditados** ficam **travados como privados**. Para liberar público/agendado pela API, peça a auditoria gratuita do seu projeto no formulário *YouTube API Services – Audit and Quota Extension*. Enquanto isso, use o **modo manual** (abre o YouTube Studio e a pasta do vídeo com os textos prontos para colar).
Outros detalhes: thumbnail personalizada exige canal verificado por telefone; deixe o app do Google Cloud como *Em produção* para a conexão não expirar a cada 7 dias.

## Sincronia e resolução
- Cada cena tem a própria narração, e a imagem dura exatamente o tempo da fala dela. As transições ficam **centradas na troca de frase**: a imagem nova aparece por inteiro meia transição depois da frase dela começar. As legendas seguem o mesmo relógio.
- **1080p ou 2K:** escolha na aba Exportar antes de gerar (2K de verdade, ~1,8x mais lento). Na hora de aprovar dá para exportar na outra resolução também (o programa converte).

## Dicas
- **Efeitos sonoros próprios:** coloque arquivos .wav/.mp3 em `assets/efeitos_sonoros` (o programa sorteia entre eles).
- **Pasta do PC como banco:** nomeie os arquivos com palavras-chave (`tribunal_palermo.mp4`) para o programa achar o melhor arquivo para cada cena.
- **Pausar, retomar e cancelar:** enquanto o vídeo gera aparecem os botões ⏸️ Pausar / ▶️ Retomar e ⏹️ Cancelar. A pausa vale ao fim da cena atual. Um vídeo cancelado pode ser continuado depois, de onde parou, em **Trabalhos**.
- **Se der erro no meio:** em **Trabalhos**, clique em **Continuar**. O programa reaproveita o que já foi feito (áudios, imagens, cenas) e não gasta créditos de novo.
- **Velocidade:** no notebook, deixe "Cenas renderizando juntas" entre 2 e 4. Um vídeo de 10 minutos costuma levar de 10 a 25 minutos para renderizar, dependendo do processador.
- **Sem interface:** `python -m core.pipeline dados\trabalhos\<pasta>` roda um trabalho direto.

## Estrutura
```
app.py            interface
core/llm.py       divide o roteiro e cria os prompts
core/tts.py       ElevenLabs / Fish Audio
core/images.py    geradores de IA + Pexels/Pixabay/pasta local
core/render.py    FFmpeg: movimento, transições, áudio, legendas
core/review.py    agente de revisão
core/thumbnail.py thumbnail
core/nichos.py    buscador de nichos (YouTube Data API)
core/canal.py     análise de canal
core/seo.py       descrição, hashtags e palavras-chave
core/pipeline.py  junta tudo
dados/            suas chaves, perfis e trabalhos (não compartilhe esta pasta)
```

## Estilos de vídeo (etapa Cenas)
A etapa **Cenas** tem uma galeria com 17 estilos, cada um com uma imagem de exemplo:
Motion Graphics, 3D Cinematográfico, Cartoon 2D, Stickman, Webdoc Investigativo, Quadrinho Animado,
Recortes de Papel, Pixel Art, Stop Motion, Avatar de Culinária, Diorama Isométrico, Gravura Animada,
Mapa de Relevo 3D, Mapa de Busca, Pintura Digital, Aquarela e Óleo sobre Tela. Clique em **Usar este**.

- O estilo escolhido vai em **todas** as imagens geradas por IA: cenas, troca de cena no projeto e thumbnail.
- A IA que escreve os prompts das cenas recebe uma "direção" do estilo (ex.: no Mapa de Busca toda cena vira mapa de satélite).
- **Personagem principal fixo**: descreva o personagem (em inglês funciona melhor) para ele sair igual em todas as cenas.
  No Avatar de Culinária já vem uma apresentadora pronta, e você pode trocar.
- Estilos desenhados não combinam com fotos do banco. Se a mistura tiver banco, aparece um aviso com o botão "Usar 100% IA".
- Para criar seus próprios estilos, edite `core/estilos.py` e coloque a miniatura em `assets/estilos/`.

## Referência de edição (Novo vídeo)
Logo abaixo do título há a seção **🎞️ Referência de edição**. Cole o link de um vídeo (YouTube e outros sites) ou o caminho de um vídeo do seu PC e clique em **Analisar edição**.

- **Medido com o FFmpeg** (nos 10 primeiros minutos): duração média de cada plano (e no 1º minuto), trocas de imagem por minuto, cortes secos × dissolves × passagens pelo preto, duração das transições e quantidade de movimento (zoom/pan).
- **Com a IA** (Claude ou outra que aceite imagens), olhando 8 quadros: estilo das imagens, se usa banco ou IA, legendas e estilo, template parecido, clima da trilha, personagem que se repete e jeito de enquadrar as cenas.
- **Pela transcrição**: velocidade da narração (palavras por minuto).
- Aparece a lista do que vai mudar, com caixinhas para desmarcar. **Aplicar no vídeo** preenche as etapas sozinho.
- Só a edição é copiada, nunca o conteúdo. O vídeo do YouTube é baixado em baixa qualidade só para a análise e apagado logo depois (usa o yt-dlp, que o programa instala sozinho na primeira vez).
