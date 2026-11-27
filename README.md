# Indicaê · Posts automáticos no Instagram

A cada 2 dias, às 8h, o robô:
1. busca uma notícia de Sobral no Google Notícias (pula crime, acidente e política);
2. monta a legenda e as artes do **feed** (4:5) e do **stories** (9:16);
3. abre uma **Issue de prévia** aqui no GitHub (você recebe aviso por e-mail e no app);
4. depois de **4 horas**, se você não cancelou, publica feed + stories no @indicaesobral.

Tudo roda na nuvem do GitHub, de graça. O computador pode ficar desligado.

## Como cancelar ou mudar um post
- **Cancelar:** feche a Issue ou coloque a etiqueta `cancelar`.
- **Mudar a legenda:** edite a descrição da Issue (só o texto dentro do bloco da legenda).
- **Publicar antes:** Actions → "2 - Publicar aprovados" → Run workflow (só publica depois das 4h).

## Configuração (já feita)
- App na Meta: **Indicae Posts**, ligado ao portfólio **Indicae Sobral**.
- Robô: usuário do sistema **Robo Indicae**, com acesso ao @indicaesobral (permissões `instagram_basic` e `instagram_content_publish`).
- O token do robô **não expira**. Ele fica no segredo `IG_TOKEN` do GitHub; o ID da conta fica em `IG_USER_ID`.
- Para conferir a conexão: Actions → "3 - Testar conexão com o Instagram" → Run workflow.
- Se um dia precisar trocar o token: Meta Business Suite → Configurações → Usuários do sistema → Robo Indicae → Gerar token, e atualize o segredo `IG_TOKEN`.

## Ajustes fáceis (arquivo `config.json`)
- `horas_para_cancelar`: prazo da prévia (padrão 4).
- `buscas_noticias`: o que procurar no Google Notícias.
- `palavras_proibidas`: temas que nunca viram post.
- `chamadas`: frases de chamada para o Indicaê (sorteia uma por post).
- `hashtags`, `cores`.

Frequência: arquivo `.github/workflows/1-preparar-post.yml`, linha `cron` (`0 11 */2 * *` = a cada 2 dias, 8h de Brasília).
