"""Mock gov"""

import contextlib
import io
import json
import logging
import random
import re
import socket
import sys
import time
import tomllib
import traceback
from pathlib import Path
from typing import Any, Callable, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def measure(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator: wraps a function to print its execution time in seconds."""

    def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"[INFO]: {func.__name__} took {execution_time:.2f}s")
        return result

    return wrapper


@contextlib.contextmanager
def redirect_logs(stream: Optional[io.StringIO] = None):
    """Redirect logs to stream"""
    i = stream or io.StringIO()

    _rstdout = sys.stdout
    _rstderr = sys.stderr

    sys.stdout = i
    sys.stderr = i
    yield i

    sys.stdout = _rstdout
    sys.stderr = _rstderr
    i.seek(0)


def log(main: Callable[[], dict]) -> dict:
    """Wraps main by appending logs to its response dictionary."""
    stream = io.StringIO()
    format = "[%(levelname)s]: %(message)s"
    with redirect_logs(stream):
        try:
            logging.basicConfig(stream=stream, format=format)
            logging.root.setLevel(logging.INFO)
            result = main()
            stream.seek(0)
            logs = stream.read()
            logs = re.sub(r"api_token=.{50}", "token=xxx", logs)
            return {**result, "logs": logs[-64000:]}
        except Exception:
            stream.seek(0)
            logs = stream.read() + "\n" + traceback.format_exc()
            logs = re.sub(r"api_token=.{50}", "token=xxx", logs)
            return {"logs": logs[-64000:]}


def click_play_button(driver) -> None:
    # re-find and switch to iframe every time
    iframe = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.TAG_NAME, "iframe"))
    )
    driver.switch_to.frame(iframe)

    btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (
                By.CSS_SELECTOR,
                "button.play-controls-container__play-pause-button",
            )
        )
    )
    btn.click()


def emit_curr_total(driver) -> None:
    """Emit current and total pages."""
    width = 30
    label = driver.find_element(
        By.CSS_SELECTOR, "div.navigation-controls__label"
    )
    current, total = map(int, label.text.split(" of "))
    # Custom progress bar
    filled = int(width * current / total)
    bar = "#" * filled + "-" * (width - filled)
    print(f"\r[{bar}] {current}/{total}", end="", flush=True)


def load_settings() -> dict:
    """Load config from settings.toml. Assumed in the same dir as the .exe."""
    with open("settings.toml", "rb") as f:
        return tomllib.load(f)


def wait_with_spinner(
    seconds: float, current: int, total: int, elapsed: int
) -> None:
    """Waiting spinner that does not override the progress bar."""
    width = 30

    for i in range(int(seconds)):
        filled = int(width * current / total)
        bar = "#" * filled + "-" * (width - filled)
        spinner = "|/-\\"[i % 4]

        total_elapsed = elapsed + i
        mins = total_elapsed // 60
        secs = total_elapsed % 60

        # NOTE: The space after s is needed for proper flushing
        print(
            f"\r[{bar}] {current}/{total} {spinner} {i}s | elapsed: {mins:02}:{secs:02} ",
            end="",
            flush=True,
        )
        time.sleep(1)


def _get_current(driver) -> int:
    """Live fetch current slide from driver."""
    label = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "div.navigation-controls__label")
        )
    )

    current, _ = map(int, label.text.split(" of "))
    return current


@measure
def main() -> dict:
    """Logical entry point."""
    try:
        settings = load_settings()
    except FileNotFoundError:
        print(f"[ERROR]: The settings.toml must be in the same dir at the exe")
        return {}
    chrome_path = Path(settings.get("chrome_path", ""))
    driver_path = Path(settings.get("driver_path", ""))

    if not chrome_path.is_file():
        print(f"[ERROR]: chrome.exe not found at {chrome_path}")
        return {}

    if not driver_path.is_file():
        print(f"[ERROR]: chromedriver not found at {driver_path}")

    print(f"[DEBUG]: Found chrome in {chrome_path}")
    print(f"[DEBUG]: Found chromedriver in {driver_path}")

    options = Options()
    options.debugger_address = "127.0.0.1:9222"
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.binary_location = str(chrome_path)  # TODO: check if needed

    service = Service(driver_path)

    # NOTE: First check socket & then instantiate driver
    if socket.socket().connect_ex(("127.0.0.1", 9222)) != 0:
        print(f"[ERROR]: chrome is not listening on 127.0.0.1:9222")
        print(f"[INFO]: Usage: 'chrome --remote-debugging-port=9222'")
        return {}

    driver = webdriver.Chrome(service=service, options=options)
    print(f"[INFO]: {driver.title}")

    # wait for iframe
    iframe = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.TAG_NAME, "iframe"))
    )
    driver.switch_to.frame(iframe)
    label = driver.find_element(
        By.CSS_SELECTOR, "div.navigation-controls__label"
    )

    current, total = map(int, label.text.split(" of "))
    print(f"[INFO]: Selenium started on current: {current}")
    print(f"[INFO]: Selenium started on total: {total}")

    min_sec = settings.get("min_sec", 30)
    max_sec = settings.get("max_sec", 50)

    time_limit_mins = settings.get("time_limit_mins", 40)
    time_limit_s = time_limit_mins * 60
    start_time = time.time()
    print(f"[INFO]: Slide uniformly in range ({min_sec}s,{max_sec}s)")

    while current < total:
        if time.time() - start_time >= time_limit_s:
            print("\n[INFO]: Time limit reached, stopping loop.")
            break
        # play slide
        # click_play_button(driver=driver)
        driver.switch_to.default_content()  # ensure correct context
        body = driver.find_element(By.TAG_NAME, "body")
        body.click()  # <-- give focus to page
        body.send_keys(Keys.ARROW_RIGHT)
        body.send_keys(Keys.ARROW_RIGHT)

        # spinner
        wait_time = random.triangular(min_sec, max_sec, max_sec)
        elapsed = int(time.time() - start_time)
        wait_with_spinner(wait_time, current + 1, total, elapsed)

        # incr
        current += 1

    return {}


def execute() -> dict:
    """SF entry point."""
    return main()


if __name__ == "__main__":
    """Dev entry point. Does not affect deployment."""
    state = execute()
    print(json.dumps(state, indent=2))
    input("\nPress Enter to exit...")
    # state["logs"] = state["logs"].replace("\\n", "\n")
    # print(state.pop("logs"))
    # print(json.dumps(state, indent=2))
