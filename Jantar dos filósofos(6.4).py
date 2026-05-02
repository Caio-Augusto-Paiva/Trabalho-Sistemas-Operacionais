import threading
import time

PHILOSOPHERS = 5
FORCE_YIELD = 0.00001

STRESS_PHILOSOPHERS = 12
STRESS_DEADLOCK_WAIT = 1.5
STRESS_RUN_TIME = 4


def make_forks(n):
	return [threading.Lock() for _ in range(n)]


def philosopher_deadlock(
	idx,
	forks,
	start_barrier,
	left_barrier,
	delay_between,
	think_time=0.1,
):
	left = forks[idx]
	right = forks[(idx + 1) % len(forks)]
	name = f"F{idx}"

	start_barrier.wait()
	time.sleep(think_time)

	print(f"{name} trying LEFT fork {idx}")
	left.acquire()
	print(f"{name} got LEFT fork {idx}")
	time.sleep(FORCE_YIELD)
	left_barrier.wait()
	time.sleep(delay_between)

	print(f"{name} trying RIGHT fork {(idx + 1) % len(forks)}")
	right.acquire()
	print(f"{name} got RIGHT fork {(idx + 1) % len(forks)}")
	right.release()
	left.release()


def run_deadlock_demo(n=PHILOSOPHERS, demo_timeout=6, delay_between=0.3):
	forks = make_forks(n)
	start_barrier = threading.Barrier(n)
	left_barrier = threading.Barrier(n)

	threads = []
	for idx in range(n):
		t = threading.Thread(
			target=philosopher_deadlock,
			args=(idx, forks, start_barrier, left_barrier, delay_between),
			daemon=True,
		)
		threads.append(t)
		t.start()

	print("\n[Deadlock demo] All philosophers are right-handed.")
	print("[Deadlock demo] Output should stop once every left fork is held.")
	time.sleep(demo_timeout)
	print("[Deadlock demo] Timeout reached. Moving to the corrected version.\n")


def philosopher_ordered(
	idx,
	forks,
	stop_event,
	think_time=0.2,
	eat_time=0.2,
):
	left_id = idx
	right_id = (idx + 1) % len(forks)
	first_id, second_id = (left_id, right_id) if left_id < right_id else (right_id, left_id)
	first = forks[first_id]
	second = forks[second_id]
	name = f"F{idx}"

	while not stop_event.is_set():
		print(f"{name} thinking")
		time.sleep(think_time)

		print(f"{name} trying forks {first_id} -> {second_id}")
		with first:
			with second:
				print(f"{name} eating")
				time.sleep(eat_time)


def run_correct_demo(n=PHILOSOPHERS, run_time=6):
	forks = make_forks(n)
	stop_event = threading.Event()
	threads = []

	for idx in range(n):
		t = threading.Thread(target=philosopher_ordered, args=(idx, forks, stop_event))
		threads.append(t)
		t.start()

	time.sleep(run_time)
	stop_event.set()
	for t in threads:
		t.join(timeout=1)

	return sum(1 for t in threads if t.is_alive())


def run_deadlock_stress(n=STRESS_PHILOSOPHERS, delay_between=0.05) -> int:
	forks = make_forks(n)
	start_barrier = threading.Barrier(n)
	left_barrier = threading.Barrier(n)

	threads = []
	for idx in range(n):
		t = threading.Thread(
			target=philosopher_deadlock,
			args=(idx, forks, start_barrier, left_barrier, delay_between, 0.01),
			daemon=True,
		)
		threads.append(t)
		t.start()

	time.sleep(STRESS_DEADLOCK_WAIT)
	return sum(1 for t in threads if t.is_alive())


def run_stress_tests() -> None:
	print("\n=== Teste de estresse (6.4) ===")
	stuck = run_deadlock_stress()
	print("[ESTRESSE] incorreto - filosofos bloqueados:", stuck)
	assert stuck >= STRESS_PHILOSOPHERS

	alive = run_correct_demo(n=STRESS_PHILOSOPHERS, run_time=STRESS_RUN_TIME)
	print("[ESTRESSE] correto - threads ainda vivas:", alive)
	assert alive == 0

def main():
	try:
		run_deadlock_demo()
	except KeyboardInterrupt:
		print("\n[Deadlock demo] Interrupted by user. Moving to corrected version.\n")

	run_correct_demo()
	print("\n[Correct demo] Finished without deadlock.")
	run_stress_tests()


if __name__ == "__main__":
	main()
