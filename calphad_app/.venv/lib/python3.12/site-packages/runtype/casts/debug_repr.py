import typing as t
from itertools import islice
from typing import Type
import dataclasses

from runtype.cast import add_cast, cast, StringBox

class DebugRepr(StringBox):
    def __str__(self):
        return self.str

class DebugReprShort(DebugRepr):
    pass

@add_cast
def _(obj, to: Type[DebugRepr]):
    if dataclasses.is_dataclass(obj):
        name = type(obj).__name__
        attrs = {f.name:to(getattr(obj, f.name)) for f in dataclasses.fields(obj) if f.repr}
        contents = ', '.join(f'{k}={v}' for k, v in attrs.items())
        s = f'{name}({contents})'
    else:
        s = repr(obj)

    return to._new(s)



def _repr_sequence(a: t.Sequence, to: Type[DebugRepr], fmt: str):
    items = [to(i).str for i in a]
    return to._new(fmt % ', '.join(items))

@add_cast
def _(obj: list, t: Type[DebugRepr]):
    return _repr_sequence(obj, t, "[%s]")

@add_cast
def _(a: set, to: Type[DebugRepr]):
    return _repr_sequence(a, to, "{%s}") if a else to._new("set()")

@add_cast
def _(a: frozenset, to: Type[DebugRepr]):
    return _repr_sequence(a, to, "frozenset({%s})") if a else to._new("frozenset()")

@add_cast
def _(a: tuple, t: Type[DebugRepr]):
    return _repr_sequence(a, t, "(%s,)" if len(a) == 1 else "(%s)")

@add_cast
def _(a: dict, to: Type[DebugRepr]):
    contents = [f"{to(k)}: {to(v)}" for k, v in a.items()]
    return to._new("{%s}" % ', '.join(contents))
    

T = t.TypeVar("T")
def _shorten_sequence(seq: t.Sequence[T], max_len: int) -> tuple[t.Collection[T], str]:
    if len(seq) <= max_len:
        return seq, ""
    short = list(islice(seq, max_len))
    x = f", .. ({len(seq) - max_len})"
    return short, x

MAX_LEN = 3

@add_cast
def _(seq: tuple, t: Type[DebugReprShort]):
    short, x = _shorten_sequence(seq, MAX_LEN)
    return _repr_sequence(short, t, f"(%s{x})")

@add_cast
def _(seq: list, t: Type[DebugReprShort]):
    short, x = _shorten_sequence(seq, MAX_LEN)
    return _repr_sequence(short, t, f"[%s{x}]")

@add_cast
def _(seq: set, t: Type[DebugReprShort]):
    short, x = _shorten_sequence(seq, MAX_LEN)
    return _repr_sequence(short, t, f"{{%s{x}}}")


@add_cast
def _(seq: frozenset, t: Type[DebugReprShort]):
    short, x = _shorten_sequence(seq, MAX_LEN)
    return _repr_sequence(short, t, f"frozenset({{%s{x}}})")

@add_cast
def _(seq: dict, t: Type[DebugReprShort]):
    short, x = _shorten_sequence(seq.items(), MAX_LEN)
    contents = [f"{t(k)}: {t(v)}" for k, v in short]
    return t._new("{%s%s}" % (', '.join(contents), x))




# DebugReprFull (XXX TBD WIP)

class DebugReprAllFields(DebugRepr):
    """Shows fields that are normally hidden, e.g. with repr=False
    """
    pass


def _(obj, to: Type[DebugReprAllFields]):
    # TODO priority for arg0 over arg1
    if dataclasses.is_dataclass(obj):
        name = type(obj).__name__
        attrs = {f.name:to(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
        contents = ', '.join(f'{k}={v}' for k, v in attrs.items())
        s = f'{name}({contents})'
    else:
        s = repr(obj)

    return to._new(s)

add_cast(_, priority=-1)




def test():
    
    assert cast("foo", str) == "foo"
    assert cast("foo", DebugRepr).str == "'foo'"

    # # assert cast(["foo", "bar"], Pretty).s == "[foo, bar]"
    assert DebugRepr(["foo", "bar"]).str == "['foo', 'bar']"

    # # print( cast(["foo", "bar", "!", "too long"], PrettyDebugShort).s )
    # # assert cast(["foo", "bar", "!", "too long"], PrettyShort).s == "[foo, bar, !, ..]"
    assert DebugReprShort(["foo", "bar", "!", "too long"]).str == "['foo', 'bar', '!', .. (1)]"

    assert DebugReprShort({1,2,3,4,5}).str == "{1, 2, 3, .. (2)}"
    assert DebugReprShort(frozenset({1,2,3,4,5})).str == "frozenset({1, 2, 3, .. (2)})"


    assert DebugRepr([{}, (), (1,)]).str == "[{}, (), (1,)]"
    assert DebugRepr([set()]).str == "[set()]", DebugRepr([set()]).str

    assert DebugRepr([{1: 2, 2: 1}]).str == "[{1: 2, 2: 1}]"



    # print(DebugReprShort((1,2,3,4,5)))
    # print(DebugReprShort({i:i for i in range(100)}))
    # print(DebugReprShort({i for i in range(100)}))

    # import rich
    # rich.print(DebugReprShort({i:{j for j in range(100)} for i in range(100)}))