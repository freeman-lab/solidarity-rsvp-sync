from yachalk import chalk


def create_logger(prefix):
    def logger(string):
        print(f'{prefix} {string}')

    return logger


def ok(text):
    return chalk.green(text)


def warn(text):
    return chalk.yellow(text)


def err(text):
    return chalk.red(text)


def hl(text):
    return chalk.white_bright(str(text))
