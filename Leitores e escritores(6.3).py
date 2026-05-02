import threading
import time


BUFFER_SIZE = 6
READERS = 4
WRITERS = 2
LOOPS = 40

PAUSE = 0.0005
WAIT = threading.Event()

FORCE_YIELD = 0.00001

STRESS_READERS = 100
STRESS_WRITERS = 1
STRESS_LOOPS = 30
STRESS_PAUSE = 0.0001


def run_incorrect(
	readers: int = READERS,
	writers: int = WRITERS,
	loops: int = LOOPS,
	pause: float = PAUSE,
) -> dict:
	shared = [0] * BUFFER_SIZE
	inconsistencies = 0
	total_reads = 0

	def writer(writer_id: int) -> None:
		nonlocal shared
		for i in range(1, loops + 1):
			value = writer_id * 100 + i
			for k in range(BUFFER_SIZE):
				shared[k] = value
				time.sleep(FORCE_YIELD)
				WAIT.wait(pause)

	def reader() -> None:
		nonlocal inconsistencies, total_reads
		for _ in range(loops * 2):
			snapshot = []
			for k in range(BUFFER_SIZE):
				snapshot.append(shared[k])
				time.sleep(FORCE_YIELD)
				WAIT.wait(pause)
			total_reads += 1
			if len(set(snapshot)) > 1:
				inconsistencies += 1

	threads = []
	for w in range(writers):
		threads.append(threading.Thread(target=writer, args=(w + 1,)))
	for _ in range(readers):
		threads.append(threading.Thread(target=reader))

	for t in threads:
		t.start()
	for t in threads:
		t.join()

	return {
		"total_reads": total_reads,
		"inconsistencies": inconsistencies,
	}


def run_correct(
	readers: int = READERS,
	writers: int = WRITERS,
	loops: int = LOOPS,
	pause: float = PAUSE,
	log_prefix: str = "[OK ]",
	log_writes: bool = False,
) -> dict:
	shared = [0] * BUFFER_SIZE
	inconsistencies = 0
	total_reads = 0
	readers_active = 0
	reader_mutex = threading.Lock()
	room_empty = threading.Lock()
	turnstile = threading.Lock()

	writer_waits = []
	writer_counts = [0 for _ in range(writers)]

	def writer(writer_id: int) -> None:
		nonlocal shared
		for i in range(1, loops + 1):
			value = writer_id * 100 + i
			start_wait = time.perf_counter()
			with turnstile:
				with room_empty:
					wait_time = time.perf_counter() - start_wait
					writer_waits.append(wait_time)
					for k in range(BUFFER_SIZE):
						shared[k] = value
						WAIT.wait(pause)
			writer_counts[writer_id - 1] += 1
			if log_writes and (i == 1 or i == loops):
				print(f"{log_prefix} escritor {writer_id} escreveu {i}/{loops}")

	def reader() -> None:
		nonlocal inconsistencies, total_reads, readers_active
		for _ in range(loops * 2):
			with turnstile:
				pass
			with reader_mutex:
				readers_active += 1
				if readers_active == 1:
					room_empty.acquire()
			snapshot = []
			for k in range(BUFFER_SIZE):
				snapshot.append(shared[k])
				WAIT.wait(pause)
			total_reads += 1
			if len(set(snapshot)) > 1:
				inconsistencies += 1

			with reader_mutex:
				readers_active -= 1
				if readers_active == 0:
					room_empty.release()

	threads = []
	for w in range(writers):
		threads.append(threading.Thread(target=writer, args=(w + 1,)))
	for _ in range(readers):
		threads.append(threading.Thread(target=reader))

	for t in threads:
		t.start()
	for t in threads:
		t.join()

	return {
		"total_reads": total_reads,
		"inconsistencies": inconsistencies,
		"writer_wait_max": max(writer_waits) if writer_waits else 0.0,
		"writer_wait_avg": (
			sum(writer_waits) / len(writer_waits) if writer_waits else 0.0
		),
		"writer_counts": writer_counts,
	}


def run_stress_tests() -> None:
	print("\n=== Teste de estresse (6.3) ===")
	bad = run_incorrect(
		readers=STRESS_READERS,
		writers=STRESS_WRITERS,
		loops=STRESS_LOOPS,
		pause=STRESS_PAUSE,
	)
	print("[ESTRESSE] incorreto - inconsistencias:", bad["inconsistencies"])
	assert bad["inconsistencies"] > 0

	good = run_correct(
		readers=STRESS_READERS,
		writers=STRESS_WRITERS,
		loops=STRESS_LOOPS,
		pause=STRESS_PAUSE,
		log_prefix="[ESTRESSE]",
		log_writes=True,
	)
	print(
		"[ESTRESSE] correto - espera_max:",
		f"{good['writer_wait_max']:.6f}",
		"espera_media:",
		f"{good['writer_wait_avg']:.6f}",
		"inconsistencias:",
		good["inconsistencies"],
	)
	assert good["inconsistencies"] == 0
	assert all(count == STRESS_LOOPS for count in good["writer_counts"])


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
	run_stress_tests()
