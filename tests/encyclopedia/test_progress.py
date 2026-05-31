from encyclopedia.cabook_annotate.progress import ProgressBar


def test_progress_bar_reaches_total(capsys):
    bar = ProgressBar(10, label="test", file=__import__("io").StringIO())
    for _ in range(10):
        bar.update(1)
    bar.close()
    assert bar.n == 10
