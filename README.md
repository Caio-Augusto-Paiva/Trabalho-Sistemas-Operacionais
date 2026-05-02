# Trabalho-Sistemas-Operacionais

Scripts de sincronizacao (6.2 a 6.8) com demonstracao incorreta, versao corrigida
e testes de estresse automatizados (asserts).

## Pre-requisitos

- Python 3.x instalado (comando `python` no PATH).
- Windows PowerShell (exemplos abaixo).

## Execucao

Abra um terminal na pasta do projeto e rode cada script:

```powershell
python "Produtor-consumidor com buffer limitado(6.2).py"
python "Leitores e escritores(6.3).py"
python "Jantar dos filósofos(6.4).py"
python "Barbeiro Sonolento(6.5).py"
python "Ponte de mão única(6.6).py"
python "Estacionamento com vagas limitadas(6.7).py"
python "Impressora compartilhada(6.8).py"
```

Cada execucao roda:
1) versao incorreta (falha aparece no log),
2) versao corrigida (sem falha),
3) teste de estresse com asserts. Se algum assert falhar, o Python encerra com
`AssertionError`.

## Matriz de resultados (6.2 a 6.8)

### 6.2 - Produtor-consumidor com buffer limitado

- Versao incorreta: corrida no contador do buffer; log mostra "ERRO: produtor sobrescreveu buffer cheio" e/ou "ERRO: consumidor tentou ler buffer vazio".
- Versao corrigida: semaforos + mutex; teste de estresse confirma que `count` nunca sai do intervalo e que nao ha itens faltantes/extras/duplicados.
- Comparacao e justificativa: a versao correta usa semaforos de contagem para controlar vagas/itens e mutex para proteger `buffer` e `count`, eliminando as sobrescritas e leituras de vazio sob carga extrema.

### 6.3 - Leitores e escritores (fairness, sem starvation)

- Versao incorreta: leitores podem enxergar escrita parcial; o contador de inconsistencias fica > 0.
- Versao corrigida: turnstile + exclusao de escrita; no estresse (100 leitores, 1 escritor) o log mostra o escritor progredindo e `inconsistencies == 0`.
- Comparacao e justificativa: o turnstile bloqueia novos leitores quando um escritor aguarda, garantindo que o escritor sempre avance mesmo com assimetria extrema.

### 6.4 - Jantar dos filosofos

- Versao incorreta: deadlock garantido; a saida trava depois que todos pegam o garfo esquerdo.
- Versao corrigida: hierarquia de recursos; o teste de estresse termina com todas as threads finalizadas.
- Comparacao e justificativa: a ordem total de recursos remove a condicao de espera circular, logo nao ha deadlock mesmo com mais filosofos.

### 6.5 - Barbeiro Sonolento

- Versao incorreta: corridas no contador de espera e no estado do barbeiro; log registra over-capacity e contador negativo.
- Versao corrigida: semaforos `customers`/`barber_ready` + mutex; no estresse (80 clientes) `max_waiting` nunca passa de `CHAIRS`.
- Comparacao e justificativa: a sincronizacao elimina a janela entre checagem e incremento do contador, garantindo que a capacidade maxima nunca seja ultrapassada.

### 6.6 - Ponte de mao unica

- Versao incorreta: sem exclusao mutua; log mostra "COLISAO" quando sentidos opostos entram juntos.
- Versao corrigida: Condition + limite por turno; no estresse (50 carros N, 2 S) ambos os lados atravessam e o log mostra tempos maximos de espera finitos.
- Comparacao e justificativa: a alternancia por turno previne starvation e garante progressao do lado minoritario mesmo sob fluxo assimetrico.

### 6.7 - Estacionamento com vagas limitadas

- Versao incorreta: sem exclusao mutua; log registra `ocupacao > vagas` e, ocasionalmente, contagem negativa.
- Versao corrigida: semaforo de vagas + mutex; no estresse `max_occupied <= SPOTS` sempre.
- Comparacao e justificativa: o semaforo limita a entrada simultanea, e o mutex torna a contagem de vagas consistente.

### 6.8 - Impressora compartilhada

- Versao incorreta: intercalacao de paginas entre documentos; teste detecta ranges sobrepostos no log.
- Versao corrigida: spooler FIFO; teste confirma que a ordem de impressao e identica a ordem de solicitacao.
- Comparacao e justificativa: a fila FIFO separa pedido e atendimento, garantindo fairness mesmo com muitos produtores concorrentes.

## Execucao do 6.1 (contador compartilhado)

```powershell
python "Contador compartilhado(6.1).py"
```

Na versao incorreta o valor final pode variar; na versao com lock o valor deve
ser deterministico (ainda que mais lento).