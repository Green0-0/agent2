# Framework

## Agent Setup

**Toml File Configuration:**

ID, agent description, multiline system prompt, header, speculative viewing prompt, prompt wrapper

The header, speculative viewing prompt, and prompt wrapper are dynamically merged depending on whether or not chat turns must be injected in the middle.

**Agent Tree:**

Each agent holds its own task, children, and world (the files it accesses).

**Data Store / Rollout:**

Store the agent metadata + history into a json file within .agent/task/agent_id.

Specifically: session_id, agent_id, agent_parent, agent_children, date deployed, config_path, raw_chat, action_history. 

**Constructors:**

Classes which wrap functions that run before the agent loop begins, to setup the agent.

Example: Providers: Substitutes filler tokens in the text with actual values. Can also substitute with a sentence instead of a value by appending a *, ie: {{banned_tools_primary*}}.

Avaliable: {{os_info}}, {{date}}, {{full_dir_and_elements}}, {{full_dir}}, {{folders_dir}}, {{top_level_dir}}, {{avaliable_subagent_pipelines}}, {{avaliable_tools_primary}}, {{avaliable_tools_secondary}}, {{banned_tools_primary}}, {{banned_tools_secondary}, {{speculated_element_names}}, {{speculated_element_blocks}}, {{hint_element_names}} …

Example 2: Prefill-Providers: Similar to the provider, but instead works by directly modding the chat instead of substituting tokens.

**Hooks:**

Classes which wrap functions that run in the agent loop right after the LLM response is parsed to provide functionality. Each optionally return a string which is appended to the tool response or user message, and all returns are stacked together.

Example: Tool calls

**Primary + Secondary Tools + Subagent pipelines:**

The agent gets a persistent set of primary tools (search, view, delegate, tools, bash) and secondary tools (view_lines, open, edit … etc), where the secondary tools are routed via the tools tool (which lists tools when used). Connected subagent pipelines are also listed with delegate, and can be spawned with that tool. Certain tools may be disabled (and block execution) for certain agents.

**Architecture:**

Begin by loading the project (all accessible agent configs, files, cached embeddings, previous tasks) as a `Session` object. To pipeline, setup the `Agent` objects, each with the global session ID + personal task ID (so they can distinguish their own histories in file from others), and save them to the data file (updated live). Then run the agent loop async, wait for completion, and finish the pipeline as necessary. Note that pipelines are coded in script instead of configured, this is because building a pipeline via graph will be too complicated for a standard UI. The session has both commit options and re-read options for saving changes and loading new changes.

## Code Retrieval

Note that cache reads are free and cache writes are expensive. We want to maximize the reward, the number of tokens we get as reads instead of writes. This is done via retrieving relevant code elements before running the agent and prepending them to our prompt. For reference, we have our previous prompts along with the code elements we viewed. There are four possible outcomes:

1. Useful cache read: immediate reward equal to the number of tokens read.
2. Useful cache writes: potential future rewards on new cache hits. No immediate reward. Possible cache eviction locally, but this is not within the scope of this problem.
3. Useless cache read: Minor context bloat, otherwise no reward or loss.
4. Useless cache write: immediate loss equal to the number of tokens read, potential future reward on new cache hits.

**Similarity Function (Weight as needed):**

BM25: Likely good for prompts, terrible for code

Qwen3 Embedding: Probably decent for code

Qwen3 Reranker: Expensive, requires embedding, would need to convert rankings to values

**Scoring Function:**

Let sim_p be the similarity against a previously executed prompt, and sim_c be the similarity between the prompt and code element. 

Define the nested relation for a code element as:

R = sim_c * ∑ for i over p (sim_pi) / normalization factor

Where the normalization factor brings it to a range from 0 … 1. The range is not evenly distributed, and code elements unseen by any prompt are scored with 0 (since sim_pi is 0).

We can also consider linear functions instead of multiplicative ones, where R is a weighted average between ∑sim_pi and sim_c

**Prefix Cache Tree Builder:**

Assuming that the fixed prefix (the system prompt + the part of the prompt above the inserted elements) is static, our prefix takes the form of a tree where each element is a node. The prefix must be retrieved from the top of the tree downwards, but we can stop at any point midway. We build the tree according to the four possible outcomes listed above. We can also attempt to track separate statistics to predict the future reward.

# TBA:
- Tree-sitter elements
- Repomap
- Agent pipeline composition: Use an abstract pipeline that gets implemented for specific pipeline types