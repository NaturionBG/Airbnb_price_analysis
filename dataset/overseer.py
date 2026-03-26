import pandas as pd
import subprocess
import sys
import time
import os
import json

INITIAL_URLS_FILE = "all_urls.json"   
OUTPUT_FILE = "data.jl"              
TIMEOUT = 300
TEMP_URLS_FILE = "current_urls.json"                    


def load_initial_urls(frame: pd.DataFrame) -> set:
  return set(frame.url.values.tolist())
all_urls = pd.read_json('urls.json')


def write_current_urls(urls_set):
    with open(TEMP_URLS_FILE, 'w') as f:
        json.dump(list(urls_set), f, indent=2)
    
class OverSeer:
  def __init__(self, timeout: int):
    self.timeout = timeout
    self.remaining = load_initial_urls(all_urls)
    
  def get_scraped_urls(self) -> set:
    if not os.path.exists(OUTPUT_FILE):
        return set()
    temp = pd.read_json(OUTPUT_FILE, lines=True)
    return set(temp['url'].dropna().unique())
  
  def kill_process(self, proc) -> None:
    try:
        proc.terminate()
        time.sleep(2)
        if proc.poll() is None:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
    except Exception:
        pass
  def run(self):
    while self.remaining:
      write_current_urls(self.remaining)

      cmd = [
          sys.executable, "-m", "scrapy", "crawl", "airbnb",
          "-o", OUTPUT_FILE,
      ]
      print(f"\nRemaining: {len(self.remaining)}. Starting spider...")
      proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

      try:
          stdout, _ = proc.communicate(timeout=self.timeout)
          print(stdout)
      except subprocess.TimeoutExpired:
          print(f"Spider timed out after {self.timeout} seconds. Killing...")
          self.kill_process(proc)

      scraped = self.get_scraped_urls()
      self.remaining -= scraped
      print(f"Scraped in total: {len(scraped)}. Remaining now: {len(self.remaining)}")
      time.sleep(10)

    print("All URLs scraped!")

overseer = OverSeer(TIMEOUT)
overseer.run()