from ieum.demo.index_status import get_index_status


class Session:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def execute(self, _):
        return self.rows

    def scalar(self, _):
        return self.rows[0][1]


def test_index_status_flags_mixed_and_unlabeled_vectors():
    status = get_index_status(lambda: Session([(None, 2), ("new-model", 8)]), "new-model")
    assert status["total_chunks"] == 10
    assert status["active_chunks"] == 8
    assert status["counts_by_model"]["<unlabeled>"] == 2
    assert status["ready_for_search"] is False


def test_index_status_requires_nonempty_complete_index():
    assert get_index_status(lambda: Session([]), "new-model")["ready_for_search"] is False
    assert get_index_status(lambda: Session([("new-model", 10)]), "new-model")["ready_for_search"] is True


def test_index_status_reports_pending_migration_without_model_column():
    status = get_index_status(
        lambda: Session([("<unlabeled>", 10)]),
        "new-model",
        schema_has_model=False,
    )
    assert status["total_chunks"] == 10
    assert status["migration_required"] is True
    assert status["ready_for_search"] is False
