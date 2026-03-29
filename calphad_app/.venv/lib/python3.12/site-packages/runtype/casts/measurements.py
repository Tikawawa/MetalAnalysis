from typing import Type

from runtype.cast import add_cast, cast, FloatBox


# Units

class MeasurementUnit(FloatBox):
    pass

class Temperature(MeasurementUnit):
    pass

class Celsius(Temperature):
    pass

class Fahrenheit(Temperature):
    pass

CELSIUS_FAHRENHEIT_RATIO = 9. / 5

@add_cast
def _(c: Celsius, _: Fahrenheit):
    return c.float * CELSIUS_FAHRENHEIT_RATIO + 32

@add_cast
def _(f: Fahrenheit , _: Celsius):
    return (f.float - 32.0) / CELSIUS_FAHRENHEIT_RATIO


class Angle(MeasurementUnit):
    pass

class Radians(Angle):
    pass

class Degrees(Angle):
    pass


class Unit(MeasurementUnit):
    pass


class FunctionResult(FloatBox):
    pass

@add_cast
def _(i: int | float, to_type: Type[FunctionResult]):
    # We block casting to prevent confusion. Users might think
    # that Sine(0.5) runs the function sin, instead of just storing a result.
    raise TypeError(f"Cannot cast '{i}' to {to_type}. Try casting from a different type, or using ._new()")

class Sine(FunctionResult):
    pass

class Cosine(FunctionResult):
    pass

import math
@add_cast
def _(r: Radians , t: Sine):
    return t._new(math.sin(r.float))

@add_cast
def _(r: Radians , t: Cosine):
    return t._new(math.cos(r.float))


DEGREE_RADIAN_RATIO = math.pi / 180.

@add_cast
def _(a: Degrees, _: Radians):
    return a.float * DEGREE_RADIAN_RATIO

@add_cast
def _(a: Radians, _: Degrees):
    return a.float / DEGREE_RADIAN_RATIO




class TimeDuration(FloatBox):
    pass

@add_cast
def _(i: int | float, to_type: Type[FloatBox]):
    return to_type._new(float(i))

class Hours(TimeDuration): pass
class Minutes(TimeDuration): pass
class Seconds(TimeDuration): pass

@add_cast
def _(i: Hours, to_type: Type[Minutes]):
    return i.float * 60



def test():
    x = Celsius(100)
    assert cast(cast(x, Fahrenheit), Celsius) == x
    assert Celsius(Fahrenheit(x)) == x

    right_angle = Degrees(90)
    assert Degrees(Radians(right_angle)) == right_angle

    assert cast(cast(right_angle, Radians), Sine).float == 1.0
    assert Sine(Radians(right_angle)) == Sine._new(1.0)

    # assert autocast(straight_angle, Sine).value == 1.0

    assert Hours(5) == Hours._new(5.0)
    assert hash(Hours(5)) == hash(Hours._new(5.0))
    # assertRaises(Hours._new(5.0)

    hours = Hours(5)
    assert Minutes(hours).float == 300

