"""
Produtor-consumidor com buffer limitado.

Objetivo: mostrar uma versao incorreta (sem sincronizacao) e a versao
corrigida com semaforos de contagem e mutex.
"""

import threading
import time


# Parametros do experimento
BUFFER_SIZE = 5
ITEMS_TOTAL = 30

# Delays diferentes ajudam a expor o problema na versao incorreta.
PRODUCER_DELAY = 0.001
CONSUMER_DELAY = 0.004


def run_incorrect() -> dict:
	"""
	Versao incorreta: sem semaforos e sem mutex.
	Mostra leituras de buffer vazio e sobrescritas em buffer cheio.
	"""
	buffer = [None] * BUFFER_SIZE
	in_idx = 0
	out_idx = 0
	count = 0

	produced_items = []
	consumed_items = []
	errors = {"overwrites": 0, "underreads": 0}

	def producer() -> None:
		nonlocal in_idx, count
		for item in range(1, ITEMS_TOTAL + 1):
			# Sem sincronizacao: pode escrever mesmo com buffer cheio.
			if count >= BUFFER_SIZE:
				errors["overwrites"] += 1
				print("ERRO: produtor sobrescreveu buffer cheio")

			buffer[in_idx] = item
			in_idx = (in_idx + 1) % BUFFER_SIZE
			count += 1
			produced_items.append(item)
			time.sleep(PRODUCER_DELAY)

	def consumer() -> None:
		nonlocal out_idx, count
		for _ in range(ITEMS_TOTAL):
			# Sem sincronizacao: pode ler mesmo com buffer vazio.
			if count <= 0:
				errors["underreads"] += 1
				print("ERRO: consumidor tentou ler buffer vazio")

			item = buffer[out_idx]
			buffer[out_idx] = None
			out_idx = (out_idx + 1) % BUFFER_SIZE
			count -= 1
			consumed_items.append(item)
			time.sleep(CONSUMER_DELAY)

	# Inicia o consumidor antes para aumentar a chance de leitura de vazio.
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
	"""
	Versao correta: semaforos de contagem + mutex para a secao critica.
	"""
	buffer = [None] * BUFFER_SIZE
	in_idx = 0
	out_idx = 0

	empty_slots = threading.Semaphore(BUFFER_SIZE)
	full_slots = threading.Semaphore(0)
	mutex = threading.Lock()

	produced_items = []
	consumed_items = []

	def producer() -> None:
		nonlocal in_idx
		for item in range(1, ITEMS_TOTAL + 1):
			# Espera vaga no buffer.
			empty_slots.acquire()
			with mutex:
				buffer[in_idx] = item
				in_idx = (in_idx + 1) % BUFFER_SIZE
				produced_items.append(item)
			# Sinaliza item disponivel.
			full_slots.release()
			time.sleep(PRODUCER_DELAY)

	def consumer() -> None:
		nonlocal out_idx
		for _ in range(ITEMS_TOTAL):
			# Espera item disponivel.
			full_slots.acquire()
			with mutex:
				item = buffer[out_idx]
				buffer[out_idx] = None
				out_idx = (out_idx + 1) % BUFFER_SIZE
				consumed_items.append(item)
			# Sinaliza vaga liberada.
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
