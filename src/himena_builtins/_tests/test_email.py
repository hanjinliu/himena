from himena.widgets import MainWindow


def test_email_widget(himena_ui: MainWindow, sample_dir):
    himena_ui.read_file(sample_dir / "email.eml")
