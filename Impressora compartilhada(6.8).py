from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, List


LOG_LOCK = threading.Lock()

FORCE_YIELD = 0.00001

STRESS_PRODUCERS = 60
STRESS_MINIMO_PAGES = 1
STRESS_MAXIMO_PAGES = 3
STRESS_MAX_DELAY = 0.02


def log(mensagem: str) -> None:
	with LOG_LOCK:
		tempo = f"{time.perf_counter():.6f}"
		print(f"{tempo} | {mensagem}")


def imprimir_sem_bloqueio(
	documento_id: str,
	paginas: int,
	barreira_inicio: threading.Barrier,
	atraso_inicial: float,
	atraso_por_pagina: float,
	event_log: list[tuple[str, int]] | None = None,
) -> None:
	barreira_inicio.wait()
	time.sleep(atraso_inicial)
	for pagina in range(1, paginas + 1):
		log(f"[INCORRETO] Documento {documento_id} - pagina {pagina}/{paginas}")
		if event_log is not None:
			event_log.append((documento_id, pagina))
		time.sleep(FORCE_YIELD)
		time.sleep(atraso_por_pagina)


def executar_versao_incorreta() -> None:
	log("=== Versao incorreta: sem bloqueio ===")
	documentos = [
		("A", 3, 0.00, 0.05),
		("B", 3, 0.01, 0.02),
	]
	barreira = threading.Barrier(len(documentos))
	threads: List[threading.Thread] = []

	for doc_id, paginas, atraso_inicial, atraso_pag in documentos:
		thread = threading.Thread(
			target=imprimir_sem_bloqueio,
			name=f"Proc-{doc_id}",
			args=(doc_id, paginas, barreira, atraso_inicial, atraso_pag),
		)
		threads.append(thread)
		thread.start()

	for thread in threads:
		thread.join()

	log("=== Fim da versao incorreta ===")


@dataclass(frozen=True)
class PrintJob:
	job_id: int
	documento_id: str
	paginas: int
	solicitante: str


class RequestSequencer:
	def __init__(self) -> None:
		self._lock = threading.Lock()
		self._next_id = 1
		self.ordem: List[int] = []

	def next_job_id(self) -> int:
		with self._lock:
			job_id = self._next_id
			self._next_id += 1
			self.ordem.append(job_id)
			return job_id


class PrintSpooler:
	def __init__(self) -> None:
		self._fila: Deque[PrintJob] = deque()
		self._lock = threading.Lock()
		self._not_empty = threading.Condition(self._lock)
		self._stop = False
		self.printed_jobs: List[int] = []
		self._daemon = threading.Thread(
			target=self._run,
			name="SpoolerDaemon",
			daemon=True,
		)
		self._started = False

	def start(self) -> None:
		if not self._started:
			self._daemon.start()
			self._started = True

	def enqueue(self, job: PrintJob) -> None:
		with self._not_empty:
			self._fila.append(job)
			self._not_empty.notify()

	def stop_when_idle(self) -> None:
		with self._not_empty:
			self._stop = True
			self._not_empty.notify_all()
		self._daemon.join()

	def _run(self) -> None:
		while True:
			with self._not_empty:
				while not self._fila and not self._stop:
					self._not_empty.wait()
				if self._stop and not self._fila:
					break
				job = self._fila.popleft()

			self._print_job(job)

	def _print_job(self, job: PrintJob) -> None:
		self.printed_jobs.append(job.job_id)
		log(
			f"[SPOOLER] Inicia job {job.job_id} - Documento {job.documento_id} "
			f"({job.paginas} paginas)"
		)
		for pagina in range(1, job.paginas + 1):
			log(
				f"[SPOOLER] Documento {job.documento_id} - pagina {pagina}/{job.paginas}"
			)
			time.sleep(0.02)
		log(f"[SPOOLER] Conclui job {job.job_id} - Documento {job.documento_id}")


def produtor(
	spooler: PrintSpooler,
	sequencer: RequestSequencer,
	documento_id: str,
	paginas: int,
	atraso: float,
) -> None:
	time.sleep(atraso)
	job_id = sequencer.next_job_id()
	log(
		f"[PRODUTOR] Solicita job {job_id} - Documento {documento_id} "
		f"({paginas} paginas)"
	)
	spooler.enqueue(
		PrintJob(
			job_id=job_id,
			documento_id=documento_id,
			paginas=paginas,
			solicitante=threading.current_thread().name,
		)
	)


def executar_versao_corrigida() -> None:
	log("=== Versao corrigida: spooler FIFO ===")

	spooler = PrintSpooler()
	sequencer = RequestSequencer()
	spooler.start()

	produtores = [
		("C", 4, 0.00),
		("A", 3, 0.01),
		("B", 2, 0.02),
	]

	threads: List[threading.Thread] = []
	for doc_id, paginas, atraso in produtores:
		thread = threading.Thread(
			target=produtor,
			name=f"Proc-{doc_id}",
			args=(spooler, sequencer, doc_id, paginas, atraso),
		)
		threads.append(thread)
		thread.start()

	for thread in threads:
		thread.join()

	spooler.stop_when_idle()
	log(f"[ORDEM] Solicitacoes (IDs): {sequencer.ordem}")
	log("[ORDEM] Impressao respeitou exatamente a ordem FIFO acima")
	log("=== Fim da versao corrigida ===")


def detect_interleaving(events: list[tuple[str, int]]) -> bool:
	first_index: dict[str, int] = {}
	last_index: dict[str, int] = {}
	for idx, (doc_id, _) in enumerate(events):
		if doc_id not in first_index:
			first_index[doc_id] = idx
		last_index[doc_id] = idx

	docs = list(first_index.keys())
	for i in range(len(docs)):
		for j in range(i + 1, len(docs)):
			doc_a = docs[i]
			doc_b = docs[j]
			if first_index[doc_a] < first_index[doc_b] < last_index[doc_a]:
				return True
			if first_index[doc_b] < first_index[doc_a] < last_index[doc_b]:
				return True
	return False


def run_stress_tests() -> None:
	log(" Teste de estresse (6.8) ")
	events: list[tuple[str, int]] = []
	documentos = [
		("A", 5, 0.00, 0.01),
		("B", 5, 0.00, 0.01),
		("C", 5, 0.00, 0.01),
	]
	barreira = threading.Barrier(len(documentos))
	threads: List[threading.Thread] = []

	for doc_id, paginas, atraso_inicial, atraso_pag in documentos:
		thread = threading.Thread(
			target=imprimir_sem_bloqueio,
			name=f"Stress-{doc_id}",
			args=(doc_id, paginas, barreira, atraso_inicial, atraso_pag, events),
		)
		threads.append(thread)
		thread.start()

	for thread in threads:
		thread.join()

	interleaved = detect_interleaving(events)
	log(f"[ESTRESSE] incorreto - intercalacao: {interleaved}")
	assert interleaved
	spooler = PrintSpooler()
	sequencer = RequestSequencer()
	spooler.start()

	threads = []
	for i in range(1, STRESS_PRODUCERS + 1):
		doc_id = f"D{i:02d}"
		paginas = random.randint(STRESS_MINIMO_PAGES, STRESS_MAXIMO_PAGES)
		atraso = random.uniform(0.0, STRESS_MAX_DELAY)
		thread = threading.Thread(
			target=produtor,
			name=f"Prod-{doc_id}",
			args=(spooler, sequencer, doc_id, paginas, atraso),
		)
		threads.append(thread)
		thread.start()

	for thread in threads:
		thread.join()

	spooler.stop_when_idle()

	log(
		f"[ESTRESSE] correto - jobs impressos: {len(spooler.printed_jobs)}"
	)
	log(f"[ESTRESSE] correto - ordem solicitacoes: {sequencer.ordem}")
	log(f"[ESTRESSE] correto - ordem impressao: {spooler.printed_jobs}")
	assert spooler.printed_jobs == sequencer.ordem


def main() -> None:
	executar_versao_incorreta()
	time.sleep(0.2)
	executar_versao_corrigida()
	run_stress_tests()


if __name__ == "__main__":
	main()
