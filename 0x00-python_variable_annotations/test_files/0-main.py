#!/usr/bin/env python3
add = __import__('test-files/0-add.py').add

print(add(1.11, 2.22) == 1.11 + 2.22)
print(add.__annotations__)
