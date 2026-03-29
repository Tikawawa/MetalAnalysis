#
# NOTE: Currently doesn't work because we don't support dispatch on generics
#       Type[X] gets cached as <type>
#

import inspect
import typing as t
from datetime import datetime

from . import pytypes
from . import datetime_parse
from . import multidispatch_final, MultiDispatch, PythonTyping
import runtype


multidispatch = MultiDispatch(PythonTyping(), enable_generics=(t.Type,))

class CastFailed(Exception):
    ...


def get_parameter_names(func):
    return [param.name for param in inspect.signature(func).parameters.values()]

def add_cast(cast_f, *, priority=None):
    to_key = get_parameter_names(cast_f)[1]
    ann = cast_f.__annotations__
    if ann.get(to_key, None):
        # If to param not is Type[...], make it one
        typ = pytypes.type_caster.to_canon(ann[to_key])
        if not isinstance(typ, pytypes.TypeType):
            ann[to_key] = t.Type[ann[to_key]]

    md = multidispatch(priority=priority) if priority else multidispatch
    return md(cast_f)


@add_cast
def _(obj: str, to_type: t.Type[int]):
    assert to_type is int
    try:
        return int(obj)
    except ValueError:
        raise CastFailed()


@add_cast
def _(obj: str | int, to_type: t.Type[float]):
    # assert to_type is float
    try:
        return float(obj)
    except ValueError:
        raise CastFailed()


@add_cast
def _(obj: str, _: datetime):
    try:
        return datetime_parse.parse_datetime(obj)
    except datetime_parse.DateTimeError:
        raise CastFailed()


@add_cast
def _(obj, to_type: t.Type[object]):
    if runtype.isa(obj, to_type):
        return obj
    raise CastFailed(obj, to_type)



# @multidispatch_final
@add_cast
def _(obj, to_type):
    raise CastFailed()

T = t.TypeVar("T")
@t.overload
def cast(obj, t: t.Type[T]) -> T:
    ...

@t.overload
def cast(obj, _: type, t: t.Type[T]) -> T:
    ...

def cast(obj, *to_types: type):
    # TODO auto=True or autocast?
    for to_type in to_types:
        while not runtype.isa(obj, to_type):
            # TODO keep track of seen types and throw on recursion
            obj = _(obj, to_type)
    return obj



def autocast(obj, to_type):
    pass


def union_classes(*clss):
    class _Union(*clss):
        pass
    return _Union

def create_box(TYPE: type):
    class _Box:
        _type: type = TYPE
        _value: TYPE

        def __new__(cls, from_obj) -> t.Self:
            return cast(from_obj, cls)

        def __repr__(self):
            return f"{type(self).__name__}({self._value})"

        @classmethod
        def _new(cls, value: TYPE):
            if not isinstance(value, TYPE):
                raise TypeError(f"Expected value of type {TYPE} but got value: {value}.\nTry using {cls.__name__}(...) instead.")
            obj = object.__new__(cls)
            obj._value = value
            return obj

        def __eq__(self, other):
            if isinstance(other, type(self)):
                return self._value == other._value

            return NotImplemented

        def __hash__(self):
            return hash((type(self), self._value))

        @classmethod
        def union(cls, *others):
            for o in others:
                if not (issubclass(o, _Box) and o._type is cls._type):
                    raise TypeError("Can only union with a box of the same base type")
            return union_classes(cls, *others)

    return _Box


class FloatBox(create_box(float)):
    @property
    def float(self) -> float:
        return self._value

class StringBox(create_box(str)):
    @property
    def str(self) -> str:
        return self._value

    def __str__(self):
        raise TypeError("Cannot convert to string. Use the .str attribute instead.")



def test():
    assert cast("1.5", float) == 1.5
    try:
        cast("1", "a")
    except TypeError:
        pass

    assert isinstance(cast("1", float), float)
    assert isinstance(cast("1", int), int)
    assert isinstance(cast(2, int), int)
    assert isinstance(cast(2, float), float)

    from runtype.casts.debug_repr import test
    test()
    from runtype.casts.measurements import test
    test()


if __name__ == "__main__":
    test()


