from django.db import models
import random
from typing import List

class Number(models.Model):
    base = models.IntegerField()
    digits = models.JSONField()
    value = models.FloatField()
    negative = models.BooleanField(default=False)

    def __init__(self, base: int, digits: List[int], value: float = None, negative: bool = False):
        self.base = base
        self.digits = digits
        self.negative = negative
        self.value = value if value is not None else self._to_decimal()

    @staticmethod
    def random(min_len=1, max_len=3):
        base = random.randint(2, 10)
        length = random.randint(min_len, max_len)
        while True:
            digits = [random.randint(0, base - 1) for _ in range(length)]
            while len(digits) > 1 and digits[0] == 0:
                digits = digits[1:]
            if digits[0] != 0 or len(digits) == 1:
                value = sum(d * (base ** i) for i, d in enumerate(reversed(digits)))
                if value != 0:
                    break
        return Number(base, digits, value, negative=False)

    @staticmethod
    def from_value(base: int, value: float):
        negative = value < 0
        abs_val = abs(value)
        integer_part = int(abs_val)
        integer_digits = Number.decimal_to_digits(base, integer_part)
        return Number(base, integer_digits, round(value, 5), negative=negative)

    @staticmethod
    def decimal_to_digits(base: int, value: int):
        if value == 0:
            return [0]
        digits = []
        while value > 0:
            digits.append(value % base)
            value //= base
        return digits[::-1]

    @staticmethod
    def decimal_to_fractional_digits(base: int, value: float, precision: int = 5):
        digits = []
        for _ in range(precision):
            value *= base
            digit = int(value)
            digits.append(digit)
            value -= digit
        return digits

    def _to_decimal(self):
        value = sum(d * (self.base ** i) for i, d in enumerate(reversed(self.digits)))
        return -value if self.negative else value

    def __str__(self):
        sign = '-' if self.negative else ''
        integer_digits = ''.join(map(str, self.digits))
        if self.value == int(self.value):
            return f"[{sign}{integer_digits}] (осн. {self.base})"
        fractional_value = abs(self.value) - int(abs(self.value))
        fractional_digits = Number.decimal_to_fractional_digits(self.base, fractional_value, 5)
        fractional_str = ''.join(map(str, fractional_digits)).rstrip('0')
        return f"[{sign}{integer_digits}.{fractional_str}] (осн. {self.base})"