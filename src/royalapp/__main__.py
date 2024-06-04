from royalapp import new_window


def main(profile: str | None = None):
    ui = new_window(profile)
    ui.show(run=True)
