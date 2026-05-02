import threading
import time
TAMANHO_DO_BUFFER = 5
ITEMS_TOTAL = 30

PRODUCER_DELAY = 0.001
CONSUMER_DELAY = 0.004

FORCE_YIELD = 0.00001

STRESS_PRODUCERS = 60
STRESS_CONSUMERS = 60
STRESS_ITEMS_PER_PRODUCER = 40
STRESS_ITEMS_PER_CONSUMER = 40
STRESS_TAMANHO_DO_BUFFER = 5
STRESS_PRODUCER_DELAY = 0.0002
STRESS_CONSUMER_DELAY = 0.0002


def run_incorrect() -> dict:

	buffer = [None] * TAMANHO_DO_BUFFER
	in_idx = 0
	out_idx = 0
	count = 0

	produced_items = []
	consumed_items = []
	errors = {"overwrites": 0, "underreads": 0}

	def producer() -> None:
		nonlocal in_idx, count
		for item in range(1, ITEMS_TOTAL + 1):
			if count >= TAMANHO_DO_BUFFER:
				errors["overwrites"] += 1
				print("ERRO: produtor sobrescreveu buffer cheio")

			time.sleep(FORCE_YIELD)
			buffer[in_idx] = item
			time.sleep(FORCE_YIELD)
			in_idx = (in_idx + 1) % TAMANHO_DO_BUFFER
			count += 1
			produced_items.append(item)
			time.sleep(PRODUCER_DELAY)

	def consumer() -> None:
		nonlocal out_idx, count
		for _ in range(ITEMS_TOTAL):
			if count <= 0:
				errors["underreads"] += 1
				print("ERRO: consumidor tentou ler buffer vazio")

			time.sleep(FORCE_YIELD)
			item = buffer[out_idx]
			buffer[out_idx] = None
			time.sleep(FORCE_YIELD)
			out_idx = (out_idx + 1) % TAMANHO_DO_BUFFER
			count -= 1
			consumed_items.append(item)
			time.sleep(CONSUMER_DELAY)

	t_consumer = threading.Thread(target=consumer)
	t_producer = threading.Thread(target=producer)

	t_consumer.start()
	time.sleep(0.02)
	t_producer.start()

	t_consumer.join()
	t_producer.join()

	none_reads = sum(1 for x in consumed_items if x is None)
	unique_consumed = len(set(x for x in consumed_items if x is not None))

	return {
		"final_count": count,
		"produced": len(produced_items),
		"consumed": len(consumed_items),
		"unique_consumed": unique_consumed,
		"none_reads": none_reads,
		"overwrites": errors["overwrites"],
		"underreads": errors["underreads"],
	}


def run_correct() -> dict:
	buffer = [None] * TAMANHO_DO_BUFFER
	in_idx = 0
	out_idx = 0

	empty_slots = threading.Semaphore(TAMANHO_DO_BUFFER)
	full_slots = threading.Semaphore(0)
	mutex = threading.Lock()

	produced_items = []
	consumed_items = []

	def producer() -> None:
		nonlocal in_idx
		for item in range(1, ITEMS_TOTAL + 1):
			empty_slots.acquire()
			with mutex:
				buffer[in_idx] = item
				in_idx = (in_idx + 1) % TAMANHO_DO_BUFFER
				produced_items.append(item)
			full_slots.release()
			time.sleep(PRODUCER_DELAY)

	def consumer() -> None:
		nonlocal out_idx
		for _ in range(ITEMS_TOTAL):
			full_slots.acquire()
			with mutex:
				item = buffer[out_idx]
				buffer[out_idx] = None
				out_idx = (out_idx + 1) % TAMANHO_DO_BUFFER
				consumed_items.append(item)
			empty_slots.release()
			time.sleep(CONSUMER_DELAY)

	t_producer = threading.Thread(target=producer)
	t_consumer = threading.Thread(target=consumer)

	t_producer.start()
	t_consumer.start()

	t_producer.join()
	t_consumer.join()

	produced_set = set(produced_items)
	consumed_set = set(consumed_items)
	missing = produced_set - consumed_set
	extra = consumed_set - produced_set
	duplicates = len(consumed_items) - len(consumed_set)

	return {
		"produced": len(produced_items),
		"consumed": len(consumed_items),
		"missing": len(missing),
		"extra": len(extra),
		"duplicates": duplicates,
	}


def stress_test_incorrect() -> dict:
	buffer = [None] * STRESS_TAMANHO_DO_BUFFER
	in_idx = 0
	out_idx = 0
	count = 0
	errors = {"overwrites": 0, "underreads": 0, "none_reads": 0}
	errors_lock = threading.Lock()

	def producer(pid: int) -> None:
		nonlocal in_idx, count
		for item in range(1, STRESS_ITEMS_PER_PRODUCER + 1):
			if count >= STRESS_TAMANHO_DO_BUFFER:
				with errors_lock:
					errors["overwrites"] += 1
			time.sleep(FORCE_YIELD)
			buffer[in_idx] = (pid, item)
			time.sleep(FORCE_YIELD)
			in_idx = (in_idx + 1) % STRESS_TAMANHO_DO_BUFFER
			count += 1
			time.sleep(STRESS_PRODUCER_DELAY)

	def consumer() -> None:
		nonlocal out_idx, count
		for _ in range(STRESS_ITEMS_PER_CONSUMER):
			if count <= 0:
				with errors_lock:
					errors["underreads"] += 1
			time.sleep(FORCE_YIELD)
			item = buffer[out_idx]
			buffer[out_idx] = None
			time.sleep(FORCE_YIELD)
			out_idx = (out_idx + 1) % STRESS_TAMANHO_DO_BUFFER
			count -= 1
			if item is None:
				with errors_lock:
					errors["none_reads"] += 1
			time.sleep(STRESS_CONSUMER_DELAY)

	threads = []
	for pid in range(1, STRESS_PRODUCERS + 1):
		threads.append(threading.Thread(target=producer, args=(pid,)))
	for _ in range(STRESS_CONSUMERS):
		threads.append(threading.Thread(target=consumer))

	for t in threads:
		t.start()
	for t in threads:
		t.join()

	return errors


def stress_test_correct() -> dict:
	buffer = [None] * STRESS_TAMANHO_DO_BUFFER
	in_idx = 0
	out_idx = 0
	count = 0
	max_count = 0
	min_count = 0

	empty_slots = threading.Semaphore(STRESS_TAMANHO_DO_BUFFER)
	full_slots = threading.Semaphore(0)
	mutex = threading.Lock()

	produced_items = []
	consumed_items = []

	def producer(pid: int) -> None:
		nonlocal in_idx, count, max_count, min_count
		for item in range(1, STRESS_ITEMS_PER_PRODUCER + 1):
			empty_slots.acquire()
			with mutex:
				buffer[in_idx] = (pid, item)
				in_idx = (in_idx + 1) % STRESS_TAMANHO_DO_BUFFER
				count += 1
				max_count = max(max_count, count)
				min_count = min(min_count, count)
				assert 0 <= count <= STRESS_TAMANHO_DO_BUFFER
				produced_items.append((pid, item))
			full_slots.release()
			time.sleep(STRESS_PRODUCER_DELAY)

	def consumer() -> None:
		nonlocal out_idx, count, max_count, min_count
		for _ in range(STRESS_ITEMS_PER_CONSUMER):
			full_slots.acquire()
			with mutex:
				item = buffer[out_idx]
				buffer[out_idx] = None
				out_idx = (out_idx + 1) % STRESS_TAMANHO_DO_BUFFER
				count -= 1
				max_count = max(max_count, count)
				min_count = min(min_count, count)
				assert 0 <= count <= STRESS_TAMANHO_DO_BUFFER
				consumed_items.append(item)
			empty_slots.release()
			time.sleep(STRESS_CONSUMER_DELAY)

	threads = []
	for pid in range(1, STRESS_PRODUCERS + 1):
		threads.append(threading.Thread(target=producer, args=(pid,)))
	for _ in range(STRESS_CONSUMERS):
		threads.append(threading.Thread(target=consumer))

	for t in threads:
		t.start()
	for t in threads:
		t.join()

	produced_set = set(produced_items)
	consumed_set = set(consumed_items)
	missing = produced_set - consumed_set
	extra = consumed_set - produced_set
	duplicates = len(consumed_items) - len(consumed_set)

	return {
		"max_count": max_count,
		"min_count": min_count,
		"missing": len(missing),
		"extra": len(extra),
		"duplicates": duplicates,
	}


def run_stress_tests() -> None:
	print("\n=== Teste de estresse (6.2) ===")
	bad = stress_test_incorrect()
	print(
		"[ESTRESSE] incorreto - sobrescritas:",
		bad["overwrites"],
		"leituras_vazias:",
		bad["underreads"],
		"leituras_None:",
		bad["none_reads"],
	)
	assert bad["overwrites"] > 0 or bad["underreads"] > 0 or bad["none_reads"] > 0

	good = stress_test_correct()
	print(
		"[ESTRESSE] correto - max_count:",
		good["max_count"],
		"min_count:",
		good["min_count"],
		"missing:",
		good["missing"],
		"extra:",
		good["extra"],
		"duplicates:",
		good["duplicates"],
	)
	assert good["max_count"] <= STRESS_TAMANHO_DO_BUFFER
	assert good["min_count"] >= 0
	assert good["missing"] == 0
	assert good["extra"] == 0
	assert good["duplicates"] == 0


def main() -> None:
	print("--- Versao incorreta (sem sincronizacao) ---")
	bad = run_incorrect()
	print("Resumo incorreto:")
	print("- count_final         :", bad["final_count"])
	print("- produzidos          :", bad["produced"])
	print("- consumidos          :", bad["consumed"])
	print("- consumidos_unicos   :", bad["unique_consumed"])
	print("- leituras_de_None    :", bad["none_reads"])
	print("- sobrescritas        :", bad["overwrites"])
	print("- leituras_de_vazio   :", bad["underreads"])

	print("\n--- Versao corrigida (semaforos + mutex) ---")
	good = run_correct()
	print("Resumo corrigido:")
	print("- produzidos          :", good["produced"])
	print("- consumidos          :", good["consumed"])
	print("- faltantes           :", good["missing"])
	print("- extras              :", good["extra"])
	print("- duplicados          :", good["duplicates"])


if __name__ == "__main__":
	main()
	run_stress_tests()
