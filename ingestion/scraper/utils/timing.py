import random
#Creating a more human like delay since not using rotating proxies
def human_delay(base_delay: float) -> float:
    factor = random.uniform(0.7, 1.6)
    delay = max(8, base_delay * factor)

    if random.random() < 0.07:
        delay += random.uniform(20, 60)

    return delay

