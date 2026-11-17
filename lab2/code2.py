import hashlib
import itertools
import time
import multiprocessing
import queue
import sys

ALPHABET = 'abcdefghijklmnopqrstuvwxyz'
PASSWORD_LENGTH = 5

def calculate_md5(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def calculate_sha256(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def check_password(password, hash_value, hash_type):
    if hash_type == 'md5':
        return calculate_md5(password) == hash_value
    elif hash_type == 'sha256':
        return calculate_sha256(password) == hash_value
    else:
        return False

def get_hash_type(hash_value):
    if len(hash_value) == 32:
        return 'md5'
    elif len(hash_value) == 64:
        return 'sha256'
    else:
        return None

def single_process_search(hash_value, result_queue):
    start_time = time.time()
    hash_type = get_hash_type(hash_value)
    if not hash_type:
        print(f"Неизвестный тип хэша: {hash_value} (неправильная длина)")
        result_queue.put((None, time.time() - start_time))
        return

    for p_tuple in itertools.product(ALPHABET, repeat=PASSWORD_LENGTH):
        password = ''.join(p_tuple)
        if check_password(password, hash_value, hash_type):
            elapsed_time = time.time() - start_time
            result_queue.put((password, elapsed_time))
            return

    elapsed_time = time.time() - start_time
    result_queue.put((None, elapsed_time))

def worker_task(args):
    hash_value, hash_type, start_time = args
    for p_tuple in itertools.product(ALPHABET, repeat=PASSWORD_LENGTH):
        password = ''.join(p_tuple)
        if check_password(password, hash_value, hash_type):
            return (password, time.time() - start_time)
    return (None, time.time() - start_time)

def multi_process_search(hash_value, num_processes):
    start_time = time.time()
    hash_type = get_hash_type(hash_value)
    if not hash_type:
        print(f"Неизвестный тип хэша: {hash_value} (неправильная длина)")
        return (None, time.time() - start_time)

    with multiprocessing.Pool(processes=num_processes) as pool:
        tasks = [(hash_value, hash_type, start_time)] * num_processes
        results = pool.map(worker_task, tasks)

    for result, elapsed_time in results:
        if result:
            return (result, elapsed_time)

    return (None, time.time() - start_time)

def main():
    print("Введите хэш значения(или Enter дважды):")
    hashes = []
    while True:
        user_input = input().strip()
        if user_input == "":
            if hashes:
                break
            else:
                continue
        else:
            hashes.append(user_input)

    if not hashes:
        hashes = [
            "1115dd800feaacefdf481f1f9070374a2a81e27880f187396db67958b207cbad",
            "3a7bd3e2360a3d29eea436fcfb7e44c735d117c42d1c1835420b6b9942dd4f1b",
            "74e1bb62f8dabb8125a58852b63bdf6eaef667cb56ac7f7cdba6d7305c50a22f",
            "7a68f09bd992671bb3b19a5e70b7827e"
        ]
        print("Используются хэши из задания.")

    print("\nВыберите режим:")
    print("1. Однопроцессорный")
    print("2. Многопроцессорный")
    mode_choice = input("Введите 1 или 2: ").strip()

    num_processes = None
    if mode_choice == "2":
        try:
            num_processes = int(input("Введите количество процессов: "))
            if num_processes <= 0:
                raise ValueError
        except ValueError:
            print("Некорректное количество процессов")
            num_processes = 4

    for hash_val in hashes:
        print(f"\nПоиск для хэша: {hash_val}")
        hash_type = get_hash_type(hash_val)
        if not hash_type:
            print(f"Пропущен неизвестный тип хэша: {hash_val}")
            continue

        if mode_choice == "1":
            print("Запуск однопроцессорного поиска...")
            result_q = multiprocessing.Queue()
            single_process_search(hash_val, result_q)
            result, elapsed_time = result_q.get()
            if result:
                print(f"Найден пароль: {result}")
                print(f"Время поиска: {elapsed_time:.4f} секунд")
            else:
                print("Пароль не найден.")
                print(f"Время поиска: {elapsed_time:.4f} секунд")

        elif mode_choice == "2":
            print(f"Запуск многопроцессорного поиска ({num_processes} процессов)")
            result, elapsed_time = multi_process_search(hash_val, num_processes)
            if result:
                print(f"Найден пароль: {result}")
                print(f"Время поиска: {elapsed_time:.4f} секунд")
            else:
                print("Пароль не найден.")
                print(f"Время поиска: {elapsed_time:.4f} секунд")
        else:
            print("Неверный выбор режима.")
            return

if __name__ == "__main__":
    main()