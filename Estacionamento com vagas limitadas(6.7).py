import threading
import time
import random


SPOTS = 5
TOTAL_CARS = 20
ARRIVAL_MIN = 0.0
ARRIVAL_MAX = 0.05
PARK_MIN = 0.02
PARK_MAX = 0.08

FORCE_YIELD = 0.00001

STRESS_CARS = 80
STRESS_SPOTS = 10
STRESS_ARRIVAL_MIN = 0.0
STRESS_ARRIVAL_MAX = 0.001
STRESS_PARK_MIN = 0.001
STRESS_PARK_MAX = 0.003


def run_incorrect(
	*,
	spots: int = SPOTS,
	total_cars: int = TOTAL_CARS,
	arrival_min: float = ARRIVAL_MIN,
	arrival_max: float = ARRIVAL_MAX,
	park_min: float = PARK_MIN,
	park_max: float = PARK_MAX,
	start_barrier: threading.Barrier | None = None,
) -> dict:
	print("=== VERSAO INCORRETA (sem exclusao mutua) ===")
	occupied = 0
	max_occupied = 0
	errors = {"over_capacity": 0, "negative": 0}
	errors_lock = threading.Lock()

	def car(cid: int) -> None:
		nonlocal occupied, max_occupied
		time.sleep(random.uniform(arrival_min, arrival_max))
		if start_barrier is not None:
			start_barrier.wait()

		if occupied >= spots:
			time.sleep(FORCE_YIELD)
			if occupied >= spots:
				print(f"[INCORRETO] Carro {cid} foi embora (sem vaga)")
				return

		time.sleep(FORCE_YIELD)
		occupied += 1
		max_occupied = max(max_occupied, occupied)
		if occupied > spots:
			with errors_lock:
				errors["over_capacity"] += 1
			print(
				f"[INCORRETO] ERRO: ocupacao {occupied} > {spots}"
			)

		time.sleep(random.uniform(park_min, park_max))
		time.sleep(FORCE_YIELD)
		occupied -= 1
		if occupied < 0:
			with errors_lock:
				errors["negative"] += 1
			print("[INCORRETO] ERRO: ocupacao negativa")
			occupied = 0

	threads = []
	for cid in range(1, total_cars + 1):
		thread = threading.Thread(target=car, args=(cid,))
		threads.append(thread)
		thread.start()

	for thread in threads:
		thread.join()

	print("=== FIM DA VERSAO INCORRETA ===\n")
	return {
		"max_occupied": max_occupied,
		"over_capacity": errors["over_capacity"],
		"negative": errors["negative"],
	}


def run_correct(
	*,
	spots: int = SPOTS,
	total_cars: int = TOTAL_CARS,
	arrival_min: float = ARRIVAL_MIN,
	arrival_max: float = ARRIVAL_MAX,
	park_min: float = PARK_MIN,
	park_max: float = PARK_MAX,
	start_barrier: threading.Barrier | None = None,
) -> dict:
	print("=== VERSAO CORRETA (semaforo + mutex) ===")
	occupied = 0
	max_occupied = 0
	spots_sem = threading.Semaphore(spots)
	mutex = threading.Lock()

	def car(cid: int) -> None:
		nonlocal occupied, max_occupied
		time.sleep(random.uniform(arrival_min, arrival_max))
		if start_barrier is not None:
			start_barrier.wait()

		spots_sem.acquire()
		with mutex:
			occupied += 1
			max_occupied = max(max_occupied, occupied)
			assert occupied <= spots

		time.sleep(random.uniform(park_min, park_max))

		with mutex:
			occupied -= 1
			assert occupied >= 0
		spots_sem.release()

	threads = []
	for cid in range(1, total_cars + 1):
		thread = threading.Thread(target=car, args=(cid,))
		threads.append(thread)
		thread.start()

	for thread in threads:
		thread.join()

	print("=== FIM DA VERSAO CORRETA ===")
	return {"max_occupied": max_occupied}


def run_stress_tests() -> None:
	print("\n=== Teste de estresse (6.7) ===")
	barrier = threading.Barrier(STRESS_CARS + 1)
	bad = run_incorrect(
		spots=STRESS_SPOTS,
		total_cars=STRESS_CARS,
		arrival_min=STRESS_ARRIVAL_MIN,
		arrival_max=STRESS_ARRIVAL_MAX,
		park_min=STRESS_PARK_MIN,
		park_max=STRESS_PARK_MAX,
		start_barrier=barrier,
	)
	print(
		"[ESTRESSE] incorreto - over_capacity:",
		bad["over_capacity"],
		"negative:",
		bad["negative"],
	)
	assert bad["over_capacity"] > 0 or bad["negative"] > 0

	barrier = threading.Barrier(STRESS_CARS + 1)
	good = run_correct(
		spots=STRESS_SPOTS,
		total_cars=STRESS_CARS,
		arrival_min=STRESS_ARRIVAL_MIN,
		arrival_max=STRESS_ARRIVAL_MAX,
		park_min=STRESS_PARK_MIN,
		park_max=STRESS_PARK_MAX,
		start_barrier=barrier,
	)
	print("[ESTRESSE] correto - max_occupied:", good["max_occupied"])
	assert good["max_occupied"] <= STRESS_SPOTS


def main() -> None:
	random.seed(42)
	run_incorrect()
	run_correct()
	run_stress_tests()


if __name__ == "__main__":
	main()
