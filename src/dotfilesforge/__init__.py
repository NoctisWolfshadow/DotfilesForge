from dotfilesforge import config


def main() -> None:
    print("Hello from dotfilesforge!")
    print(config.load_toml_config()["install"])
