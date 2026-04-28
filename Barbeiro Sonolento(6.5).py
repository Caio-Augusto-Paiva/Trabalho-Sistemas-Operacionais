import threading
import time
import random


CHAIRS = 3
TOTAL_CLIENTS = 10
ARRIVAL_MIN = 0.01
ARRIVAL_MAX = 0.25
CUT_MIN = 0.05
CUT_MAX = 0.15


def run_incorrect():
	print("=== VERSAO INCORRETA (sem exclusao mutua) ===")

	waiting = 0
	barber_sleeping = True
	closing = threading.Event()
	busy_spin = 0

	def barber():
		nonlocal waiting, barber_sleeping, busy_spin
		while True:
			if waiting == 0:
				if closing.is_set():
					print("[INCORRETO] Barbeiro encerrou o turno")
					return
				if not barber_sleeping:
					print("[INCORRETO] Barbeiro dormindo (sem protecao)")
				barber_sleeping = True
				busy_spin += 1
				if busy_spin % 2000 == 0:
					print("[INCORRETO] Barbeiro em espera ocupada (busy waiting)")
				time.sleep(0.001)
				continue

			waiting -= 1
			if waiting < 0:
				print("[INCORRETO] ERRO: contador de espera negativo")
				waiting = 0

			barber_sleeping = False
			print("[INCORRETO] Barbeiro cortando cabelo")
			time.sleep(random.uniform(CUT_MIN, CUT_MAX))

	def client(cid):
		nonlocal waiting, barber_sleeping
		time.sleep(random.uniform(ARRIVAL_MIN, ARRIVAL_MAX))

		if waiting >= CHAIRS:
			time.sleep(random.uniform(0.0, 0.01))
			if waiting < CHAIRS:
				print(
					f"[INCORRETO] ERRO: Cliente {cid} foi embora, mas havia cadeira livre"
				)
			else:
				print(f"[INCORRETO] Cliente {cid} foi embora (barbearia cheia)")
			return

		print(f"[INCORRETO] Cliente {cid} sentou na sala de espera")
		time.sleep(random.uniform(0.0, 0.02))
		waiting += 1
		if waiting > CHAIRS:
			print(
				f"[INCORRETO] ERRO: cadeiras ocupadas = {waiting} > {CHAIRS}"
			)

		if barber_sleeping:
			print(f"[INCORRETO] Cliente {cid} acorda o barbeiro")
			barber_sleeping = False

	barber_thread = threading.Thread(target=barber, name="Barbeiro-Incorreto")
	barber_thread.start()

	clients = []
	for cid in range(1, TOTAL_CLIENTS + 1):
		t = threading.Thread(target=client, args=(cid,), name=f"Cliente-{cid}")
		clients.append(t)
		t.start()

	for t in clients:
		t.join()

	closing.set()
	barber_thread.join()
	print("=== FIM DA VERSAO INCORRETA ===\n")


def run_correct():
	print("=== VERSAO CORRETA (Dijkstra) ===")

	waiting = 0
	closing = threading.Event()
	mutex = threading.Lock()
	customers = threading.Semaphore(0)
	barber_ready = threading.Semaphore(0)

	# Justificativa tecnica: o mutex torna atomicas as operacoes sobre
	# waiting, eliminando a corrida entre verificar cadeiras e dormir.
	# O semaforo customers bloqueia o barbeiro quando nao ha clientes,
	# evitando espera ocupada. O semaforo barber_ready sincroniza o
	# inicio do corte, garantindo que o cliente so avance quando o
	# barbeiro estiver pronto.

	def barber():
		nonlocal waiting
		while True:
			with mutex:
				if waiting == 0 and not closing.is_set():
					print("[CORRETO] Barbeiro dormindo (aguardando clientes)")

			customers.acquire()

			with mutex:
				if waiting == 0 and closing.is_set():
					print("[CORRETO] Barbeiro encerrou o turno")
					return
				waiting -= 1
				barber_ready.release()

			print("[CORRETO] Barbeiro cortando cabelo")
			time.sleep(random.uniform(CUT_MIN, CUT_MAX))

	def client(cid):
		nonlocal waiting
		time.sleep(random.uniform(ARRIVAL_MIN, ARRIVAL_MAX))

		with mutex:
			if waiting < CHAIRS:
				waiting += 1
				if waiting == 1:
					print(f"[CORRETO] Cliente {cid} acorda o barbeiro")
				print(f"[CORRETO] Cliente {cid} senta na sala de espera")
				customers.release()
			else:
				print(f"[CORRETO] Cliente {cid} foi embora (barbearia cheia)")
				return

		barber_ready.acquire()
		print(f"[CORRETO] Cliente {cid} na cadeira do barbeiro")

	barber_thread = threading.Thread(target=barber, name="Barbeiro-Correto")
	barber_thread.start()

	clients = []
	for cid in range(1, TOTAL_CLIENTS + 1):
		t = threading.Thread(target=client, args=(cid,), name=f"Cliente-{cid}")
		clients.append(t)
		t.start()

	for t in clients:
		t.join()

	closing.set()
	customers.release()
	barber_thread.join()
	print("=== FIM DA VERSAO CORRETA ===")


if __name__ == "__main__":
	random.seed(42)
	run_incorrect()
	run_correct()
