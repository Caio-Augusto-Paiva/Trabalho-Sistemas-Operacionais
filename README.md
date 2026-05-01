# Trabalho-Sistemas-Operacionais

## Como rodar o 6.1 (com e sem lock)

1) Abra um terminal na pasta do projeto.
2) Execute o arquivo [Contador compartilhado(6.1).py](Contador%20compartilhado(6.1).py):

```powershell
python "Contador compartilhado(6.1).py"
```

3) Compare as duas linhas exibidas no final:
- "Versao incorreta (sem lock)": valor pode variar por condicao de corrida.
- "Versao corrigida (com lock)": deve ficar igual ao esperado.

Obs.: a versao com lock costuma ser bem mais lenta. Vai parecer que o programa falhou ou parou a execuçaõ mas aguarde para imprimir o resultado com lock.

Para testes mais rapidos, reduza "ITERATIONS".

4) Para observar inconsistencias, rode varias vezes:

```powershell
for ($i=1; $i -le 20; $i++) { python "Contador compartilhado(6.1).py" }
```