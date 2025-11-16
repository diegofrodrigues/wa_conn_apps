# Problema de Arquitetura: Múltiplos Providers com _inherit

## Problema Identificado

Quando temos múltiplos módulos fazendo `_inherit` no mesmo modelo (`wa.account`), o Odoo cria uma ÚNICA classe mesclada com TODOS os métodos. O problema é o **Method Resolution Order (MRO)** - a ordem em que os métodos são resolvidos.

###Exemplo do Problema:

```python
# wa_conn/models/wa_account.py
class WAAccount(models.Model):
    _name = 'wa.account'
    
    def send_text(self, mobile, message):
        raise NotImplementedError()

# wa_conn_evolution/models/wa_account_evolution.py  
class WAAccountEvolution(models.Model):
    _inherit = 'wa.account'
    
    def send_text(self, mobile, message):
        if self.provider != 'evolution':
            return super().send_text(mobile, message)  # Passa para próximo na cadeia
        # ... código evolution ...

# wa_conn_quepasa/models/wa_conn_quepasa_provider.py
class WAConnQuepasaProvider(models.Model):
    _inherit = 'wa.account'
    
    def send_text(self, mobile, message):
        if self.provider != 'quepasa':
            return super().send_text(mobile, message)  # Passa para próximo na cadeia
        # ... código quepasa ...
```

### O que acontece:

1. Usuário cria account com `provider='evolution'`
2. Chama `account.send_text()`
3. **MRO pode ser**: `WAConnQuepasaProvider -> WAAccountEvolution -> WAAccount`
4. Quepasa vê `self.provider != 'quepasa'`, chama `super()`
5. Evolution vê `self.provider == 'evolution'`, **DEVERIA executar**, MAS...
6. Dependendo da ordem de carregamento dos módulos, pode executar o método errado!

## Solução 1: Pattern do Odoo Payment (RECOMENDADO)

O módulo `payment` do Odoo resolve isso **NÃO chamando super()**, apenas retornando:

```python
# wa_conn_evolution/models/wa_account_evolution.py  
def send_text(self, mobile, message):
    if self.provider != 'evolution':
        return super().send_text(mobile, message)
    # ... código evolution ...
    return resultado

# wa_conn_quepasa/models/wa_conn_quepasa_provider.py
def send_text(self, mobile, message):
    if self.provider != 'quepasa':
        return super().send_text(mobile, message)
    # ... código quepasa ...
    return resultado
```

**Vantagens:**
- Padrão oficial do Odoo
- Simples de implementar
- Funciona com qualquer número de providers

**Desvantagens:**
- Se nenhum provider reconhecer o valor de `provider`, o método base lança `NotImplementedError`
- Cada provider precisa ter o check `if self.provider != 'X'`

## Solução 2: Models Separados (Pattern Delegation/Composition)

Criar modelos separados para cada provider e delegar:

```python
# wa_conn/models/wa_account.py
class WAAccount(models.Model):
    _name = 'wa.account'
    
    provider = fields.Selection([...])
    provider_evolution_id = fields.Many2one('wa.account.evolution')
    provider_quepasa_id = fields.Many2one('wa.account.quepasa')
    
    def send_text(self, mobile, message):
        if self.provider == 'evolution' and self.provider_evolution_id:
            return self.provider_evolution_id.send_text(mobile, message)
        elif self.provider == 'quepasa' and self.provider_quepasa_id:
            return self.provider_quepasa_id.send_text(mobile, message)
        raise NotImplementedError()

# wa_conn_evolution/models/wa_account_evolution.py
class WAAccountEvolution(models.Model):
    _name = 'wa.account.evolution'  # Modelo PRÓPRIO, não _inherit
    
    account_id = fields.Many2one('wa.account')
    api_url = fields.Char()
    api_key = fields.Char()
    
    def send_text(self, mobile, message):
        # ... código evolution ...

# wa_conn_quepasa/models/wa_account_quepasa.py
class WAAccountQuepasa(models.Model):
    _name = 'wa.account.quepasa'  # Modelo PRÓPRIO, não _inherit
    
    account_id = fields.Many2one('wa.account')
    quepasa_url = fields.Char()
    quepasa_bot_token = fields.Char()
    
    def send_text(self, mobile, message):
        # ... código quepasa ...
```

**Vantagens:**
- Separação total entre providers
- Sem conflito de MRO
- Cada provider é independente
- Fácil adicionar/remover providers

**Desvantagens:**
- Refatoração completa necessária
- Mais complexo de gerenciar
- Campos específicos ficam em modelos separados

## Solução 3: Dispatch Dinâmico (Complexo)

Fazer o modelo base detectar e rotear para a classe correta dinamicamente:

```python
# wa_conn/models/wa_account.py
class WAAccount(models.Model):
    _name = 'wa.account'
    
    # Registro de providers
    _provider_registry = {}
    
    @classmethod
    def _register_provider(cls, provider_code, provider_class):
        cls._provider_registry[provider_code] = provider_class
    
    def send_text(self, mobile, message):
        provider_class = self._provider_registry.get(self.provider)
        if provider_class:
            # Chama método diretamente na classe do provider
            return provider_class.send_text(self, mobile, message)
        raise NotImplementedError()

# wa_conn_evolution/__init__.py
def post_init_hook(env):
    WAAccount = env['wa.account'].__class__
    WAAccount._register_provider('evolution', WAAccountEvolution)
```

**Vantagens:**
- Routing explícito
- Sem ambiguidade de MRO

**Desvantagens:**
- Muito complexo
- Não é padrão Odoo
- Difícil manutenção

## Recomendação

**Usar Solução 1** (Pattern do Odoo Payment). É o padrão oficial e já está parcialmente implementado.

O que precisa ser ajustado:
1. ✅ Manter `if self.provider != 'X'` em TODOS os métodos dos providers
2. ✅ Chamar `super()` quando não for o provider correto
3. ✅ Garantir ordem de carregamento dos módulos (depends no __manifest__.py)
4. ✅ Testar com logging para verificar qual método executa

## Debugging

Para verificar o MRO atual:

```python
account = self.env['wa.account'].browse(1)
print(f"Class: {account.__class__.__name__}")
print(f"MRO: {[c.__name__ for c in account.__class__.__mro__]}")
```

Adicionar logs em cada provider para rastrear execução:

```python
def send_text(self, mobile, message):
    import logging
    _logger = logging.getLogger(__name__)
    _logger.info(f"[{self.__class__.__name__}] send_text called - provider={self.provider}")
    
    if self.provider != 'evolution':
        _logger.info(f"[{self.__class__.__name__}] Skipping - not my provider")
        return super().send_text(mobile, message)
    
    _logger.info(f"[{self.__class__.__name__}] Executing send_text")
    # ... código ...
```
