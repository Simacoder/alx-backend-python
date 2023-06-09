#!/usr/bin/env python3
"""
Tasks three
"""

import asyncio

wait_random = __import__('0-basic_async_syntax').wait_random


def task_wait_random(max_delay: int) -> asyncio.Task:
    """
    takes an integer max_delay
     and returns a asyncio.Task.
    :param max_delay:
    :return:
    """
    return asyncio.create_task(wait_random(max_delay))
