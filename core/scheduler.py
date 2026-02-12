import schedule
import time
import threading

class Scheduler:
    def __init__(self):
        self.running = False

    def add_job(self, time_str: str, job_func, *args, **kwargs):
        """Add a daily job at specific time."""
        schedule.every().day.at(time_str).do(job_func, *args, **kwargs)

    def add_interval_job(self, minutes: int, job_func, *args, **kwargs):
        """Add a job that runs every X minutes."""
        schedule.every(minutes).minutes.do(job_func, *args, **kwargs)

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        print("Scheduler started.")

    def _run(self):
        while self.running:
            schedule.run_pending()
            time.sleep(1)

    def stop(self):
        self.running = False
