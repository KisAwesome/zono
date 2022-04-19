import threading
import os


class EmptyElement:
    pass


class AutoThreadsBase:
    pass


class MiddlewareArgument:
    def __init__(self, iteration, _max):
        self.iteration = iteration
        self.max = _max


AutoThreads = AutoThreadsBase()


class Workload:
    AutoThreads = AutoThreadsBase()

    def __init__(self, threads, daemon=False, after=None, before=None, complete=None, ordered_return=False):
        if isinstance(threads, AutoThreadsBase):
            threads = os.cpu_count()

        else:
            if not isinstance(threads, int):
                raise ValueError('Threads must be an integer')

            if threads <= 0:
                raise ValueError('Threads cannot be less that zero')

        self.threads = threads
        self.results_dict = {}
        self.currently_running = []
        self.daemon = daemon
        self.run_queue = []
        self.after = after
        self.results = []
        self.before = before
        self.ordered_return = ordered_return
        self.complete = complete

    def chunks(self, lst, n):
        k, m = divmod(len(lst), n)
        _list = (lst[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n))
        fin = []
        for _el in _list:
            fin.append(_el)

        return fin

    def parse_jobs(self, jobs):
        _max = 0
        empty = EmptyElement()

        for job in jobs:
            if len(job) > _max:
                _max = len(job)

        for index, job in enumerate(jobs):
            if len(jobs[index]) < _max:
                missing = _max-len(jobs[index])
                for _missing in range(missing):
                    jobs[index].append(empty)

        return jobs, _max

    def _runner_(self, func, arg, *args):
        ret = func(arg, *args)
        if self.ordered_return:
            self.results_dict[arg] = ret
        else:
            self.results.append(ret)

    def run(self, lst, callback, *args):
        self.results.clear()
        if len(lst) <= 0:
            raise TypeError('Empty lists are not allowed')
        _jobs = self.chunks(lst, self.threads)
        jobs, _max = self.parse_jobs(_jobs)
        if not callable(callback):
            raise TypeError('callback must be a function')

        lst = list(lst)

        for ind in range(_max):
            for argument_ in jobs:
                arg = argument_[ind]
                if isinstance(arg, EmptyElement):
                    continue
                thread = threading.Thread(
                    args=(callback, arg, *args,), daemon=self.daemon, target=self._runner_)

                self.run_queue.append(thread)

            if callable(self.before):
                self.before(MiddlewareArgument(ind+1, _max))

            for torun in self.run_queue:
                self.currently_running.append(torun)
                torun.start()

            self.run_queue.clear()

            for d in self.currently_running:
                d.join()
                del d

            self.currently_running.clear()
            if callable(self.after):
                self.after(MiddlewareArgument(ind+1, _max))

        if callable(self.complete):
            self.complete()

        if not self.ordered_return:
            return self.results
        else:
            results = []
            for i in lst:
                if i in self.results_dict:
                    results.append(self.results_dict[i])

            return results


class AsynchronousWorkload(Workload):
    def __init__(self, threads, daemon=False, after=None, before=None, complete=None):
        super().__init__(threads, daemon=daemon, after=after, before=before, complete=complete)

    def run(self, lst, callback, *args):
        thread = threading.Thread(
            target=Workload.run, args=(self, lst, callback, *args), daemon=self.daemon)

        thread.start()


