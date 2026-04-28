"""Impressora compartilhada (6.8).

Este arquivo demonstra duas versoes:
1) Versao incorreta sem bloqueio (intercalacao de paginas).
2) Versao corrigida com spooler FIFO (ordem de chegada preservada).
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, List


LOG_LOCK = threading.Lock()


def log(mensagem: str) -> None:
	"""Escreve logs de forma atomica para evitar linhas quebradas."""
	with LOG_LOCK:
		tempo = f"{time.perf_counter():.6f}"
		print(f"{tempo} | {mensagem}")


def imprimir_sem_bloqueio(
	documento_id: str,
	paginas: int,
	barreira_inicio: threading.Barrier,
	atraso_inicial: float,
	atraso_por_pagina: float,
) -> None:
	"""Impressao direta, sem exclusao mutua e sem fila."""
	barreira_inicio.wait()
	time.sleep(atraso_inicial)
	for pagina in range(1, paginas + 1):
		log(f"[INCORRETO] Documento {documento_id} - pagina {pagina}/{paginas}")
		time.sleep(atraso_por_pagina)


def executar_versao_incorreta() -> None:
	"""Executa a versao sem bloqueio para mostrar intercalacao."""
	log("=== Versao incorreta: sem bloqueio ===")
	documentos = [
		# Atrasos escolhidos para provocar intercalacao deterministica
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
	"""Representa um trabalho de impressao enfileirado."""

	job_id: int
	documento_id: str
	paginas: int
	solicitante: str


class RequestSequencer:
	"""Gera IDs sequenciais para registrar a ordem de chegada."""

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
	"""Spooler FIFO com daemon de impressao."""

	def __init__(self) -> None:
		self._fila: Deque[PrintJob] = deque()
		self._lock = threading.Lock()
		self._not_empty = threading.Condition(self._lock)
		self._stop = False
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
		"""Enfileira um trabalho mantendo a ordem de chegada."""
		with self._not_empty:
			self._fila.append(job)
			self._not_empty.notify()

	def stop_when_idle(self) -> None:
		"""Sinaliza parada apos a fila esvaziar e aguarda o daemon."""
		with self._not_empty:
			self._stop = True
			self._not_empty.notify_all()
		self._daemon.join()

	def _run(self) -> None:
		"""Daemon que atende a fila em ordem FIFO."""
		while True:
			with self._not_empty:
				while not self._fila and not self._stop:
					self._not_empty.wait()
				if self._stop and not self._fila:
					break
				job = self._fila.popleft()

			self._print_job(job)

	def _print_job(self, job: PrintJob) -> None:
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
	"""Thread produtora: apenas solicita impressao, sem imprimir."""
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
	"""Executa a versao com spooler FIFO e daemon."""
	log("=== Versao corrigida: spooler FIFO ===")

	# Nota tecnica:
	# Um Mutex/Lock garante exclusao mutua, mas NAO garante ordem de atendimento.
	# O escalonador do SO pode acordar threads em ordem diferente da chegada,
	# levando a injustica. A fila FIFO + Condition separa o pedido do atendimento:
	# produtores apenas enfileiram, e o daemon imprime em ordem, garantindo fairness.

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


def main() -> None:
	executar_versao_incorreta()
	time.sleep(0.2)
	executar_versao_corrigida()


if __name__ == "__main__":
	main()
