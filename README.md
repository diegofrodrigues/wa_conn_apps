# wa_conn_apps

Este diretório é a nova raiz do monorepo "wa_conn_apps" — um repositório que agrupa os diversos apps relacionados a WA (WhatsApp) usados pela equipe. O objetivo é facilitar manutenção, releases e integração entre os plugins/providers que antes viviam em repositórios separados.

> Atenção: este é o novo diretório/monorepo. Os repositórios originais (por exemplo `wa_conn`, `wa_conn_evolution`, `wa_conn_quepasa`, `wa_conn_bot`) podem continuar existindo no remoto por um tempo enquanto migramos e validamos tudo.

## Conteúdo esperado

Ao final da migração, a estrutura ficará parecida com:

```
wa_conn_apps/
├─ wa_conn/                # Core WA connector
├─ wa_conn_evolution/      # Provider: Evolution
├─ wa_conn_quepasa/        # Provider: Quepasa
├─ wa_conn_bot/            # Bot / automations
└─ README.md
```

## Status da Migração

- Este repositório foi criado para agrupar os apps WA.
- Verifique os commits para confirmar se o histórico de cada subprojeto foi preservado (métodos comuns: `git subtree` / `git read-tree`).
- Se o histórico não foi preservado (importação simples), os repositórios originais permanecerão como fonte canônica do histórico antigo.

> Se você não tiver certeza sobre como foi feita a importação, cheque o log e as tags de cada subpasta:
>
> ```bash
> # Ver commits que afetaram a subpasta
> git log --follow -- wa_conn/
> 
> # List tags
> git tag --contains <commit-ish>
> ```

## Como contribuir

- Clone o monorepo:

```bash
git clone git@github.com:<org>/wa_conn_apps.git
cd wa_conn_apps
```

- Crie uma branch com o escopo da sua alteração (ex: `feat/wa_conn-fix-xyz`):

```bash
git checkout -b feat/wa_conn-fix-xyz
```

- Faça as mudanças dentro da pasta do subprojeto correspondente (ex: `wa_conn/` ou `wa_conn_evolution/`).
- Commit e push normalmente. Abra pull request no repositório `wa_conn_apps`.

Observação: se sua equipe preferir continuar usando repositórios separados (submodules), adapte o fluxo de acordo — este monorepo unifica o trabalho em um único repositório por padrão.

## Comandos úteis para manutenção

- Importar um outro repositório para uma subpasta (preservando histórico) — exemplo usando `read-tree`:

```bash
# a partir do clone do monorepo
git remote add wa_conn_remote git@github.com:<org>/wa_conn.git
git fetch wa_conn_remote --tags
git checkout -b import-wa_conn wa_conn_remote/main
git checkout main
git merge --allow-unrelated-histories -s ours --no-commit import-wa_conn
git read-tree --prefix=wa_conn/ -u import-wa_conn
git commit -m "Import wa_conn into subdirectory wa_conn/ (preserve history)"
git branch -D import-wa_conn
git remote remove wa_conn_remote
```

- Import simples (sem preservar histórico) a partir de um clone local:

```bash
mkdir -p wa_conn
rsync -a --exclude '.git' /caminho/para/wa_conn_clone/ wa_conn/
git add wa_conn
git commit -m "Add wa_conn as subdirectory (shallow import)"
```

## CI / Deploy

- Atualize pipelines e scripts que esperam o layout antigo. Paths para builds, testes e deploys agora provavelmente deverão apontar para `wa_conn/<path>` ou `wa_conn_evolution/<path>`.

## Política de retenção dos repositórios antigos

- Repositórios originais podem ser mantidos como read-only/archivados por um período para auditoria.
- Recomenda-se adicionar um `README.md` nesses repositórios apontando para este monorepo e explicando a data da migração.

## Contatos

Se precisar de ajuda com a migração, conflitos ou configuração de CI, contate:

- Time de Infra / SCM: devops@seudominio.com
- Responsável pelo WA: nome.do.responsavel@seudominio.com

---

Se preferir, eu gero um script de migração (rápido ou preservando histórico) com placeholders para os URLs dos remotos — quer que eu gere agora?