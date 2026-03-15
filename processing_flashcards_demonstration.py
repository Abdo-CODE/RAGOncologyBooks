import re

text = """Alkylating agents are a class of anti-cancer agents that represent the oldest class of anti-tumor agents. They are active or latent nitrogen mustards that work by forming covalent bonds with DNA, thereby inhibiting DNA replication and leading to cell death.

Here are 5 flashcards based on the answer:

Q: What is the primary mechanism of action of alkylating agents?
A: Forming covalent bonds with DNA, inhibiting DNA replication, and leading to cell death.

Q: What type of alkylating agents are active or latent nitrogen mustards?
A: Nitrogen mustards.

Q: What is the result of the reaction between alkylating agents and DNA?
A: Inhibition of DNA replication.

Q: What is the end effect of alkylating agents on DNA?
A: Cell death.

Q: Are alkylating agents specific in their action, or do they affect normal and tumor cells?
A: They are non-specific in their action, and can affect both normal and tumor cells."""

pattern = re.compile(
    r"Q:\s*(.*?)\s*A:\s*(.*?)(?=\n\s*Q:|\Z)",
    re.IGNORECASE | re.DOTALL,
)

flashcards = []
for m in pattern.finditer(text):
    question = " ".join(m.group(1).split())
    answer = " ".join(m.group(2).split())
    if question and answer:
        flashcards.append((question, answer))

print(f"Extracted {len(flashcards)} flashcards")
for (q, a) in (flashcards):
    print(f" Q: {q}\n   A: {a}\n")