import threading
import time
import random


# ------------------------------
# Versao incorreta (sem exclusao mutua)
# ------------------------------
unsafe_current_direction = None
unsafe_cars_on_bridge = 0


def unsafe_cross_bridge(car_id, direction):
	global unsafe_current_direction, unsafe_cars_on_bridge

	time.sleep(random.uniform(0.01, 0.08))
	print(f"[INC] carro {car_id} chegando da direcao {direction}")

	# Sem exclusao mutua: dois sentidos podem entrar ao mesmo tempo.
	if unsafe_cars_on_bridge > 0 and unsafe_current_direction != direction:
		print(
			f"[INC] COLISAO detectada: carro {car_id} na direcao {direction} "
			f"entrou enquanto havia carros na direcao {unsafe_current_direction}"
		)

	if unsafe_cars_on_bridge == 0:
		unsafe_current_direction = direction

	unsafe_cars_on_bridge += 1
	print(f"[INC] carro {car_id} atravessando na direcao {direction}")
	time.sleep(random.uniform(0.05, 0.15))
	unsafe_cars_on_bridge -= 1
	print(f"[INC] carro {car_id} saindo da ponte")

	if unsafe_cars_on_bridge == 0:
		unsafe_current_direction = None


def run_incorrect_simulation():
	print("\n=== Versao Incorreta (sem exclusao mutua) ===")
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


# ------------------------------
# Versao corrigida (com prevencao de inatencao/starvation)
# ------------------------------
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


def safe_cross_bridge(car_id, direction):
	global current_direction, turn_direction, cars_on_bridge, passed_in_turn

	time.sleep(random.uniform(0.01, 0.08))
	print(f"[OK ] carro {car_id} chegando da direcao {direction}")

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
	threads = []
	cars = []

	# Fluxo propositalmente desequilibrado para forcar alternancia.
	for i in range(1, 21):
		cars.append((i, "N"))
	for i in range(21, 24):
		cars.append((i, "S"))

	random.shuffle(cars)

	for car_id, direction in cars:
		t = threading.Thread(target=safe_cross_bridge, args=(car_id, direction))
		t.start()
		threads.append(t)
		time.sleep(0.01)

	for t in threads:
		t.join()


def main():
	random.seed(42)
	run_incorrect_simulation()
	run_correct_simulation()


if __name__ == "__main__":
	main()


# Justificativa tecnica:
# A condicao (Condition) protege as variaveis compartilhadas e bloqueia
# a entrada de carros de direcoes opostas enquanto ha carros na ponte.
# Para evitar starvation, contamos quantos carros atravessam em cada turno
# (MAX_CARS_PER_TURN). Se o limite e atingido e ha carros aguardando no
# outro sentido, o fluxo e alternado assim que a ponte fica vazia, garantindo
# que ambos os lados avancem mesmo com chegada continua de um unico sentido.
