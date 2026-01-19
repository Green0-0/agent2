# ---------- script_1: lots of decorators, async, nested classes & funcs ----------
script_1 = r'''
import os
# a lonely comment       ← must be part of top_level_block_0
from typing import Any

GLOBAL_VAR = 42          # still top_level_block_0

class Outer: # line 7
    """Docstring for Outer"""

    # ---------- nested class ----------
    class Inner: # line 11
        """Inner docstring"""

        def inner_method(self):
            """Docstring inner method"""
            x = 1

            def sub_inner():
                """sub inner docstring"""
                pass                          # sub_inner has no children

            return sub_inner()

        @staticmethod # line 24
        def static():
            pass

    # ---------- normal method that itself nests stuff ----------
    def outer_method(self):
        def nested_function(
            param: int                     # header split over lines
        ) -> int:
            return param * 2

        class MethodClass:
            def method_class_method(self):
                pass

        return nested_function(5)          # will become top_level_block inside the method


@decor1
@decor2(param=1)
def top_level_function(a: int,
                       b: str
                       ) -> None:
    """multiline header decorated function docstring"""
    if a:
        print(b)

    async def inner_async():
        """Docstring for inner async"""
        await async_op()

    return None


async def async_func():
    pass
'''

# ---------- script_2: module docstring, deep-nested classes, decorated inner func ----------
script_2 = r'''
"""Module docstring"""

import math
import sys as system

value = [i for i in range(5)]

def function_one():
    pass

class A:
    # comment inside class but before anything

    class B:
        class C:
            def method_c1(self):
                pass

            def method_c2(self):
                def deep_nested():
                    pass
                return deep_nested          # will be a top_level_block inside C.method_c2

    @classmethod
    def make(cls):
        """Factory method"""
        return cls()

    def instance_method(self):
        x = 0

        @decor
        def decorated_inside():
            """Decorated nested function"""
            return x

        return decorated_inside()

if __name__ == "__main__":
    print("run")
'''

from agent2.parsing.code_parsers.parse_python import parse_python_elements

def dump(elements, indent=0):
    for el in elements:
        pad = "    " * indent
        print(f"{pad}{el.identifier:40}  line={el.line_start:>3}  header={el.header!r}")
        if el.description:
            print(f"{pad}    docstring: {el.description.splitlines()[0]!r}")
        dump(el.elements, indent + 1)


print("================  SCRIPT 1  ================\n")
elements1 = parse_python_elements(script_1)
dump(elements1)
print(elements1[1].elements[1].elements[0].content)

print("\n================  SCRIPT 2  ================\n")
elements2 = parse_python_elements(script_2)
dump(elements2)
