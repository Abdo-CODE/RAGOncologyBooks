import logging 
import inngest
from fastapi import FastAPI
from pydantic import BaseModel
import osimport logging 
import inngest
from fastapi import FastAPI
from pydantic import BaseModel
import os
import inngest.fast_api
from dotenv import load_dotenv
import uuid
from inngest.experimental  import ai 
import datetime 

from data_loader import load_and_chunk_pdf, embed_texts
from vector_db import QdrantStorage

from custom_types import RAGChunkandSrc, RAGUpsertResult, RAGSearchResult, RAGQueryResult
from openai import OpenAI
import genanki
import re 


load_dotenv()

inngest_client = inngest.Inngest(
    app_id="rag_app",
    logger=logging.getLogger("uvicorn"),
    is_production=False,
)

@inngest_client.create_function(fn_id="RAG :Ingest PDF",
                                 trigger=inngest.TriggerEvent(event="rag/ingest_pdf"))


async def rag_ingest_pdf(ctx:inngest.Context):
    def _load(ctx: inngest.Context) -> RAGChunkandSrc:
      pdf_path=ctx.event.data["pdf_path"]
      source_id=ctx.event.data.get("source_id",pdf_path)
      chunks= load_and_chunk_pdf(pdf_path)
      return RAGChunkandSrc(chunks=chunks,source_id=source_id).model_dump() ## converts it to json serializable dict





    def _upsert(data: RAGChunkandSrc) -> RAGUpsertResult:
      chunks=data["chunks"]
      source_id=data["source_id"]
      vecs=embed_texts(chunks)
      ids=[str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{i}")) for i in range(len(chunks))]
      payloads= [{"source":source_id, "text":chunks[i]} for i in range(len(chunks))]
      QdrantStorage().upsert(ids,vecs,payloads)
      return RAGUpsertResult(ingested=len(chunks)).model_dump() ## converts it to json serializable dict





    chunk_and_src = await ctx.step.run(" load and chunk pdf",lambda : _load(ctx), output_type=RAGChunkandSrc)

    ingested= await ctx.step.run("embed and upsert",lambda : _upsert(chunk_and_src),
                                 output_type=RAGUpsertResult)
    return ingested ## converts it to json serializable dict

def search_contexts(question:str, top_k:int =5):
    query_vec=embed_texts([question])[0]
    store=QdrantStorage()
    found=store.search(query_vec,top_k)
    return RAGSearchResult(contexts=found["contexts"],sources=found["sources"]).model_dump()


@inngest_client.create_function(fn_id="RAG :Query_PDF",
                                 trigger=inngest.TriggerEvent(event="rag/query_pdf_ai"))

async def rag_query_pdf_ai(ctx: inngest.Context):
 ## converts it to json serializable dict
   question=ctx.event.data["question"]
   top_k=int(ctx.event.data.get("top_k",5))
   
   found = await ctx.step.run("embed-and-search",lambda: search_contexts(question,top_k),output_type=RAGSearchResult)
   
   
   
   context_block = "\n\n".join(f"- {c}" for c in found["contexts"])
   user_content = (
       "Answer the following question using only the provided context. If the context does not contain the answer, say you don't know.\n\n"
       f"Context:\n{context_block}\n\n"
       f"Question: {question}"
   )

   client = OpenAI(
       api_key=os.getenv("GROQ_API_KEY"),
       base_url="https://api.groq.com/openai/v1"
   )

   def _ask_llm():
       response = client.chat.completions.create(
           model="llama-3.1-8b-instant",
           messages=[
               {"role": "system", "content": "You are an assistant for answering questions based on provided context. If the context does not contain the answer, say you don't know."},
               {"role": "user", "content": user_content}
           ]
       )
       return {"answer": response.choices[0].message.content.strip(), "sources": found["sources"], "num_contexts": len(found["contexts"])}

   result = await ctx.step.run("llm answer", _ask_llm)
   return result
 
@inngest_client.create_function(fn_id="RAG :Query_and Create_Flashcard",
                                 trigger=inngest.TriggerEvent(event="rag/query_and_create_flashcard"))

async def rag_query_and_create_flashcard(ctx: inngest.Context):
  question = ctx.event.data["question"]
  top_k = int(ctx.event.data.get("top_k", 5))
  number_of_flashcards = int(ctx.event.data.get("num_flashcards", 3))
  found = await ctx.step.run("embed-and-search", lambda: search_contexts(question, top_k), output_type=RAGSearchResult)
  context_block = "\n\n".join(f"- {c}" for c in found["contexts"])
  flashcard_rules = (
    "Flashcard rules (strict):\n"
    "1) One card = one fact/concept.\n"
    "2) Each question must have exactly one correct answer.\n"
    "3) No list/enumeration questions.\n"
    "4) No yes/no questions.\n"
    "5) Do not ask for examples; use concept-recognition style questions.\n"
    "6) Each card must be understandable on its own.\n"
    "7) Keep answers short (prefer under 20 words).\n"
    "8) Split multi-fact information into multiple cards.\n"
    "9) Include at least one concept-definition card for key terms.\n"
    "10) Rewrite content clearly; do not copy source text verbatim.\n"
  )
  user_content = (
    f"{flashcard_rules}\n"
    f"Create up to {number_of_flashcards} flashcards from the context.\n\n"
    "Output format (mandatory):\n"
    "Q: <question>\n"
    "A: <answer>\n\n"
    "Do NOT add headings, numbering, bullets, markdown, or explanations.\n"
    "Only output Q/A pairs.\n\n"
    f"Context:\n{context_block}\n\n"
    f"Topic: {question}"
  )
  client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1")

  def _ask_llm_for_flashcards():
    response = client.chat.completions.create(
      model="llama-3.1-8b-instant",
      messages=[
        {"role": "system", "content": "You are an assistant for answering questions based on provided context and creating flashcards. If the context does not contain the answer, say you don't know."},
        {"role": "user", "content": user_content}
      ]
    )
    return response.choices[0].message.content.strip()
  def _ask_llm_for_flashcards_title():
    title_prompt = (
        "Create a deck title from this topic.\n"
        "Rules: max 2 words, letters/numbers/underscore only.\n"
        "Return title only.\n"
        f"Topic: {question}")
    response = client.chat.completions.create(
      model="llama-3.1-8b-instant",
      messages=[
        {"role": "system", "content": "You are an assistant for  creating titles , create a title for the flashcard set based on the question. THE TITLE SHOULD ONLY BE TWO WORDS WITH _ seperator only IF NEEDED. If you can't create a title based on the question, just return 'My Flashcards' as the title."},
        {"role": "user", "content": title_prompt}
      ]
    )
    return response.choices[0].message.content.strip()

  llm_output = await ctx.step.run("llm answer and create flashcards", _ask_llm_for_flashcards)
  deck_name = await ctx.step.run("llm create flashcard title", _ask_llm_for_flashcards_title)
  pattern = re.compile(
    r"Q:\s*(.*?)\s*A:\s*(.*?)(?=\n\s*Q:|\Z)",
    re.IGNORECASE | re.DOTALL,
  )

  flashcards = []
  for m in pattern.finditer(llm_output):
    question = " ".join(m.group(1).split())
    answer = " ".join(m.group(2).split())
    if question and answer:
      flashcards.append((question, answer))

  deck_id = uuid.uuid4()
  #deck_suffix = str(deck_id)[:8]
  deck_id = deck_id.int % (2**63 - 1)
  if deck_id == 0:
    deck_id = 1
  my_deck = genanki.Deck(deck_id, f'My Deck_{deck_name}')

  my_model = genanki.Model(
    1607392319,
    'Simple Model',
    fields=[
      {'name': 'Question'},
      {'name': 'Answer'},
    ],
    templates=[
      {
        'name': 'Card 1',
        'qfmt': '{{Question}}',
        'afmt': '{{FrontSide}}<hr id="answer">{{Answer}}',
      },
    ])

  for question_text, answer_text in flashcards:
    my_note = genanki.Note(model=my_model, fields=[question_text, answer_text])
    my_deck.add_note(my_note)

  deck_file = f"output_{deck_name}.apkg"
  genanki.Package(my_deck).write_to_file(deck_file)
  return {"flashcards_created": len(flashcards), "deck_file": deck_file, "llm_output": llm_output, "sources": found["sources"]}

    
   
   







app=FastAPI()

inngest.fast_api.serve(app, inngest_client,[rag_ingest_pdf,rag_query_pdf_ai,rag_query_and_create_flashcard])
import inngest.fast_api
from dotenv import load_dotenv
import uuid
from inngest.experimental  import ai 
import datetime 

from data_loader import load_and_chunk_pdf, embed_texts
from vector_db import QdrantStorage

from custom_types import RAGChunkandSrc, RAGUpsertResult, RAGSearchResult, RAGQueryResult
from openai import OpenAI
import genanki
import re 


load_dotenv()

inngest_client = inngest.Inngest(
    app_id="rag_app",
    logger=logging.getLogger("uvicorn"),
    is_production=False,
)

@inngest_client.create_function(fn_id="RAG :Ingest PDF",
                                 trigger=inngest.TriggerEvent(event="rag/ingest_pdf"))


async def rag_ingest_pdf(ctx:inngest.Context):
    def _load(ctx: inngest.Context) -> RAGChunkandSrc:
      pdf_path=ctx.event.data["pdf_path"]
      source_id=ctx.event.data.get("source_id",pdf_path)
      chunks= load_and_chunk_pdf(pdf_path)
      return RAGChunkandSrc(chunks=chunks,source_id=source_id).model_dump() ## converts it to json serializable dict





    def _upsert(data: RAGChunkandSrc) -> RAGUpsertResult:
      chunks=data["chunks"]
      source_id=data["source_id"]
      vecs=embed_texts(chunks)
      ids=[str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{i}")) for i in range(len(chunks))]
      payloads= [{"source":source_id, "text":chunks[i]} for i in range(len(chunks))]
      QdrantStorage().upsert(ids,vecs,payloads)
      return RAGUpsertResult(ingested=len(chunks)).model_dump() ## converts it to json serializable dict





    chunk_and_src = await ctx.step.run(" load and chunk pdf",lambda : _load(ctx), output_type=RAGChunkandSrc)

    ingested= await ctx.step.run("embed and upsert",lambda : _upsert(chunk_and_src),
                                 output_type=RAGUpsertResult)
    return ingested ## converts it to json serializable dict

def search_contexts(question:str, top_k:int =5):
    query_vec=embed_texts([question])[0]
    store=QdrantStorage()
    found=store.search(query_vec,top_k)
    return RAGSearchResult(contexts=found["contexts"],sources=found["sources"]).model_dump()


@inngest_client.create_function(fn_id="RAG :Query_PDF",
                                 trigger=inngest.TriggerEvent(event="rag/query_pdf_ai"))

async def rag_query_pdf_ai(ctx: inngest.Context):
 ## converts it to json serializable dict
   question=ctx.event.data["question"]
   top_k=int(ctx.event.data.get("top_k",5))
   
   found = await ctx.step.run("embed-and-search",lambda: search_contexts(question,top_k),output_type=RAGSearchResult)
   
   
   
   context_block = "\n\n".join(f"- {c}" for c in found["contexts"])
   flashcard_rules = (
    "Flashcard rules (strict):\n"
    "1) One card = one fact/concept.\n"
    "2) Each question must have exactly one correct answer.\n"
    "3) No list/enumeration questions.\n"
    "4) No yes/no questions.\n"
    "5) Do not ask for examples; use concept-recognition style questions.\n"
    "6) Each card must be understandable on its own.\n"
    "7) Keep answers short (prefer under 20 words).\n"
    "8) Split multi-fact information into multiple cards.\n"
    "9) Include at least one concept-definition card for key terms.\n"
    "10) Rewrite content clearly; do not copy source text verbatim.\n"
  )
   user_content = (
    f"{flashcard_rules}\n"
    f"Create up to {number_of_flashcards} flashcards from the context.\n\n"
    "Output format (mandatory):\n"
    "Q: <question>\n"
    "A: <answer>\n\n"
    "Do NOT add headings, numbering, bullets, markdown, or explanations.\n"
    "Only output Q/A pairs.\n\n"
    f"Context:\n{context_block}\n\n"
    f"Topic: {question}"
  )
   
   client = OpenAI(
       api_key=os.getenv("GROQ_API_KEY"),
       base_url="https://api.groq.com/openai/v1"
   )
   
   def _ask_llm():
       response = client.chat.completions.create(
           model="llama-3.1-8b-instant",
           messages=[
               {"role": "system", "content": "You are an assistant for answering questions based on provided context. If the context does not contain the answer, say you don't know."},
               {"role": "user", "content": user_content}
           ]
       )
       return {"answer": response.choices[0].message.content.strip(), "sources": found["sources"], "num_contexts": len(found["contexts"])}
   
   result = await ctx.step.run("llm answer", _ask_llm)
   return result
 
@inngest_client.create_function(fn_id="RAG :Query_and Create_Flashcard",
                                 trigger=inngest.TriggerEvent(event="rag/query_and_create_flashcard"))

async def rag_query_and_create_flashcard(ctx: inngest.Context):
  question = ctx.event.data["question"]
  top_k = int(ctx.event.data.get("top_k", 5))
  number_of_flashcards = int(ctx.event.data.get("num_flashcards", 3))
  found = await ctx.step.run("embed-and-search", lambda: search_contexts(question, top_k), output_type=RAGSearchResult)
  context_block = "\n\n".join(f"- {c}" for c in found["contexts"])
  user_content = (
    "Use the following context to answer the question.\n\n"
    f"Context:\n{context_block}\n\n"
    f"Question: {question}\n"
    f"Answer concisely using the context above. Then create flashcards in the format 'Q: question? A: answer.' based on the answer. Create up to {number_of_flashcards} flashcards."
  )
  client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1")

  def _ask_llm_for_flashcards():
    response = client.chat.completions.create(
      model="llama-3.1-8b-instant",
      messages=[
        {"role": "system", "content": "You are an assistant for answering questions based on provided context and creating flashcards. If the context does not contain the answer, say you don't know."},
        {"role": "user", "content": user_content}
      ]
    )
    return response.choices[0].message.content.strip()
  def _ask_llm_for_flashcards_title():
    title_prompt = (
        "Create a deck title from this topic.\n"
        "Rules: max 2 words, letters/numbers/underscore only.\n"
        "Return title only.\n"
        f"Topic: {question}")
    response = client.chat.completions.create(
      model="llama-3.1-8b-instant",
      messages=[
        {"role": "system", "content": "You are an assistant for  creating titles , create a title for the flashcard set based on the question. THE TITLE SHOULD ONLY BE TWO WORDS WITH _ seperator only IF NEEDED. If you can't create a title based on the question, just return 'My Flashcards' as the title."},
        {"role": "user", "content": title_prompt}
      ]
    )
    return response.choices[0].message.content.strip()

  llm_output = await ctx.step.run("llm answer and create flashcards", _ask_llm_for_flashcards)
  deck_name = await ctx.step.run("llm create flashcard title", _ask_llm_for_flashcards_title)
  pattern = re.compile(
    r"Q:\s*(.*?)\s*A:\s*(.*?)(?=\n\s*Q:|\Z)",
    re.IGNORECASE | re.DOTALL,
  )

  flashcards = []
  for m in pattern.finditer(llm_output):
    question = " ".join(m.group(1).split())
    answer = " ".join(m.group(2).split())
    if question and answer:
      flashcards.append((question, answer))

  deck_id = uuid.uuid4()
  #deck_suffix = str(deck_id)[:8]
  deck_id = deck_id.int % (2**63 - 1)
  if deck_id == 0:
    deck_id = 1
  my_deck = genanki.Deck(deck_id, f'My Deck_{deck_name}')

  my_model = genanki.Model(
    1607392319,
    'Simple Model',
    fields=[
      {'name': 'Question'},
      {'name': 'Answer'},
    ],
    templates=[
      {
        'name': 'Card 1',
        'qfmt': '{{Question}}',
        'afmt': '{{FrontSide}}<hr id="answer">{{Answer}}',
      },
    ])

  for question_text, answer_text in flashcards:
    my_note = genanki.Note(model=my_model, fields=[question_text, answer_text])
    my_deck.add_note(my_note)

  deck_file = f"output_{deck_name}.apkg"
  genanki.Package(my_deck).write_to_file(deck_file)
  return {"flashcards_created": len(flashcards), "deck_file": deck_file, "llm_output": llm_output, "sources": found["sources"]}

    
   
   







app=FastAPI()

inngest.fast_api.serve(app, inngest_client,[rag_ingest_pdf,rag_query_pdf_ai,rag_query_and_create_flashcard])