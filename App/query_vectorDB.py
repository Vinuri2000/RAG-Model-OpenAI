from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import Chroma
import os
from dotenv import load_dotenv

# Load env files
load_dotenv()
similarity_search_index = int(os.getenv("similarity_search_index"))
chorma_DB_path = os.getenv("CHROMA_DB_PATH")
similarity_margin_value = float(os.getenv("SIMILARITY_MARGIN_VALUE"))


# Vector Embedding the question and performing the similarity search and get the top most results
def query_database(question: str):
    db = Chroma(
        persist_directory = chorma_DB_path,
        embedding_function = OpenAIEmbeddings()
    )
    search_results = db.similarity_search_with_relevance_scores(question, similarity_search_index)
    filtered_results = [res for res in search_results if res[1] > similarity_margin_value]
    print("\n\n",search_results)
    print("\n\n",filtered_results)
    return filtered_results

# Query using the LLM
def query_question(question: str) -> str:
    print("Question is", question)
    results = query_database(question)
    if not results:
        return "No relevant information found in documents. Try another question."

    context_text = "\n\n---\n\n".join([doc.page_content for doc, _ in results])
    prompt = f"""
You are a helpful internal analytics assistant specialized in Finance and Project Management.
Answer the given question using only the provided context. And only answer the relevant question.

Context:
{context_text}

Question:
{question}
"""
    llm = ChatOpenAI(model="gpt-4o-mini")
    response = llm.invoke(prompt)
    answer_text = response.content
    sources_text = format_sources(results)
    return f"{answer_text}\n\n📂 Sources Utilized:\n{sources_text}"


# -Format Sources to show in the output
def format_sources(search_results):
    sources = [
        os.path.basename(doc.metadata.get("source", ""))
        for doc, _ in search_results
        if doc.metadata.get("source")
    ]
    unique_sources = list(dict.fromkeys(sources))
    return "\n".join([f"    • {s}" for s in unique_sources]) if unique_sources else "No sources available"
