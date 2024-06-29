LONG_MONTHS: set = {1, 3, 5, 7, 8, 10, 12}
SHORT_MONTHS: set = {4, 6, 9, 11}
DAY_TICK: int = 86400
YEAR_TICK: int = DAY_TICK * 365

def days_of_month(month: int, leap_year: bool) -> int:
    return 31 if month in LONG_MONTHS else 30 if month in SHORT_MONTHS else 29 if leap_year else 28

def epoch_to_date(epoch: int) -> str:
    year: int = 1970
    month: int = 1
    day: int = 1

    next_leap_year: int = 1972
    leap_year: bool = False

    if epoch > 0:
        while epoch >= YEAR_TICK + (DAY_TICK if leap_year else 0):
            year += 1
            epoch -= YEAR_TICK + (DAY_TICK if leap_year else 0)
            if leap_year:
                leap_year = False
            elif year == next_leap_year:
                leap_year = True
                next_leap_year += 4

    elif epoch < 0:
        year -= 1
        next_leap_year -= 4

        while epoch <= -(YEAR_TICK + (DAY_TICK if leap_year else 0)):
            year -= 1
            epoch += YEAR_TICK + (DAY_TICK if leap_year else 0)
            if leap_year:
                leap_year = False
            elif year == next_leap_year:
                leap_year = True
                next_leap_year -= 4

        epoch += (YEAR_TICK + (DAY_TICK if leap_year else 0))

    while epoch >= DAY_TICK:
        days: int = days_of_month(month, leap_year)
        months_tick: int = days * DAY_TICK
        if epoch >= months_tick:
            month += 1
            epoch -= months_tick
        else:
            day = epoch // DAY_TICK
            epoch -= (day * DAY_TICK)
            if epoch >= 0:
                day += 1

    return f"{year}-{month:02}-{day:02}"

def date_to_epoch(string: str) -> int:
    parts: list = string.split('-')
    try:
        year: int = int(parts[0])
        month: int = int(parts[1])
        day: int = int(parts[2])
    except (IndexError, ValueError):
        return 0

    epoch: int = 0
    leap_year: bool = False
    next_leap_year: int = 1972
    if year >= 1970:
        for y in range(1970, year):
            epoch += YEAR_TICK + (DAY_TICK if leap_year else 0)

            if leap_year:
                leap_year = False

            elif y == next_leap_year:
                leap_year = True
                next_leap_year += 4

        for m in range(1, month):
            days: int = days_of_month(m, leap_year)
            epoch += (days * DAY_TICK)

        epoch += (day - 1) * DAY_TICK + 43200  # adds half day -> 12 o'clock

    elif year < 1970:
        next_leap_year = 1968
        for y in range(1969, year, -1):
            epoch -= (YEAR_TICK + (DAY_TICK if leap_year else 0))
            if leap_year:
                leap_year = False

            elif y == next_leap_year:
                leap_year = True
                next_leap_year -= 4

        for m in range(12, month, -1):
            days: int = days_of_month(m, leap_year)
            epoch -= (days * DAY_TICK)

        days: int = days_of_month(month, leap_year)
        epoch -= (days - day + 1) * DAY_TICK + 43200  # adds half day -> 12 o'clock

    return epoch