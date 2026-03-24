from src.models.postgres_filter import check_prerequisites_satisfied

def test_prereq_check():
    prereq_map = {
        "IE7615": ["IE6400"]
    }

    satisfied, missing = check_prerequisites_satisfied(
        "IE7615",
        ["IE6400"],
        prereq_map
    )

    assert satisfied is True