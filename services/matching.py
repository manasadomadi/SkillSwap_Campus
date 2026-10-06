from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def get_skill_names(user, skill_type):
    """
    Get all skill names for a user based on
    TEACH or LEARN.
    """

    return [
        item.skill.name.lower()
        for item in user.skills
        if item.skill_type == skill_type
    ]


def calculate_match(user, other_user):
    """
    Calculate compatibility between two students.

    A good match happens when:
    - I can teach something they want to learn
    - They can teach something I want to learn
    """

    user_teach = get_skill_names(user, "TEACH")
    user_learn = get_skill_names(user, "LEARN")

    other_teach = get_skill_names(other_user, "TEACH")
    other_learn = get_skill_names(other_user, "LEARN")

    if not user_teach or not user_learn:
        return 0

    if not other_teach or not other_learn:
        return 0

    # Direct skill overlap
    teach_match = set(user_teach) & set(other_learn)

    learn_match = set(user_learn) & set(other_teach)

    # If there is no reciprocal match
    if not teach_match and not learn_match:
        return 0

    # Create text representations
    user_teach_text = " ".join(user_teach)
    user_learn_text = " ".join(user_learn)

    other_teach_text = " ".join(other_teach)
    other_learn_text = " ".join(other_learn)

    texts = [
        user_teach_text,
        user_learn_text,
        other_teach_text,
        other_learn_text
    ]

    try:
        vectorizer = TfidfVectorizer()

        matrix = vectorizer.fit_transform(texts)

        # What I teach ↔ What they learn
        teach_to_learn = cosine_similarity(
            matrix[0:1],
            matrix[3:4]
        )[0][0]

        # What I learn ↔ What they teach
        learn_to_teach = cosine_similarity(
            matrix[1:2],
            matrix[2:3]
        )[0][0]

        score = (
            teach_to_learn +
            learn_to_teach
        ) / 2

        # Give additional importance to exact matches
        if teach_match:
            score += 0.20

        if learn_match:
            score += 0.20

        score = min(score, 1.0)

        return round(score * 100, 2)

    except Exception:
        return 0


def get_common_skills(user, other_user):

    user_teach = set(
        get_skill_names(user, "TEACH")
    )

    user_learn = set(
        get_skill_names(user, "LEARN")
    )

    other_teach = set(
        get_skill_names(other_user, "TEACH")
    )

    other_learn = set(
        get_skill_names(other_user, "LEARN")
    )

    skills = (
        (user_teach & other_learn)
        |
        (user_learn & other_teach)
    )

    return sorted(skills)