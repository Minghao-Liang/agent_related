package builtin

const QueryWriterInstructions = `Your goal is to generate sophisticated and diverse web search queries. These queries are intended for an advanced automated web research tool capable of analyzing complex results, following links, and synthesizing information.

Instructions:
- Always prefer a single search query, only add another query if the original question requests multiple aspects or elements and one query is not enough.
- Each query should focus on one specific aspect of the original question.
- Don't produce more than {number_queries} queries.
- Queries should be diverse, if the topic is broad, generate more than 1 query.
- Don't generate multiple similar queries, 1 is enough.
- Query should ensure that the most current information is gathered. The current date is {current_date}.

Format: 
- Format your response as a JSON object with ALL two of these exact keys:
   - "rationale": Brief explanation of why these queries are relevant
   - "query": A list of search queries

Example:

Topic: What revenue grew more last year apple stock or the number of people buying an iphone
` + "```json" + `
{
    "rationale": "To answer this comparative growth question accurately, we need specific data points on Apple's stock performance and iPhone sales metrics. These queries target the precise financial information needed: company revenue trends, product-specific unit sales figures, and stock price movement over the same fiscal period for direct comparison.",
    "query": ["Apple total revenue growth fiscal year 2024", "iPhone unit sales growth fiscal year 2024", "Apple stock price growth fiscal year 2024"],
}
` + "```" + `

Context: {research_topic}`

const WebSearcherInstructions = `You are given the top search results (title, URL, snippet) from a single query about "{research_topic}". Your task is to synthesize these results into a verifiable research note.

Constraints:
- You MUST use only the provided search results as evidence. Do not assume you can browse the web, follow links, or run additional searches.
- Do not introduce facts that are not supported by the provided snippets.
- If the snippets are insufficient or conflicting, say so explicitly and state what is missing.
- The current date is {current_date}. Prioritize recency only when it is evidenced by the snippets.

Output Requirements:
- Write a concise summary with 3–7 key findings.
- Every key finding must include an inline citation placeholder in the form ([1]), ([2]), etc., corresponding to the provided Source numbers.
- Add a short "Gaps" section listing 1–3 concrete missing pieces of information that would require another query.

Research Topic:
{research_topic}
`

const ReflectionInstructions = `You are an expert research assistant analyzing summaries about "{research_topic}".

Instructions:
- Identify knowledge gaps or areas that need deeper exploration and generate a follow-up query. (1 or multiple).
- If provided summaries are sufficient to answer the user's question, don't generate a follow-up query.
- If there is a knowledge gap, generate a follow-up query that would help expand your understanding.
- Focus on technical details, implementation specifics, or emerging trends that weren't fully covered.

Requirements:
- Ensure the follow-up query is self-contained and includes necessary context for web search.

Output Format:
- Format your response as a JSON object with these exact keys:
   - "is_sufficient": true or false
   - "knowledge_gap": Describe what information is missing or needs clarification
   - "follow_up_queries": Write a specific question to address this gap

Example:
` + "```json" + `
{
    "is_sufficient": true, // or false
    "knowledge_gap": "The summary lacks information about performance metrics and benchmarks", // "" if is_sufficient is true
    "follow_up_queries": ["What are typical performance benchmarks and metrics used to evaluate [specific technology]?"] // [] if is_sufficient is true
}
` + "```" + `

Reflect carefully on the Summaries to identify knowledge gaps and produce a follow-up query. Then, produce your output following this JSON format:

Summaries:
{summaries}
`

const AnswerInstructions = `Generate a high-quality answer to the user's question based on the provided summaries.

Instructions:
- The current date is {current_date}.
- You are the final step of a multi-step research process, don't mention that you are the final step. 
- You have access to all the information gathered from the previous steps.
- You have access to the user's question.
- Generate a high-quality answer to the user's question based on the provided summaries and the user's question.
- Include sources for every key claim using citation placeholders in the form ([1]), ([2]), etc., as they appear in the provided summaries. Do not attempt to format URLs yourself; citation placeholders will be rendered into markdown links later. THIS IS A MUST.

User Context:
- {research_topic}

Summaries:
{summaries}`
