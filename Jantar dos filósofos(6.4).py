import threading
import time


# ==============================================================
# Jantar dos filosofos (6.4)
# - Versao incorreta: deadlock garantido (todos destros)
# - Versao correta: prevencao por hierarquia de recursos
# ==============================================================

PHILOSOPHERS = 5


def make_forks(n):
	"""Create N forks as threading.Lock objects."""
	return [threading.Lock() for _ in range(n)]


def philosopher_deadlock(
	idx,
	forks,
	start_barrier,
	left_barrier,
	delay_between,
	think_time=0.1,
):
	"""
	Deadlock version: all philosophers pick left then right.
	A forced delay between forks makes the deadlock visible.
	"""
	left = forks[idx]
	right = forks[(idx + 1) % len(forks)]
	name = f"F{idx}"

	start_barrier.wait()
	time.sleep(think_time)

	print(f"{name} trying LEFT fork {idx}")
	left.acquire()
	print(f"{name} got LEFT fork {idx}")

	# Ensure everyone holds their left fork before attempting the right one.
	left_barrier.wait()

	# Forced delay to guarantee the deadlock window.
	time.sleep(delay_between)

	print(f"{name} trying RIGHT fork {(idx + 1) % len(forks)}")
	right.acquire()
	# This point is never reached in the deadlock scenario.
	print(f"{name} got RIGHT fork {(idx + 1) % len(forks)}")
	right.release()
	left.release()


def run_deadlock_demo(n=PHILOSOPHERS, demo_timeout=6, delay_between=0.3):
	"""Run the incorrect version and let it deadlock visibly."""
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
	"""Safe version: always pick the lower-ID fork first (resource hierarchy)."""
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
	"""Run the corrected version for a fixed time window."""
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


# ==============================================================
# Coffman conditions (deadlock necessities) and the fix used
#
# 1) Mutual exclusion: at least one resource is non-shareable.
# 2) Hold and wait: a process holds one resource while waiting for another.
# 3) No preemption: resources are released only voluntarily.
# 4) Circular wait: a cycle exists where each process waits for a resource
#    held by the next process in the cycle.
#
# In the corrected version we BREAK the circular wait condition by imposing
# a strict resource hierarchy: every philosopher always acquires the lower-ID
# fork first, then the higher-ID fork. With a total order, a cycle cannot form.
# ==============================================================


def main():
	try:
		run_deadlock_demo()
	except KeyboardInterrupt:
		print("\n[Deadlock demo] Interrupted by user. Moving to corrected version.\n")

	run_correct_demo()
	print("\n[Correct demo] Finished without deadlock.")


if __name__ == "__main__":
	main()
