from os import cpu_count
from .types import *
import tqdm
import zono.events
import traceback
import sys
import warnings
import threading
import multiprocessing

class Workload:
    def __init__(
        self,
        threads:int=-1,
        daemon:bool=False,
        ordered_return:bool=True,
        worker_type=Thread,
    ):
        if threads==-1:
            threads = cpu_count()

        else:
            if not isinstance(threads, int):
                raise ValueError("Threads must be an integer")

            if threads <= 0:
                raise ValueError("Threads cannot be less that zero")

        self.threads = threads
        self.results_dict = {}
        self.currently_running = []
        self.daemon = daemon
        self.run_queue = []
        self.results = []
        self.ordered_return = ordered_return
        self.stopped = False
        self.worker_type = worker_type
        self.started = False
        self.results_lock = threading.RLock()
        zono.events.attach(self)
        self.register_event("thread_error", self.thread_error)

    def thread_error(self, inp, error, exc_info):
        traceback.print_exception(exc_info[0], exc_info[1], exc_info[2])
        print(error)
        print(f"\nthis error while running function for the value: {inp}")

    def stop(self):
        self.stopped = True
        for i in self.currently_running:
            try:
                i.join()
            except RuntimeError:
                pass
            if i in self.currently_running:
                self.currently_running.remove(i)
            del i

    def chunks(self, l, n):
        return [l[i : i + n] for i in range(0, len(l), n)]

    def _runner_(self, func, arg, *args):
        try:
            ret = func(arg, *args)
        except Exception as e:
            self.run_event("thread_error", arg, e, sys.exc_info())

        with self.results_lock:
            if self.ordered_return:
                self.results_dict[arg] = ret
            else:
                self.results.append(ret)

        self.run_event("thread_complete", arg, ret)

    def terminate(self):
        self.stopped = True
        for i in self.currently_running:
            i.terminate()

    def __soft_parse_returns(self):
        if not self.ordered_return:
            return self.results
        else:
            results = []
            for i in self.lst:
                if i in self.results_dict:
                    results.append(self.results_dict[i])

            return results

    def run(self, lst, callback, *args):
        self.results.clear()
        self.stopped = False
        self.results_dict.clear()
        self.run_queue.clear()
        self.currently_running.clear()
        self.lst = lst
        lst = list(lst)

        if self.ordered_return:
            if len(lst) != len(set(lst)):
                raise ValueError(
                    "All inputed elements must be unique when using ordered_return"
                )

        if len(lst) <= 0:
            raise TypeError("Empty lists are not allowed")
        if not callable(callback):
            raise TypeError("callback must be a function")

        self.run_event("before_start")
        for group_arg in self.chunks(lst, self.threads):
            if self.stopped:
                return StoppedWorker(self.__soft_parse_returns())

            self.run_queue = [
                self.worker_type(
                    args=(
                        callback,
                        arg,
                        *args,
                    ),
                    daemon=self.daemon,
                    target=self._runner_,
                )
                for arg in group_arg
            ]
            for thread in self.run_queue:
                thread.start()
                self.currently_running.append(thread)
            for i in self.currently_running:
                i.join()

            self.currently_running.clear()

        if self.stopped:
            return StoppedWorker(self.__soft_parse_returns())

        if not self.ordered_return:
            self.run_event("complete", self.results)
            return self.results
        else:

            results = []
            for i in lst:
                if i in self.results_dict:
                    results.append(self.results_dict[i])
                else:
                    results.append(None)
                    warnings.warn(
                        "Not all functions had a return value you should avoid this when using ordered returns",
                    )

            self.results = results
            self.run_event("complete", self.results)
            return results


class AsynchronousWorkload(Workload):
    def run(self, lst, callback, *args):
        self.thread = Thread(
            target=super().run, args=(lst, callback, *args), daemon=self.daemon
        )

        self.thread.start()


class ProgressWorkload(Workload):
    def __init__(
        self,
        threads=AutoThreads,
        daemon=None,
        ordered_return=True,
        worker_type=Thread,
        tqdm_opts={},
    ):

        super().__init__(
            threads=threads,
            daemon=daemon,
            ordered_return=ordered_return,
            worker_type=worker_type,
        )
        self.tqdm_opts = tqdm_opts
        self.register_event(
            "thread_complete", lambda *_: self.progress_bar.update()
        )
        self.register_event("complete", lambda *_: self.progress_bar.close())
        self.register_event("before_start", self.before_start)

    def before_start(self):
        self.progress_bar = tqdm.tqdm(total=len(self.lst), **self.tqdm_opts)

    def stop(self):
        if hasattr(self, "progress_bar"):
            self.progress_bar.close()

        return super().stop()

    def terminate(self):
        if hasattr(self, "progress_bar"):
            self.progress_bar.close()
        return super().terminate()


class AsynchronousProgressWorkload(ProgressWorkload, AsynchronousWorkload):
    pass
