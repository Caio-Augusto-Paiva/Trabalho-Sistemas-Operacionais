import threading
import time
import random

unsafe_current_direction = None
unsafe_cars_on_bridge = 0

FORCE_YIELD = 0.00001

STRESS_MAIN_CARS = 50
STRESS_OTHER_CARS = 2
STRESS_ARRIVAL_MAX = 0.002


def unsafe_cross_bridge(car_id, direction):
	global unsafe_current_direction, unsafe_cars_on_bridge

	time.sleep(random.uniform(0.01, 0.08))
	print(f"[INC] carro {car_id} chegando da direcao {direction}")
	if unsafe_cars_on_bridge > 0 and unsafe_current_direction != direction:
		print(
			f"[INC] COLISAO detectada: carro {car_id} na direcao {direction} "
			f"entrou enquanto havia carros na direcao {unsafe_current_direction}"
		)

	time.sleep(FORCE_YIELD)
	if unsafe_cars_on_bridge == 0:
		unsafe_current_direction = direction

	time.sleep(FORCE_YIELD)
	unsafe_cars_on_bridge += 1
	print(f"[INC] carro {car_id} atravessando na direcao {direction}")
	time.sleep(random.uniform(0.05, 0.15))
	time.sleep(FORCE_YIELD)
	unsafe_cars_on_bridge -= 1
	print(f"[INC] carro {car_id} saindo da ponte")

	if unsafe_cars_on_bridge == 0:
		unsafe_current_direction = None


def run_incorrect_simulation():
	print("\n=== Versao Incorreta (sem exclusao mutua) ===")
	reset_unsafe_state()
	threads = []
	cars = [(i, "N") for i in range(1, 7)] + [(i + 6, "S") for i in range(1, 7)]
	random.shuffle(cars)

	for car_id, direction in cars:
		t = threading.Thread(target=unsafe_cross_bridge, args=(car_id, direction))
		t.start()
		threads.append(t)
		time.sleep(0.01)

	for t in threads:
		t.join()
MAX_CARS_PER_TURN = 4
bridge_lock = threading.Lock()
bridge_condition = threading.Condition(bridge_lock)
current_direction = None
turn_direction = None
cars_on_bridge = 0
passed_in_turn = 0
waiting = {"N": 0, "S": 0}


def other_direction(direction):
	return "S" if direction == "N" else "N"


def reset_unsafe_state() -> None:
	global unsafe_current_direction, unsafe_cars_on_bridge
	unsafe_current_direction = None
	unsafe_cars_on_bridge = 0


def reset_safe_state() -> None:
	global bridge_lock, bridge_condition, current_direction, turn_direction
	global cars_on_bridge, passed_in_turn, waiting
	bridge_lock = threading.Lock()
	bridge_condition = threading.Condition(bridge_lock)
	current_direction = None
	turn_direction = None
	cars_on_bridge = 0
	passed_in_turn = 0
	waiting = {"N": 0, "S": 0}


def safe_cross_bridge(car_id, direction, stats: dict | None = None):
	global current_direction, turn_direction, cars_on_bridge, passed_in_turn

	time.sleep(random.uniform(0.01, 0.08))
	print(f"[OK ] carro {car_id} chegando da direcao {direction}")
	arrival = time.perf_counter()

	waiting_logged = False
	with bridge_condition:
		waiting[direction] += 1
		while True:
			other = other_direction(direction)

			if cars_on_bridge == 0:
				if turn_direction is None:
					turn_direction = direction

				if turn_direction == direction:
					break

				if waiting[turn_direction] == 0:
					turn_direction = direction
					break
			else:
				if current_direction == direction:
					if passed_in_turn < MAX_CARS_PER_TURN or waiting[other] == 0:
						break

			if not waiting_logged:
				blocking_direction = (
					current_direction
					if current_direction is not None
					else turn_direction
				)
				print(
					f"[OK ] carro {car_id} aguardando; ponte no sentido {blocking_direction}"
				)
				waiting_logged = True

			bridge_condition.wait()

		waiting[direction] -= 1

		if cars_on_bridge == 0:
			current_direction = direction
			passed_in_turn = 0

		cars_on_bridge += 1
		passed_in_turn += 1
		if stats is not None:
			wait_time = time.perf_counter() - arrival
			stats["waits"][direction].append(wait_time)
			stats["crossed"][direction] += 1
		print(f"[OK ] carro {car_id} atravessando na direcao {direction}")

	time.sleep(random.uniform(0.06, 0.18))

	with bridge_condition:
		cars_on_bridge -= 1
		print(f"[OK ] carro {car_id} saindo da ponte")

		if cars_on_bridge == 0:
			other = other_direction(direction)
			switch_to_other = False

			if waiting[other] > 0 and passed_in_turn >= MAX_CARS_PER_TURN:
				switch_to_other = True
			elif waiting[other] > 0 and waiting[direction] == 0:
				switch_to_other = True

			if switch_to_other:
				turn_direction = other
				print(
					f"[OK ] alternancia de fluxo: agora sentido {turn_direction}"
				)
			elif waiting[direction] > 0:
				turn_direction = direction
			else:
				turn_direction = None

			current_direction = None
			passed_in_turn = 0

		bridge_condition.notify_all()


def run_correct_simulation():
	print("\n=== Versao Corrigida (com prevencao de starvation) ===")
	reset_safe_state()
	threads = []
	cars = []
	for i in range(1, 9):
		cars.append((i, "N"))
	for i in range(9, 13):
		cars.append((i, "S"))

	random.shuffle(cars)

	for car_id, direction in cars:
		t = threading.Thread(target=safe_cross_bridge, args=(car_id, direction))
		t.start()
		threads.append(t)
		time.sleep(0.01)

	for t in threads:
		t.join()


def run_stress_tests() -> None:
	print("\n=== Teste de estresse (6.6) ===")
	reset_safe_state()
	stats = {"waits": {"N": [], "S": []}, "crossed": {"N": 0, "S": 0}}
	threads = []
	cars = []

	for i in range(1, STRESS_MAIN_CARS + 1):
		cars.append((i, "N"))
	for i in range(STRESS_MAIN_CARS + 1, STRESS_MAIN_CARS + STRESS_OTHER_CARS + 1):
		cars.append((i, "S"))

	random.shuffle(cars)

	for car_id, direction in cars:
		t = threading.Thread(target=safe_cross_bridge, args=(car_id, direction, stats))
		t.start()
		threads.append(t)
		time.sleep(random.uniform(0.0, STRESS_ARRIVAL_MAX))

	for t in threads:
		t.join()

	max_wait_n = max(stats["waits"]["N"]) if stats["waits"]["N"] else 0.0
	max_wait_s = max(stats["waits"]["S"]) if stats["waits"]["S"] else 0.0

	print(
		"[ESTRESSE] cruzaram N:",
		stats["crossed"]["N"],
		"S:",
		stats["crossed"]["S"],
	)
	print(
		"[ESTRESSE] max_espera N:",
		f"{max_wait_n:.6f}",
		"S:",
		f"{max_wait_s:.6f}",
	)
	assert stats["crossed"]["N"] == STRESS_MAIN_CARS
	assert stats["crossed"]["S"] == STRESS_OTHER_CARS


def main():
	random.seed(42)
	run_incorrect_simulation()
	run_correct_simulation()
	run_stress_tests()


if __name__ == "__main__":
	main()
