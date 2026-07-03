"""Главная точка запуска командного проекта Retail Data Analytics."""

from cleaning import main as clean_all_data


def main() -> None:
    """Сначала очищает данные; ниже будут запускаться задания команды."""
    clean_all_data()

    # После объединения работ добавьте сюда вызовы заданий:
    # task_01()
    # task_02()
    # ...
    # task_22()


if __name__ == "__main__":
    main()
