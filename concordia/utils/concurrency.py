# Copyright 2023 DeepMind Technologies Limited.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Concurrency helpers."""

from collections.abc import Collection, Iterator, Sequence
from concurrent import futures
import contextlib
from typing import Any, Callable, TypeVar

_T = TypeVar('_T')


@contextlib.contextmanager
def executor(**kwargs) -> Iterator[futures.ThreadPoolExecutor]:
  """Context manager for a concurrent.futures.ThreadPoolExecutor.

  On normal __exit__ this context manager will behave like
  `ThreadPoolExecutor.__exit__`: it will block until all running and pending
  threads complete.

  However, on an __exit__ due to an error, the executor will be shutdown
  immediately without waiting for the running futures to complete, and all
  pending futures will be cancelled. This allows errors to quickly propagate to
  the caller.

  Args:
    **kwargs: Forwarded to ThreadPoolExecutor.

  Yields:
    A thread pool executor.
  """
  thread_executor = futures.ThreadPoolExecutor(**kwargs)
  try:
    yield thread_executor
  except BaseException:
    thread_executor.shutdown(wait=False, cancel_futures=True)
    raise
  else:
    thread_executor.shutdown()


def run_parallel(
    fn: Callable[..., _T],
    *args: Collection[Any],
    timeout: float | None = None,
    max_workers: int | None = None,
) -> Sequence[_T]:
  """Runs `map(*args)` in parallel.

  IMPORTANT: Passed callables must be threadsafe.

  Args:
    fn: function to execute (MUST BE THREADSAFE)
    *args: arguments to pass to function.
    timeout: the maximum number of seconds to wait.
    max_workers: them maximum number of parallel jobs. If None, will use as many
      workers as there are arguments.

  Returns:
    [fn(arg0, arg1, ...) for arg0, arg1, ...  in zip(*args)]
    However, the calls will be executed concurrently.

  Raises:
    TimeoutError: If all the results are not generated before the timeout.
    Exception: If fn(*args) raises for any values.
  """
  if max_workers is None:
    max_workers = min(len(arg) for arg in args)
  with executor(max_workers=max_workers) as executor_:
    results = executor_.map(fn, *args, timeout=timeout)
    return list(results)  # Consume iterator to surface any errors.
