from app.agent.chians import evaluator_chain


def evaluate_retrieved(question: str, raw_text: str) -> dict:
    return evaluator_chain.invoke(
        {
            "question": question,
            "raw_text": raw_text,
        }
    )

