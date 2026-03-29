from typing import Dict, Any, List, Tuple, Generator
from contextvars import ContextVar, Token
from contextlib import contextmanager

class ContextManager:
    """
    A utility class for managing context-specific variables with a clean API.
    """
    def __init__(self) -> None:
        self._vars: Dict[str, ContextVar[Any]] = {}

    def __getattr__(self, name: str) -> Any:
        """
        Retrieve the value of a context variable.
        Raises AttributeError if the variable does not exist or is not set.
        """
        if name not in self._vars:
            raise AttributeError(f"Context variable '{name}' not set in any context.")
        try:
            return self._vars[name].get()
        except LookupError:
            raise AttributeError(f"Context variable '{name}' not set in this context.")

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Prevent setting attributes directly to enforce using `push`.
        """
        if not name in ('_vars',):  # Allow internal attributes
            raise AttributeError(f"Cannot set attribute '{name}' directly. Use 'push' to manage context variables.")
        super().__setattr__(name, value)

    @contextmanager
    def push(self, **kwargs: Any) -> Generator[None, None, None]:
        """
        Contextually set context variables within a `with` block.
        Automatically resets them after exiting the block.
        
        :param kwargs: Key-value pairs to set as context variables.
        """
        tokens: List[Tuple[str, Token]] = []
        try:
            for key, value in kwargs.items():
                if key not in self._vars:
                    self._vars[key] = ContextVar(key)
                token = self._vars[key].set(value)
                tokens.append((key, token))
            yield
        finally:
            for key, token in tokens:
                self._vars[key].reset(token)


def example_usage() -> None:
    context = ContextManager()

    def sample_function() -> None:
        print(f"Inside function: foo = {context.foo}")

    print("Before context:")
    try:
        print(context.foo)  # This will raise AttributeError
    except AttributeError as e:
        print(e)

    print("\nWithin context:")
    with context.push(foo="bar"):
        print(f"Main block: foo = {context.foo}")
        sample_function()

    print("\nAfter context:")
    try:
        print(context.foo)  # This will raise AttributeError again
    except AttributeError as e:
        print(e)

if __name__ == "__main__":
    example_usage()