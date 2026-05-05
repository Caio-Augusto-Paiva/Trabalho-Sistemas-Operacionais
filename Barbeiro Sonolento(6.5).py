import threading
import time
import random

CHAIRS = 3
TOTAL_CLIENTS = 10
ARRIVAL_MIN = 0.01
ARRIVAL_MAX = 0.25
CUT_MIN = 0.05
CUT_MAX = 0.15

FORCE_YIELD = 0.00001

STRESS_CLIENTS = 40
STRESS_CHAIRS = 5
STRESS_ARRIVAL_MIN = 0.0
STRESS_ARRIVAL_MAX = 0.001
STRESS_CUT_MIN = 0.001
STRESS_CUT_MAX = 0.003

def run_incorrect(
	* ,
	chairs: int = CHAIRS,
	total_clients: int = TOTAL_CLIENTS,
	arrival_min: float = ARRIVAL_MIN,
	arrival_max: float = ARRIVAL_MAX,
	cut_min: float = CUT_MIN,
	cut_max: float = CUT_MAX,
	start_barrier: threading.Barrier | None = None,
) -> dict:
	print("=== VERSAO INCORRETA (sem exclusao mutua) ===")

	waiting = 0
	barber_sleeping = True
	closing = threading.Event()
	busy_spin = 0
	max_waiting = 0
	errors = {"over_capacity": 0, "negative_wait": 0}

	def barber():
		nonlocal waiting, barber_sleeping, busy_spin
		while True:
			if waiting == 0:
				time.sleep(FORCE_YIELD)
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

			time.sleep(FORCE_YIELD)
			waiting -= 1
			if waiting < 0:
				print("[INCORRETO] ERRO: contador de espera negativo")
				waiting = 0
				errors["negative_wait"] += 1

			barber_sleeping = False
			print("[INCORRETO] Barbeiro cortando cabelo")
			time.sleep(random.uniform(cut_min, cut_max))

	def client(cid):
		nonlocal waiting, barber_sleeping, max_waiting
		time.sleep(random.uniform(arrival_min, arrival_max))
		if start_barrier is not None:
			start_barrier.wait()

		if waiting >= chairs:
			time.sleep(FORCE_YIELD)
			time.sleep(random.uniform(0.0, 0.01))
			if waiting < chairs:
				print(
					f"[INCORRETO] ERRO: Cliente {cid} foi embora, mas havia cadeira livre"
				)
			else:
				print(f"[INCORRETO] Cliente {cid} foi embora (barbearia cheia)")
			return

		print(f"[INCORRETO] Cliente {cid} sentou na sala de espera")
		time.sleep(random.uniform(0.0, 0.02))
		time.sleep(FORCE_YIELD)
		waiting += 1
		max_waiting = max(max_waiting, waiting)
		if waiting > chairs:
			print(
				f"[INCORRETO] ERRO: cadeiras ocupadas = {waiting} > {chairs}"
			)
			errors["over_capacity"] += 1

		if barber_sleeping:
			print(f"[INCORRETO] Cliente {cid} acorda o barbeiro")
			barber_sleeping = False

	barber_thread = threading.Thread(target=barber, name="Barbeiro-Incorreto")
	barber_thread.start()

	clients = []
	for cid in range(1, total_clients + 1):
		t = threading.Thread(target=client, args=(cid,), name=f"Cliente-{cid}")
		clients.append(t)
		t.start()

	for t in clients:
		t.join()

	closing.set()
	barber_thread.join()
	print("=== FIM DA VERSAO INCORRETA ===\n")

	return {
		"max_waiting": max_waiting,
		"over_capacity": errors["over_capacity"],
		"negative_wait": errors["negative_wait"],
	}


def run_correct(
	* ,
	chairs: int = CHAIRS,
	total_clients: int = TOTAL_CLIENTS,
	arrival_min: float = ARRIVAL_MIN,
	arrival_max: float = ARRIVAL_MAX,
	cut_min: float = CUT_MIN,
	cut_max: float = CUT_MAX,
	start_barrier: threading.Barrier | None = None,
) -> dict:
	print("=== VERSAO CORRETA (Dijkstra) ===")

	waiting = 0
	closing = threading.Event()
	mutex = threading.Lock()
	customers = threading.Semaphore(0)
	barber_ready = threading.Semaphore(0)
	max_waiting = 0

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
				assert waiting >= 0
				barber_ready.release()

			print("[CORRETO] Barbeiro cortando cabelo")
			time.sleep(random.uniform(cut_min, cut_max))

	def client(cid):
		nonlocal waiting, max_waiting
		time.sleep(random.uniform(arrival_min, arrival_max))
		if start_barrier is not None:
			start_barrier.wait()

		with mutex:
			if waiting < chairs:
				waiting += 1
				max_waiting = max(max_waiting, waiting)
				assert waiting <= chairs
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
	for cid in range(1, total_clients + 1):
		t = threading.Thread(target=client, args=(cid,), name=f"Cliente-{cid}")
		clients.append(t)
		t.start()

	for t in clients:
		t.join()

	closing.set()
	customers.release()
	barber_thread.join()
	print("=== FIM DA VERSAO CORRETA ===")

	return {"max_waiting": max_waiting}


def run_stress_tests() -> None:
	print("\n=== Teste de estresse (6.5) ===")
	barrier = threading.Barrier(STRESS_CLIENTS)
	bad = run_incorrect(
		chairs=STRESS_CHAIRS,
		total_clients=STRESS_CLIENTS,
		arrival_min=STRESS_ARRIVAL_MIN,
		arrival_max=STRESS_ARRIVAL_MAX,
		cut_min=STRESS_CUT_MIN,
		cut_max=STRESS_CUT_MAX,
		start_barrier=barrier,
	)
	print(
		"[ESTRESSE] incorreto - over_capacity:",
		bad["over_capacity"],
		"negative_wait:",
		bad["negative_wait"],
	)
	assert bad["over_capacity"] > 0 or bad["negative_wait"] > 0

	barrier = threading.Barrier(STRESS_CLIENTS)
	good = run_correct(
		chairs=STRESS_CHAIRS,
		total_clients=STRESS_CLIENTS,
		arrival_min=STRESS_ARRIVAL_MIN,
		arrival_max=STRESS_ARRIVAL_MAX,
		cut_min=STRESS_CUT_MIN,
		cut_max=STRESS_CUT_MAX,
		start_barrier=barrier,
	)
	print("[ESTRESSE] correto - max_waiting:", good["max_waiting"])
	assert good["max_waiting"] <= STRESS_CHAIRS


if __name__ == "__main__":
	random.seed(42)
	run_incorrect()
	run_correct()
	run_stress_tests()
