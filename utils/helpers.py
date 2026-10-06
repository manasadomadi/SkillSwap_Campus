import re


def normalize_email(email):
    return email.strip().lower()


def normalize_skill(skill):
    return " ".join(skill.strip().lower().split())


def valid_email(email):
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return re.match(pattern, email) is not None


def skill_display_name(skill):
    return skill.title()