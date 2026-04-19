"""Mock gov"""

import contextlib
import io
import json
import logging
import re
import socket
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver  # linter
from selenium.webdriver.support import expected_conditions as ec
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


@measure
def click_hide_nav_bar(driver: WebDriver) -> None:
    """
    Remove the left side bar so that the graphs take up more space in the
    screen. Reduce clutter in the final screenshot; WebDriverWait is safer as
    it waits for the icon to be clicable.

    """
    # wait up to 10 seconds for the nav link to be clickable
    menu_link = WebDriverWait(driver, 10).until(
        ec.element_to_be_clickable(
            (By.CSS_SELECTOR, "a.nav-item.nav-link.px-0.mr-4.cursor-pointer")
        )
    )

    menu_link.click()
    time.sleep(2)


@measure
def main() -> dict:
    """Logical entry point."""
    chrome_path = Path(r"C:\Tools\chrome\chrome.exe")
    driver_path = Path(r"C:\Tools\chromedriver\chromedriver.exe")

    if not chrome_path.is_file():
        raise FileNotFoundError(f"Chrome not found at: {chrome_path}")

    if not driver_path.is_file():
        raise FileNotFoundError(f"Chromedriver not found at: {driver_path}")

    options = Options()
    options.debugger_address = "127.0.0.1:9222"
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.binary_location = str(chrome_path)  # TODO: check if needed

    service = Service(driver_path)

    # NOTE: First check sockets, then instantiate driver
    if socket.socket().connect_ex(("127.0.0.1", 9222)) != 0:
        print(f"[ERROR]: Chrome debug is not listening on 127.0.0.1: 9222")
        print(f"[INFO]: Usage: 'chrome --remote-debugging-port=9222'")
        return {}

    driver = webdriver.Chrome(service=service, options=options)
    print(driver.title)
    return {}


def execute() -> dict:
    """SF entry point."""
    return log(main)


if __name__ == "__main__":
    """Dev entry point. Does not affect deployment."""
    state = execute()
    state["logs"] = state["logs"].replace("\\n", "\n")
    print(state.pop("logs"))
    print(json.dumps(state, indent=2))
