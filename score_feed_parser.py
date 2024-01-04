"""Take data from discord channel exporter for "scores-feed"
in Discord official PewPewLive server, and parse it
"""
import csv
import sys

from loguru import logger

logger.remove(0)
logger.add(sys.stderr, level="INFO")

# uncomment the next line for logging into file
# (performance drops significantly, tests only)
# logger.add("score_feed_parser.log", level="TRACE")

logger = logger.opt(colors=True)

platforms = {
                "android": ["Android", ":android:", "<:android:"],
                "ios": [":ios:", ""],
                "windows": ["🪟"],
                "web": ["🌐", "web"],
                "unknown": ["❓"]
            }


def get_data(file: str) -> list[list[str]]:
    """Get data from given file (only time,
    content and reactions)"""
    logger.debug("Getting data from <y>{}</>", file)

    results = []
    with open(file, "r", encoding="UTF-8") as file:
        reader = csv.reader(file)
        for row in reader:
            time, content, attachments, reactions = row[2:]
            results.append([time, content, reactions])

    return results[1:]  # remove headers


def parse_time(time: str) -> list[str]:
    """Parse time from given string"""
    logger.debug("Parsing time: <w>{}</>", time)
    return time.split("T")


def get_usernames(content: str) -> list:
    """Get usernames (1/2 player) and era from given content"""
    logger.debug("Getting usernames: <w>{}</>", content)

    if "(era 1)" in content:
        era = 1
        split_content = content.split()[2:]  # remove "(era 1)"
    else:
        era = 2
        split_content = content.split()
    logger.debug("Got era: <y>{}</>, content: <w>{}</>",
                 era, split_content)

    usernames = []
    for raw_username in [split_content[0], split_content[2]]:
        if raw_username[0] == "`" and raw_username[-1] == "`":
            username = raw_username[1:-1]
        else:
            username = raw_username
        usernames.append(username)
    mode = 2
    logger.debug("Got usernames (assuming 2p): <y>{}</>", usernames)

    # case with 1p mode
    if split_content[1] != "and":
        usernames[1] = None
        mode = 1

    # edge case for older version of Score bot
    if "(2 players mode)" in content:
        mode = 2

    logger.debug("Got usernames: <y>{}</>", usernames)
    return [era, mode, *usernames]


def get_country_and_platform(content: str) -> list[str]:
    """Get country and platform from given content"""
    logger.debug("Getting country and platform: <w>{}</>", content)

    if content[-1] != ")":
        return None, None

    data = content[:-1].split("(")[-1]   # country and platform
    data = "".join([x for x in data if x != " "])  # remove spaces
    data = data.split("-")               # separate country/platform

    if len(data) == 1:
        country = data[0]
        return country, None

    country, platform = data
    # print(platform)
    logger.debug("Got country: <y>{}</>, platform: <y>{}</>",
                 country, platform)
    for name, alias in platforms.items():
        if platform in alias:
            platform_name = name
            break
    logger.debug("Replaced <y>{}</> with <y>{}</>",
                 platform, platform_name)

    return country, platform_name


def get_level(content: str) -> str:
    """Get level name from given content"""
    logger.debug("Getting level name: <w>{}</>", content)

    split_content = content.split()
    in_word_index = split_content.index("in")
    level_name_index = in_word_index + 1
    
    level_name = []
    for word in split_content[level_name_index:]:
        if word[0] == "(":
            break
        level_name.append(word)

    level_name = " ".join(level_name)
    if level_name[0] == "`" and level_name[-1] == "`":
        level_name = level_name[1:-1]

    return "".join(level_name)


def get_score(content: str) -> str:
    """Get score from given content (final, 'increased to')"""
    logger.debug("Getting player's final score: <w>{}</>", content)

    split_content = content.split()
    in_word_index = split_content.index("in")
    level_score_index = in_word_index - 1
    
    level_score = split_content[level_score_index]

    return level_score


def parse_content(content: str) -> list[str]:
    """Parse content from given string"""
    logger.debug("Parsing content: <w>{}</>", content)

    # only work with last line, where the score itself is
    logger.trace("Discrading everything except the last line")
    content = content.split("\n")[-1]

    era, mode, player1, player2 = get_usernames(content)
    
    if mode == 1:
        country, platform = get_country_and_platform(content)
    else:
        country, platform = None, None

    level = get_level(content)
    score = get_score(content)

    return [era, mode, player1, player2, level, score, country, platform]


def parse_row(row: list[str]) -> list[str|int]:
    """Parse data from given row"""
    logger.debug("Parsing row: <w>{}</>", row)
    time, content, reactions = row

    parsed_time = parse_time(time)
    parsed_content = parse_content(content)

    result = [*parsed_time, *parsed_content, reactions]
    logger.debug("Parsed row, got <y>{}</>", result)
    return result


def write_parsed(file: str, data: list[list[any]]) -> None:
    """Write parsed data to given file"""
    logger.debug("Writing parsed data to <y>{}</>", file)

    with open(file, "w", encoding="UTF-8") as file:
        writer = csv.writer(file)
        writer.writerows(data)


def main(data_file: str) -> list[list[str|int]]:
    """Parse data from given file"""

    data = get_data(data_file)
    data_len = len(data)

    info_step = data_len // 100
    if info_step == 0:
        info_step = 1

    parsed = []
    for row in data:

        try:
            parsed.append(parse_row(row))
        except Exception as e:
            logger.warning(e)

        # uncomment the following code for info on progress
        # (slows down the process significantly, tests only)

        #if data.index(row) % info_step == 0:
        #    percent = round((data.index(row) + 1) / data_len * 100)
        #    logger.info("Parsed <y>{}</>/{} (<y>{}%</>) rows",
        #                data.index(row) + 1, data_len, percent)

    write_parsed("output.csv", parsed)


if __name__ == "__main__":
    logger.debug('__name__=="__main__": running main()...')

    args = sys.argv[1:]
    main(args[0])
