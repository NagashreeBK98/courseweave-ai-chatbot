from src.data.adzuna_scraper import extract_skills_from_text

def test_skill_extraction():
    text = "We need Python and SQL experience"
    skills = extract_skills_from_text(text)
    assert "Python" in skills
    assert "SQL" in skills