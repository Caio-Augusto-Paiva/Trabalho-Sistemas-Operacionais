import threading
import time
from typing import Optional

THREADS = 10
ITERATIONS = 1_000_000
YIELD_EVERY = 1_000
contador = 0


def deltaAplicado(delta: int, i: int, use_lock: bool, lock: Optional[threading.Lock]) -> None:
	global contador

	if use_lock:
		with lock:
			temp = contador
			if i % YIELD_EVERY == 0:
				time.sleep(0)
			contador = temp + delta
	else:
		temp = contador
		if i % YIELD_EVERY == 0:
			time.sleep(0)
		contador = temp + delta


def worker(iterations: int, use_lock: bool, lock: Optional[threading.Lock]) -> None:
	for i in range(iterations):
		deltaAplicado(+1, i, use_lock, lock)
	for i in range(iterations):
		deltaAplicado(-1, i, use_lock, lock)


def experimento(threads: int, iterations: int, use_lock: bool) -> int:
	global contador
	contador = 0

	lock = threading.Lock() if use_lock else None
	thread_list = [
		threading.Thread(target=worker, args=(iterations, use_lock, lock))
		for _ in range(threads)
	]

	for t in thread_list:
		t.start()
	for t in thread_list:
		t.join()

	return contador


def main() -> None:
	expected = 0

	resultadoRuim = experimento(THREADS, ITERATIONS, use_lock=False)
	print("Versao incorreta (sem lock):", resultadoRuim, "| esperado:", expected)

	resultadoBom = experimento(THREADS, ITERATIONS, use_lock=True)
	print("Versao corrigida (com lock):", resultadoBom, "| esperado:", expected)

	print("Sem lock  :", resultadoRuim)
	print("Com lock  :", resultadoBom)


if __name__ == "__main__":
	main()
