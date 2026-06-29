from service import Greeter


def main() -> str:
    greeter = Greeter("Ada")
    return greeter.greet("world", token="secret-value")


if __name__ == "__main__":
    print(main())
