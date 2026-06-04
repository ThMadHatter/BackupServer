import click
@click.group()
def my_cli(): pass

@my_cli.command("list")
def list_backups(): pass

print(f"Built-in list: {list}")
print(f"list_backups: {list_backups}")
