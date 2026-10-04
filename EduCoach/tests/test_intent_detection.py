import pytest

from educoach.orchestrator import (
    IntentResolutionStatus,
    IntentType,
    detect_intents,
)


@pytest.mark.parametrize(
    "message",
    [
        "Bana haftalık çalışma programı hazırla.",
        "Bugün için bir plan yap.",
        "Çalışma programımı düzenle.",
        "Bana haftalık plan yapar mısın?",
        "Bu hafta ne çalışayım?",
    ],
)
def test_explicit_planning_is_detected(message: str) -> None:
    assert IntentType.PLANNING in detect_intents(message).intents


def test_program_definition_is_not_planning() -> None:
    result = detect_intents("Program nedir?")

    assert IntentType.PLANNING not in result.intents
    assert result.intents == (IntentType.KNOWLEDGE_QUESTION,)


@pytest.mark.parametrize(
    "message",
    [
        "Denememi analiz et.",
        "TYT'de 74 net yaptım.",
        "30 doğru 8 yanlış yaptım.",
        "Denemede matematik netim düştü.",
    ],
)
def test_explicit_assessment_evidence_is_detected(message: str) -> None:
    assert detect_intents(message).intents == (
        IntentType.ASSESSMENT_ANALYSIS,
    )


@pytest.mark.parametrize(
    "message",
    ["Yarın sınavım var.", "Bunu değerlendir."],
)
def test_weak_assessment_language_is_not_detected(message: str) -> None:
    assert IntentType.ASSESSMENT_ANALYSIS not in detect_intents(message).intents


@pytest.mark.parametrize(
    "message",
    [
        "Matematiğe nasıl çalışmalıyım?",
        "Paragraf için çalışma önerisi ver.",
        "Çalışma önerisi verir misin?",
        "Nasıl çalışayım?",
    ],
)
def test_explicit_study_advice_is_detected(message: str) -> None:
    result = detect_intents(message)

    assert result.intents == (IntentType.STUDY_ADVICE,)
    assert IntentType.KNOWLEDGE_QUESTION not in result.intents


@pytest.mark.parametrize(
    "message",
    [
        "Bana hedef belirlememde yardım et.",
        "Bu ay için hedef koyalım.",
        "Hedefimi belirlemek istiyorum.",
    ],
)
def test_explicit_goal_setting_is_detected(message: str) -> None:
    assert detect_intents(message).intents == (IntentType.GOAL_SETTING,)


@pytest.mark.parametrize(
    "message",
    [
        "Beni motive et.",
        "Beni motive eder misin?",
        "Motivasyona ihtiyacım var.",
        "Çalışma isteğim kalmadı, biraz motive eder misin?",
    ],
)
def test_explicit_motivation_support_is_detected(message: str) -> None:
    assert detect_intents(message).intents == (
        IntentType.MOTIVATION_SUPPORT,
    )


@pytest.mark.parametrize(
    "message",
    [
        "Motivasyona ihtiyacım yok.",
        "Geçen ay motivasyona ihtiyacım vardı.",
        "Artık motivasyona ihtiyacım kalmadı.",
    ],
)
def test_non_current_or_negative_motivation_need_is_not_detected(
    message: str,
) -> None:
    assert IntentType.MOTIVATION_SUPPORT not in detect_intents(message).intents


@pytest.mark.parametrize(
    "message",
    [
        "Aralıklı tekrar nedir?",
        "Pomodoro tekniği ne demek?",
        "Bu sınavın yapısı nedir?",
    ],
)
def test_explicit_definition_question_is_detected(message: str) -> None:
    assert detect_intents(message).intents == (IntentType.KNOWLEDGE_QUESTION,)


@pytest.mark.parametrize(
    "message",
    ["Merhaba", "Selam!", "Günaydın.", "Teşekkür ederim"],
)
def test_greeting_only_is_general_conversation(message: str) -> None:
    assert detect_intents(message).intents == (
        IntentType.GENERAL_CONVERSATION,
    )


def test_greeting_with_substantive_request_is_not_general_conversation() -> None:
    result = detect_intents("Merhaba, bana haftalık plan yap.")

    assert result.intents == (IntentType.PLANNING,)


@pytest.mark.parametrize(
    "message",
    [
        "Matematik",
        "Bugün biraz kötüyüm.",
        "YKS",
        "Bununla ilgili ne düşünüyorsun?",
        "Bir şey soracağım.",
    ],
)
def test_weak_or_unknown_message_is_unresolved(message: str) -> None:
    result = detect_intents(message)

    assert result.status == IntentResolutionStatus.UNRESOLVED
    assert result.intents == ()


def test_assessment_and_planning_are_detected_together_canonically() -> None:
    result = detect_intents(
        "Son denememde matematik netim düştü. Bu hafta ne çalışayım?"
    )

    assert result.intents == (
        IntentType.PLANNING,
        IntentType.ASSESSMENT_ANALYSIS,
    )


def test_duplicate_evidence_does_not_duplicate_the_intent() -> None:
    result = detect_intents("TYT'de 74 net, 30 doğru ve 8 yanlış yaptım.")

    assert result.intents == (IntentType.ASSESSMENT_ANALYSIS,)


@pytest.mark.parametrize(
    "message",
    [
        "BANA HAFTALIK PLAN YAP",
        "  Bana   haftalık   plan   yap  ",
        "Bana haftalık plan yap!!!",
    ],
)
def test_case_whitespace_and_punctuation_do_not_change_detection(
    message: str,
) -> None:
    assert detect_intents(message).intents == (IntentType.PLANNING,)


def test_detection_is_repeatable() -> None:
    message = "Aralıklı tekrar nedir?"

    assert detect_intents(message) == detect_intents(message)


def test_unsupported_v01_intents_are_not_guessed() -> None:
    unsupported = {
        IntentType.PROGRESS_REVIEW,
        IntentType.MEMORY_UPDATE,
        IntentType.TASK_UPDATE,
        IntentType.CLARIFICATION,
    }

    assert unsupported.isdisjoint(detect_intents("Programımı kaydet.").intents)


@pytest.mark.parametrize(
    ("message", "excluded_intent", "expected_intents"),
    [
        (
            "Dün bir çalışma programı yaptım.",
            IntentType.PLANNING,
            (),
        ),
        ("Program yapmadım.", IntentType.PLANNING, ()),
        ("Çalışma programı nasıl yapılır?", IntentType.PLANNING, ()),
        ("Program oluşturuldu.", IntentType.PLANNING, ()),
        ("Hedefimi geçen ay belirledim.", IntentType.GOAL_SETTING, ()),
        ("Daha önce hedef koymuştum.", IntentType.GOAL_SETTING, ()),
        ("Hedef oluşturuldu.", IntentType.GOAL_SETTING, ()),
        (
            "Öğretmenim beni motive etti.",
            IntentType.MOTIVATION_SUPPORT,
            (),
        ),
        (
            "Bu video beni motive etmişti.",
            IntentType.MOTIVATION_SUPPORT,
            (),
        ),
        (
            "Arkadaşım bana çalışma önerisi verdi.",
            IntentType.STUDY_ADVICE,
            (),
        ),
        (
            "Öğretmen çalışma önerisi söyledi.",
            IntentType.STUDY_ADVICE,
            (),
        ),
        (
            "Sınav sonuçları ne zaman açıklanacak?",
            IntentType.ASSESSMENT_ANALYSIS,
            (),
        ),
        (
            "Sınav puanı nedir?",
            IntentType.ASSESSMENT_ANALYSIS,
            (IntentType.KNOWLEDGE_QUESTION,),
        ),
        (
            "Deneme sonucu nerede yayınlanıyor?",
            IntentType.ASSESSMENT_ANALYSIS,
            (),
        ),
    ],
)
def test_explanatory_past_and_negative_phrases_do_not_create_intents(
    message: str,
    excluded_intent: IntentType,
    expected_intents: tuple[IntentType, ...],
) -> None:
    result = detect_intents(message)

    assert excluded_intent not in result.intents
    assert result.intents == expected_intents
