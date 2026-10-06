import os

from dotenv import load_dotenv


load_dotenv()


def generate_match_explanation(
    user_name,
    other_name,
    common_skills
):
    if common_skills:
        skills = ", ".join(common_skills)

        return (
            f"{other_name} could be a good skill-swap partner "
            f"for {user_name} because your skill interests "
            f"are related to: {skills}."
        )

    return (
        f"{other_name} may be a potential skill-swap partner "
        f"based on your learning and teaching preferences."
    )