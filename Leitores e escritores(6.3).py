"""
Leitores e escritores (preferencia para leitores).

Objetivo: mostrar uma versao sem sincronizacao e uma versao correta com
controle de acesso ao recurso compartilhado.
"""

import threading


# Parametros do experimento
BUFFER_SIZE = 6
READERS = 4
WRITERS = 2
LOOPS = 40

# Pequena espera para forcar intercalamentos entre as threads.
PAUSE = 0.0005
WAIT = threading.Event()


def run_incorrect() -> dict:
	"""
	Versao incorreta: leitores e escritores acessam sem sincronizacao.
	A escrita ocorre em partes, permitindo leituras parciais.
	"""
	shared = [0] * BUFFER_SIZE
	inconsistencies = 0
	total_reads = 0

	def writer(writer_id: int) -> None:
		nonlocal shared
		for i in range(1, LOOPS + 1):
			# Escreve o mesmo valor em todo o buffer, mas em etapas.
			value = writer_id * 100 + i
			for k in range(BUFFER_SIZE):
				shared[k] = value
				WAIT.wait(PAUSE)

	def reader() -> None:
		nonlocal inconsistencies, total_reads
		for _ in range(LOOPS * 2):
			# Leitura sem lock: pode capturar parte antiga e parte nova.
			snapshot = []
			for k in range(BUFFER_SIZE):
				snapshot.append(shared[k])
				WAIT.wait(PAUSE)
			total_reads += 1
			if len(set(snapshot)) > 1:
				inconsistencies += 1

	threads = []
	for w in range(WRITERS):
		threads.append(threading.Thread(target=writer, args=(w + 1,)))
	for _ in range(READERS):
		threads.append(threading.Thread(target=reader))

	for t in threads:
		t.start()
	for t in threads:
		t.join()

	return {
		"total_reads": total_reads,
		"inconsistencies": inconsistencies,
	}


def run_correct() -> dict:
	"""
	Versao correta com preferencia para leitores:
	- Leitores podem acessar simultaneamente.
	- Escritor tem acesso exclusivo.
	- Risco: escritores podem sofrer starvation se leitores nunca pararem.
	"""
	shared = [0] * BUFFER_SIZE
	inconsistencies = 0
	total_reads = 0

	# Mutex para proteger o contador de leitores.
	reader_mutex = threading.Lock()
	# Mutex de escrita: bloqueia escritores e leitores ao mesmo tempo.
	writer_mutex = threading.Lock()
	readers = 0

	def writer(writer_id: int) -> None:
		nonlocal shared
		for i in range(1, LOOPS + 1):
			value = writer_id * 100 + i
			# Exclusao total para escrita.
			with writer_mutex:
				for k in range(BUFFER_SIZE):
					shared[k] = value
					WAIT.wait(PAUSE)

	def reader() -> None:
		nonlocal inconsistencies, total_reads, readers
		for _ in range(LOOPS * 2):
			# Entrada de leitores (preferencia para leitores).
			with reader_mutex:
				readers += 1
				if readers == 1:
					writer_mutex.acquire()

			# Leitura concorrente (sem bloquear outros leitores).
			snapshot = []
			for k in range(BUFFER_SIZE):
				snapshot.append(shared[k])
				WAIT.wait(PAUSE)
			total_reads += 1
			if len(set(snapshot)) > 1:
				inconsistencies += 1

			# Saida de leitores.
			with reader_mutex:
				readers -= 1
				if readers == 0:
					writer_mutex.release()

	threads = []
	for w in range(WRITERS):
		threads.append(threading.Thread(target=writer, args=(w + 1,)))
	for _ in range(READERS):
		threads.append(threading.Thread(target=reader))

	for t in threads:
		t.start()
	for t in threads:
		t.join()

	return {
		"total_reads": total_reads,
		"inconsistencies": inconsistencies,
	}


def main() -> None:
	print("--- Versao incorreta (sem sincronizacao) ---")
	bad = run_incorrect()
	print("Leituras totais      :", bad["total_reads"])
	print("Leituras inconsistentes:", bad["inconsistencies"])

	print("\n--- Versao corrigida (com sincronizacao) ---")
	good = run_correct()
	print("Leituras totais      :", good["total_reads"])
	print("Leituras inconsistentes:", good["inconsistencies"])


if __name__ == "__main__":
	main()
