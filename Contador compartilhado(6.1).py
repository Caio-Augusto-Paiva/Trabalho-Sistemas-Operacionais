"""
Contador compartilhado com e sem exclusao mutua.

Objetivo: demonstrar condicao de corrida em threads e como o Lock corrige.
"""

import threading
import time
from typing import Optional


# Parametros do experimento
THREADS = 10
ITERATIONS = 1_000_000

# Forca alternancia de contexto para evidenciar a corrida.
YIELD_EVERY = 1_000

# Variavel global compartilhada entre as threads.
counter = 0


def apply_delta(delta: int, i: int, use_lock: bool, lock: Optional[threading.Lock]) -> None:
	"""
	Atualiza o contador com uma operacao de leitura-modificacao-escrita.
	Essa sequencia e a secao critica: deve ser atomica.
	"""
	global counter

	if use_lock:
		# Exclusao mutua: so uma thread executa a secao critica por vez.
		with lock:
			temp = counter
			if i % YIELD_EVERY == 0:
				time.sleep(0)
			counter = temp + delta
	else:
		# Sem protecao: varias threads podem intercalar leituras/escritas.
		temp = counter
		if i % YIELD_EVERY == 0:
			time.sleep(0)
		counter = temp + delta


def worker(iterations: int, use_lock: bool, lock: Optional[threading.Lock]) -> None:
	"""
	Cada thread faz muitos incrementos e decrementos no mesmo contador global.
	"""
	for i in range(iterations):
		apply_delta(+1, i, use_lock, lock)
	for i in range(iterations):
		apply_delta(-1, i, use_lock, lock)


def run_experiment(threads: int, iterations: int, use_lock: bool) -> int:
	"""
	Executa o experimento e retorna o valor final do contador.
	"""
	global counter
	counter = 0

	lock = threading.Lock() if use_lock else None
	thread_list = [
		threading.Thread(target=worker, args=(iterations, use_lock, lock))
		for _ in range(threads)
	]

	for t in thread_list:
		t.start()
	for t in thread_list:
		t.join()

	return counter


def main() -> None:
	expected = 0

	# Versao incorreta (sem protecao)
	result_bad = run_experiment(THREADS, ITERATIONS, use_lock=False)
	print("Versao incorreta (sem lock):", result_bad, "| esperado:", expected)

	# Versao corrigida (com protecao)
	result_good = run_experiment(THREADS, ITERATIONS, use_lock=True)
	print("Versao corrigida (com lock):", result_good, "| esperado:", expected)

	# Comparacao direta
	print("Comparacao:")
	print("- Sem lock  :", result_bad)
	print("- Com lock  :", result_good)


if __name__ == "__main__":
	main()
