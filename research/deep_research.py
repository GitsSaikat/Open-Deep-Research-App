import asyncio
import aiohttp
import json
import nest_asyncio
nest_asyncio.apply()

# API Endpoints
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
SERPAPI_URL = "https://serpapi.com/search"
JINA_BASE_URL = "https://r.jina.ai/"

# Modify the default model selection
DEFAULT_MODEL = "google/gemini-2.0-flash-lite-preview-02-05:free"  # Gemini Flash 2.0 model identifier

# Helper class to hold extracted content along with its source URL
class SourcedContext:
    def __init__(self, text, source_url):
        self.text = text
        self.source_url = source_url

async def call_openrouter_async(session, messages, model=DEFAULT_MODEL):
    """
    Make an asynchronous request to the OpenRouter chat completion API with the given messages.
    Returns the assistant's reply text.
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://github.com/Pygen",  
        "X-Title": "Research Assistant",  
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 4096
    }
    
    try:
        async with session.post(OPENROUTER_URL, headers=headers, json=payload) as resp:
            if resp.status == 200:
                result = await resp.json()
                try:
                    return result['choices'][0]['message']['content']
                except (KeyError, IndexError) as e:
                    print("Unexpected response structure from OpenRouter:", result)
                    return None
            else:
                text = await resp.text()
                print(f"OpenRouter API error: {resp.status} - {text}")
                return None
    except Exception as e:
        print("Error during OpenRouter call:", e)
        return None

async def generate_search_queries_async(session, user_query):
    """
    Use the LLM to produce up to four clear search queries based on the user's topic.
    """
    prompt = (
        "You are a seasoned research assistant. Based on the user's topic, produce as many as four distinct and precise "
        "search queries that will help collect thorough information on the subject. "
        "Return a Python list of strings only, without any code formatting or backticks. "
        "For example: ['query1', 'query2', 'query3']"
    )
    messages = [
        {"role": "system", "content": "You are a precise and supportive research assistant."},
        {"role": "user", "content": f"User Topic: {user_query}\n\n{prompt}"}
    ]
    response = await call_openrouter_async(session, messages)
    if response:
        try:
            cleaned_response = response.strip()
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response.split("```")[1]
                if cleaned_response.startswith("python"):
                    cleaned_response = cleaned_response[6:]
            cleaned_response = cleaned_response.strip()
            
            search_queries = eval(cleaned_response)
            if isinstance(search_queries, list):
                return search_queries
            else:
                print("The LLM response is not a list. Response:", response)
                return []
        except Exception as e:
            print("Error interpreting search queries:", e, "\nResponse:", response)
            return []
    return []

# Modify perform_search_async function
async def perform_search_async(session, query, result_limit=5):
    """
    Make an asynchronous SERPAPI call to perform a Google search for the provided query.
    result_limit: Maximum number of search results to return
    """
    params = {
        "q": query,
        "api_key": SERPAPI_API_KEY,
        "engine": "google",
        "num": result_limit  # Add this parameter for limiting results
    }
    try:
        async with session.get(SERPAPI_URL, params=params) as resp:
            if resp.status == 200:
                results = await resp.json()
                if "organic_results" in results:
                    links = [item.get("link") for item in results["organic_results"] if "link" in item]
                    return links[:result_limit]  # Ensure we don't exceed the limit
                else:
                    print("No organic results found in SERPAPI response.")
                    return []
            else:
                text = await resp.text()
                print(f"SERPAPI error: {resp.status} - {text}")
                return []
    except Exception as e:
        print("Error during SERPAPI search:", e)
        return []

async def fetch_webpage_text_async(session, url):
    """
    Fetch the textual content of a webpage asynchronously using the Jina service.
    """
    full_url = f"{JINA_BASE_URL}{url}"
    headers = {
        "Authorization": f"Bearer {JINA_API_KEY}"
    }
    try:
        async with session.get(full_url, headers=headers) as resp:
            if resp.status == 200:
                return await resp.text()
            else:
                text = await resp.text()
                print(f"Jina fetch error for {url}: {resp.status} - {text}")
                return ""
    except Exception as e:
        print("Error retrieving webpage text with Jina:", e)
        return ""

async def is_page_useful_async(session, user_query, page_text):
    """
    Request the LLM to determine if the provided webpage content is pertinent to answering the user's topic.
    """
    prompt = (
        "You are a discerning evaluator of research. Given the user's topic and a snippet of webpage content, "
        "decide if the page contains valuable information to address the query. "
        "Reply strictly with one word: 'Yes' if the content is useful, or 'No' if it is not. Provide no extra text."
    )
    messages = [
        {"role": "system", "content": "You are a concise and strict research relevance evaluator."},
        {"role": "user", "content": f"User Topic: {user_query}\n\nWebpage Snippet (up to 20000 characters):\n{page_text[:20000]}\n\n{prompt}"}
    ]
    response = await call_openrouter_async(session, messages)
    if response:
        answer = response.strip()
        if answer in ["Yes", "No"]:
            return answer
        else:
            if "Yes" in answer:
                return "Yes"
            elif "No" in answer:
                return "No"
    return "No"

async def extract_relevant_context_async(session, user_query, search_query, page_text):
    """
    Derive and return the important details from the webpage text to address the user's topic.
    """
    prompt = (
        "You are an expert extractor of information. Given the user's topic, the search query that produced this page, "
        "and the webpage text, extract all pertinent details needed to answer the inquiry. "
        "Return only the relevant text without any additional commentary."
    )
    messages = [
        {"role": "system", "content": "You excel at summarizing and extracting relevant details."},
        {"role": "user", "content": f"User Topic: {user_query}\nSearch Query: {search_query}\n\nWebpage Snippet (up to 20000 characters):\n{page_text[:20000]}\n\n{prompt}"}
    ]
    response = await call_openrouter_async(session, messages)
    if response:
        return response.strip()
    return ""

async def get_new_search_queries_async(session, user_query, previous_search_queries, all_contexts):
    """
    Evaluate if additional search queries are necessary based on the current research progress.
    """
    context_combined = "\n".join(all_contexts)
    prompt = (
        "You are a systematic research planner. Taking into account the original topic, prior search queries, "
        "and the extracted information from webpages, determine if more research is required. "
        "If so, produce up to four new search queries as a Python list "
        "(for example: ['new query1', 'new query2']). If no further research is needed, reply with an empty string."
        "\nReturn only a Python list or an empty string without extra commentary."
    )
    messages = [
        {"role": "system", "content": "You are methodical in planning further research steps."},
        {"role": "user", "content": f"User Topic: {user_query}\nPrevious Queries: {previous_search_queries}\n\nCollected Context:\n{context_combined}\n\n{prompt}"}
    ]
    response = await call_openrouter_async(session, messages)
    if response:
        cleaned = response.strip()
        if cleaned == "":
            return ""
        try:
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("python"):
                    cleaned = cleaned[6:]
            cleaned = cleaned.strip()
            new_queries = eval(cleaned)
            if isinstance(new_queries, list):
                return new_queries
            else:
                print("LLM response is not a list for extra search queries. Response:", response)
                return []
        except Exception as e:
            print("Failed to parse additional search queries:", e, "\nResponse:", response)
            return []
    return []

async def generate_final_report_async(session, user_query, sourced_contexts):
    """
    Construct the ultimate detailed report including proper citations and references.
    """
    # Assign citation numbers to contexts based on source URL
    references = {}
    ref_number = 1
    formatted_contexts = []
    
    for ctx in sourced_contexts:
        if ctx.source_url not in references:
            references[ctx.source_url] = ref_number
            ref_number += 1
        formatted_contexts.append(f"{ctx.text} [{references[ctx.source_url]}]")
    
    context_combined = "\n".join(formatted_contexts)
    
    # Build the reference section
    reference_list = [f"[{num}] {url}" for url, num in sorted(references.items(), key=lambda x: x[1])]
    reference_section = "\n\nReferences:\n" + "\n".join(reference_list)
    
    prompt = (
        "You are a proficient academic report writer. Using the compiled contexts below and the original topic, "
        "compose a comprehensive, well-organized, and in-depth report that fully addresses the inquiry. "
        "Ensure that each piece of evidence is tagged with citation numbers in square brackets (e.g., [1], [2]). "
        "Maintain these tags in your final report to show the references. "
        "The style should be academic with proper in-text citations. Do not alter or add citation numbers."
    )
    
    messages = [
        {"role": "system", "content": "You are an expert academic report composer."},
        {"role": "user", "content": f"User Topic: {user_query}\n\nCollected Context:\n{context_combined}\n\n{prompt}"}
    ]
    
    report = await call_openrouter_async(session, messages)
    if report:
        return report + reference_section
    return "Error occurred while generating the report."

async def process_link(session, link, user_query, search_query):
    """
    Handle a single URL: fetch its content, assess its relevance, and if it qualifies, extract the associated context.
    Returns a SourcedContext object upon success, or None otherwise.
    """
    print(f"Retrieving content from: {link}")
    page_text = await fetch_webpage_text_async(session, link)
    if not page_text:
        return None
    usefulness = await is_page_useful_async(session, user_query, page_text)
    print(f"Relevance of {link}: {usefulness}")
    if usefulness == "Yes":
        context = await extract_relevant_context_async(session, user_query, search_query, page_text)
        if context:
            print(f"Context extracted from {link} (first 200 characters): {context[:200]}")
            return SourcedContext(context, link)
    return None

# Modify research_flow function to accept search_limit parameter
async def research_flow(user_query, iteration_limit, search_limit=5):
    """
    Primary research procedure intended for integration with Streamlit.
    search_limit: Maximum number of search results per query
    """
    sourced_contexts = []   
    all_search_queries = []  
    iteration = 0

    async with aiohttp.ClientSession() as session:
        new_search_queries = await generate_search_queries_async(session, user_query)
        if not new_search_queries:
            return "No search queries were generated by the LLM. Terminating process."
        all_search_queries.extend(new_search_queries)

        while iteration < iteration_limit:
            print(f"\n--- Iteration {iteration + 1} ---")
            iteration_contexts = []

            # Update to include search_limit
            search_tasks = [perform_search_async(session, query, search_limit) for query in new_search_queries]
            search_results = await asyncio.gather(*search_tasks)


            unique_links = {}
            for idx, links in enumerate(search_results):
                query = new_search_queries[idx]
                for link in links:
                    if link not in unique_links:
                        unique_links[link] = query

            print(f"Collected {len(unique_links)} distinct links in this iteration.")

            link_tasks = [
                process_link(session, link, user_query, unique_links[link])
                for link in unique_links
            ]
            link_results = await asyncio.gather(*link_tasks)

            for res in link_results:
                if res:
                    iteration_contexts.append(res)

            if iteration_contexts:
                sourced_contexts.extend(iteration_contexts)
            else:
                print("No relevant information was found in this iteration.")

            context_texts = [ctx.text for ctx in sourced_contexts]
            new_search_queries = await get_new_search_queries_async(
                session, user_query, all_search_queries, context_texts
            )
            
            if new_search_queries == "":
                print("LLM has determined that additional research is unnecessary.")
                break
            elif new_search_queries:
                print("LLM provided extra search queries:", new_search_queries)
                all_search_queries.extend(new_search_queries)
            else:
                print("LLM returned no further search queries. Concluding the loop.")
                break

            iteration += 1

        final_report = await generate_final_report_async(session, user_query, sourced_contexts)
        return final_report

def main():
    """
    CLI entry point for testing this research module.
    """
    user_query = input("Enter your research topic/question: ").strip()
    iter_limit_input = input("Enter the maximum number of iterations (default is 10): ").strip()
    iteration_limit = int(iter_limit_input) if iter_limit_input.isdigit() else 10
    
    final_report = asyncio.run(research_flow(user_query, iteration_limit))
    print("\n==== FINAL REPORT ====\n")
    print(final_report)

if __name__ == "__main__":
    main()
