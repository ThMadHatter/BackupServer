import click
from typing import List

def my_func():
    return list([1, 2, 3])

@click.group()
def my_cli():
    pass

@my_cli.command("list")
def list_cmd():
    print("Command list called")

print(f"Result: {my_func()}")
