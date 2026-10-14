# Framework

## Runtime Layout

**Project Folder:**

The project folder is the codebase being operated on. It owns the live files and the rollout directory. The default rollout directory is `.agent2/task` inside this folder.

**Agent2 Folder:**

The agent2 repository owns the agent configuration directory. The default is `config/agents` relative to the agent2 folder, not relative to the project folder.

**Paths:**

Files are addressed by POSIX-style paths relative to the project folder. Agent configs are addressed by paths relative to the agent2 folder. Configs do not have separate IDs. Rollouts have IDs and are stored as `{rollout_id}.json`.

## Session

**Purpose:**

The `Session` is the shared live view of the project. It loads the available agent configs, persisted rollouts, and current disk files. It does not own agent edits.

The session stores:

- `configs`: Config path to `AgentConfig`.
- `datastore`: Rollout ID to `Rollout`.
- `files`: Project-relative path to the current disk-backed `File` or `CodeFile`.

**File Refreshing:**

The session scans the project folder and reloads additions, modifications, and deletions. Hidden paths, adapter-specific ignored folders, and ignored extensions are excluded.

Unchanged files retain their existing objects. Changed parsed files are incrementally reparsed by finding their unchanged left and right regions and expressing the changed middle as one `FileEdit`. If incremental parsing fails, the file is rebuilt. Generic files update their `CodeState` directly.

The default tool-call hook refreshes the session before every tool call. A single tool operation may assume that disk contents remain stable while it runs.

**Rollout Storage:**

Each rollout contains `config_path`, `id`, `date_deployed`, `parent`, `children`, `raw_chat`, and `action_history`. Registering a child updates the parent rollout. Saving writes the rollout JSON into the project-local rollout directory.

The current agent loop fills `raw_chat`. `action_history` is part of the persisted shape but is not currently populated by the default hook.

## Workspace

**Overlay:**

A `Workspace` is an agent-visible filesystem overlay on top of the session. It stores only files that have been written, deleted, or checked out for editing. Unmodified files are read directly from the session, so parallel workspaces do not duplicate the entire codebase in memory.

`read_file` first checks the workspace and then falls through to the session. `paths` combines session paths with workspace additions and removes workspace deletions. A deleted file is represented by a checked-out file whose `current_state` is `None`.

**Checkout Through Mutation:**

There is no public checkout operation. Reading does not copy a file. Writing or applying an edit checks out the file when necessary and records the session state as its `original_state`. Parsed checkouts copy the Tree-sitter tree while sharing immutable code states and nodes until an edit rebuilds them. A newly created file has no original state.

**Shared and Isolated Work:**

Agents which receive the same workspace see each other's edits immediately. An agent which receives a cloned workspace gets a separate copy of the existing overlay. This naturally permits unified and disjoint agent groups in the same pipeline without a global workspace policy.

A clone does not follow later edits from the workspace it was cloned from. Files which were never checked out still fall through to the live session.

`diff` returns one `(path, unified_diff)` tuple per changed file, sorted by path. Callers decide how to group or display those per-file diffs.

**Commit:**

Committing first refreshes the session from disk. Every changed workspace file is compared against its original content and the current session content. If the live content is neither the original nor already equal to the workspace result, the workspace is stale and the commit fails with a conflict.

Successful commits write creations and replacements, unlink deletions, refresh the session, and clear the overlay. Stale work is not automatically rebased or merged. There is no file locking; consistency is enforced through optimistic conflict detection.

Pipelines do not commit automatically. The pipeline or its caller decides when a workspace is committed.

## Files and Code Parsing

**CodeState:**

`CodeState` is an immutable byte snapshot with total byte length and precomputed line-start offsets. It supplies the byte range for a 1-indexed line and is the coordinate source for viewing and editing.

**File:**

A generic `File` holds a path, an `original_state`, and a `current_state`. It has no parsed structure.

**CodeFile:**

A `CodeFile` is a `File` with a language adapter, a Tree-sitter tree, and indexed `CodeNode` objects. It reparses after edits and passes an edited old tree back to Tree-sitter for incremental parsing.

Whole-file writes to existing files are reduced to one changed middle range. Both whole-file and targeted workspace edits use `tree.edit` and incremental reparse. Only new code files require an initial full parse.

**CodeNode:**

A code node stores its full, signature, docstring, and body byte ranges, along with its parent path and children. Its stable lookup path is structural, such as `MyClass.my_method`. Its LLM display path adds the 1-indexed starting line, such as `MyClass.my_method.42`.

Both forms index the same node in a `CodeFile`.

**Language Adapters:**

Adapters define supported extensions, ignored paths, parsing, node extraction, and formatting repair. Python is currently the only registered adapter and supports `.py` and `.pyi`. It extracts functions, classes, decorated definitions, nesting, signatures, bodies, and leading docstrings.

The project declares Tree-sitter packages for additional languages, but those languages are not active until their adapters are registered.

## Agent Setup

**TOML File Configuration:**

An `AgentConfig` contains its injected config path; subagent name and description; model, optional API base URL, and optional API-key environment variable; system prompt; optional top prompt wrapper; optional speculative middle prompt; required bottom and followup prompt wrappers; maximum step count; lists of constructor, hook, primary-tool, and secondary-tool names; a workspace policy; and the configured subagent names it may delegate to. TOML arrays map directly to the component and subagent lists.

The delegated agent's `workspace_policy` controls its relationship to its parent. `isolated` creates a fresh workspace over the session, `clone` copies the parent's current overlay and then diverges, and `shared` uses the same workspace object. Since the policy belongs to the child config, one parent may create shared, cloned, and isolated branches by delegating to different configured agents.

`globals.py` is the component registry. `TOOLS` maps tool names to `Tool` wrappers, while `CONSTRUCTORS` and `HOOKS` map configured names to zero-argument factories. Built-in provider constructors use the tokens `{{DATE}}`, `{{FILES}}`, and `{{OS}}`, with `*` variants selecting their full descriptive format.

**Agent:**

Each `Agent` owns one rollout, one workspace reference, one config, an LLM client, resolved constructors, hooks, primary tools, secondary tools, one optional pending continuation, and asynchronous inbox/outbox queues. Primary tools are immediately exposed to the model. Secondary tools are resolved but remain inactive until the secondary-tool activation mechanism is implemented.

The agent generates its rollout ID when no explicit ID is supplied. Parent IDs belong to agent creation by the delegation runtime, not normal pipeline configuration. Parent and child IDs describe rollout relationships; they do not imply workspace sharing or commit ancestry.

Inbox and inter-agent message content is string-only. Inbox strings are joined and inserted as one user message, or appended to the final user message when one already exists. Chat dictionaries remain internal to `raw_chat`; callers cannot inject system, assistant, or tool roles through the inbox. Ordinary inbox messages wait while a continuation owns the next model response. `stop()` uses a private control sentinel, so the literal text `STOP` remains ordinary user content.

**Constructors:**

Constructors modify chat state during initial setup and followups.

The default constructor accepts its prompt-token key, which is `PROMPT` in the global registry. It inserts the configured system prompt, then builds the initial user message from `prompt_wrap_top + prompt_wrap_bottom` and replaces that token. Followups replace the same token in `followup_prompt_wrapper` instead of repeating the initial wrapper. `spec_prompt_middle` is stored but currently ignored because speculative viewing is unsupported.

Optional constructors can substitute the current date, operating-system information, or workspace path listing into configured tokens. Each provider replaces both the lightweight `{{KEY}}` and full-sentence `{{KEY*}}` forms in the same pass.

**Hooks:**

Hooks run after each LLM response and return an optional `HookResult`. Its `output` is stacked with other hook output and appended to the latest tool/user message or inserted as a new user message. Its `consumed` flag means the response was handled and the agent loop must continue rather than treating it as a final answer. Consumption controls the loop and does not imply chat-history deletion.

The default `ToolCallHook` routes a response to the agent's pending continuation before ordinary tool-call processing. Otherwise it refreshes session files, parses tool arguments, injects runtime-only arguments such as `agent`, `session`, and `agentconfig`, executes the selected tool, and appends an OpenAI-format tool response. Tool and continuation exceptions become hook or tool response text rather than escaping the agent loop.

**Tools:**

`Tool` wraps a Python function and builds an OpenAI function schema from its signature and docstring. Runtime-only parameters are omitted from the public schema. Required parameters are inferred from missing defaults, and examples are parsed from `Task:` / `Tool Call:` docstring blocks.

A tool normally returns response content. It may instead return `(content, continuation)`, where the continuation is a callable which receives the next assistant message. The callable can access its originating agent through its closure, may manage chat history itself, and may return another `(content, continuation)` pair to form a chain. Only one continuation may be bound per agent; if one assistant response creates several, all are rejected and none are bound.

## Agent Loop

The agent loop takes its maximum number of steps from `AgentConfig.max_steps`.

1. Honor the private stop sentinel. If no continuation is pending, join queued inbox strings into one user message; otherwise defer them.
2. Send the current chat, model, and tool schemas to an OpenAI-compatible chat-completions client.
3. Append the assistant message to `raw_chat`.
4. Run each hook, collect its `HookResult`, and append any stacked hook output.
5. Save the rollout.
6. Continue when a hook consumed the response. Otherwise return normal assistant content; an unconsumed tool call is an error.

Exceeding the step limit raises an error.

## Pipeline Composition

**Pipeline:**

`Pipeline` is an abstract runtime with pipeline-local maps of active agents and their lifecycle tasks. Its shared utilities register and start agents, spawn configured children, transfer messages, cancel branches, persist completed rollouts, and unregister agents during cleanup. A registered agent keeps a reference to the pipeline so delegation tools can use that runtime.

Message routing is a local target lookup. A target absent from that pipeline is ignored, so independent pipelines are naturally isolated without ownership checks or a global message bus. Delivered messages are plain user-content strings labeled with the sender's configured name and rollout ID.

**SingleAgentPipeline:**

The implemented pipeline accepts only a config path and prompt. It creates a fresh workspace over the supplied session, then creates an agent which resolves its model client, step limit, constructors, hooks, and tools from its config. The agent generates the rollout ID. `run` returns a `PipelineResult` containing the final answer, rollout ID, and workspace, without retaining duplicate mutable output fields on the pipeline.

The pipeline starts its root through the base lifecycle watcher. A final response completes an agent only when it has no active direct children and no already-queued message. Otherwise the agent becomes idle. An inbox message starts the same agent again with its existing rollout and chat history. A child remains active while any of its own children remain active, so this direct-child rule applies recursively without a separate wait tool.

When a child truly completes, its final answer or failure is delivered to its parent through the inbox after the child leaves the active registry. The parent therefore receives a natural followup turn. The root pipeline result is produced only after the root has no active descendants. Cancelling a child also cancels its descendants.

**BasicMultiAgentPipeline:**

This pipeline creates five agents with separate session-derived workspaces, registers all five in its own active-agent map, and watches them concurrently. They therefore share a messaging boundary without sharing filesystem edits. Candidate failures are retained without stopping the other runs. After the candidates finish, a sixth agent, configured separately as the diff judge, receives the task, all five diffs, and their completion statuses, then returns exactly one candidate number. That validated number is the pipeline result; the candidate workspaces and diffs remain available to the caller. The pipeline never commits a workspace.

Workspace behavior is compositional: future pipelines can pass one workspace to several agents, clone workspaces for isolation, or combine both patterns in different branches.

**Delegation and Messaging:**

`delegate` accepts an allowed configured subagent name and instructions, creates the child according to that config's workspace policy, records the rollout relationship, starts its lifecycle task, and returns its rollout ID. The child's initial task includes its parent rollout ID so it can send messages upward. The parent's per-agent tool schema enumerates the allowed names and their descriptions. Config lookup requires exactly one matching `subagent_name`.

`message_subagent` queues a string for a rollout ID. The owning pipeline routes and labels it; an unrelated or completed ID is simply absent from the local registry and receives nothing. `cancel_subagent` is restricted to a direct active child and recursively cancels that branch. Completion notifications use the same inbox wakeup behavior as ordinary messages. Broadcast and persistence of live agent tasks across process restarts are not implemented.

## Code Tools

**Viewing:**

The viewing tools read the effective workspace rather than the session directly. They support whole files, truncated file overviews, line ranges, explicit element paths, and the innermost element at a line. Parsed element views use `CodeNode` byte ranges; unsupported files fall back to raw line-oriented views.

The lower-level renderer can show full nodes or collapse nested bodies to an approximate symbol budget while retaining signatures and optional docstrings.

**Editing:**

Implemented edits include moving files in the overlay, creating empty files, replacing whole files, replacing parsed elements by path or line, and replacing line ranges. Structural and line edits are translated into byte-coordinate `FileEdit` values, which both parsed and ordinary files apply polymorphically.

Moves are represented as a workspace deletion plus creation. Directory creation is implicit when committed; the current `make_dir` arguments do not change in-memory behavior.

The interactive `open_file`, `open_lines`, `open_element`, and `open_element_at` tools return the selected content and bind a continuation for the next assistant response. Their shared range editor accepts exactly one replacement code block, treats a response without one as cancellation, rejects multiple blocks, and applies a byte-coordinate `FileEdit` to parsed or ordinary files. The continuation owns its transcript cleanup: it removes the temporary assistant replacement message and inserts the edit result and per-file diff as user content.

An open tool captures the complete file bytes when opened. Before applying its range edit it refreshes disk files and requires the effective workspace file to still match that snapshot. A concurrent change therefore cancels the edit instead of applying stale byte offsets.

**Searching:**

`search` performs case-insensitive regex search over the effective workspace. An optional regex filters paths, and an optional comma-separated extension list filters file types.

Matches in parsed files are assigned directly to the innermost `CodeNode`, avoiding duplicate parent matches. Top-level matches and matches in generic files are grouped under `<file>`. Element paths are searchable alongside content. Docstrings are included without repeating their matching source lines.

Results are ranked deterministically by match count and discovery order. `start_index` selects the first ranked result of a ten-item page and defaults to zero; displayed results include their one-based ranks. Each page is trimmed to forty output lines without removing ranked items. `list_folder` lists the immediate effective workspace entries at a project-relative path. `search_folders` performs case-insensitive regex matching over file paths and folder paths inferred from them, returning at most the first hundred sorted matches.

**Agent Utilities:**

Delegation, subagent messaging, and recursive cancellation are implemented. Secondary-tool listing and shell execution remain declared but unimplemented.

## Tool Protocol Adapter

The `tool_api` package is a separate compatibility layer for models or backends which do not provide native OpenAI function calling. It does not own sessions, workspaces, agents, or rollouts.

**StandardToolPipeline:**

The protocol pipeline converts an OpenAI request with native tool schemas and tool-call history into a tools-free chat. It injects textual tool schemas at `{{llm_tools_list}}`, converts prior tool calls and responses into text, and later extracts textual calls from model output back into OpenAI tool-call objects.

Supported textual formats are XML, JSON code blocks, Markdown, and fake CodeAct Python calls. Each format supplies a call builder, call extractor, and schema builder. A shared response builder formats tool results, and the validator checks tool names, required/unknown arguments, primitive types, and enum values.

**Proxy Server:**

`scripts/tool_server.py` exposes the protocol layer as a FastAPI proxy. Chat-completion requests are converted, forwarded to an OpenAI-compatible backend without native tools, parsed on return, and restored to OpenAI response shape. Requested streaming is simulated after receiving a complete non-streamed backend response.

Custom endpoints expose conversion, extraction, schema/call/response building, validation, round trips, history, and statistics. History and statistics are thread-safe but in-memory only. An optional Streamlit process provides a local WebUI.

## Current Boundaries

The current implementation does not yet include:

- Merging or graph pipelines.
- Broadcast messaging and broader agent-management tools.
- Non-Python language adapters.
- Repomap, embeddings, BM25, reranking, or prefix-cache retrieval.
- Automatic workspace commits, rebasing, or merging.
- Persistence or recovery of an in-flight continuation across process restarts.
- Persistent tool-proxy history.

These are extension points rather than hidden session behavior. The current runtime is centered on a live shared session, sparse copy-on-write workspaces, explicit pipeline composition, optimistic commits, Tree-sitter-backed code files, and persisted rollout histories.
