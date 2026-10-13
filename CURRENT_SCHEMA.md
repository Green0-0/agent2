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

An `AgentConfig` contains its injected config path, subagent name and description, system prompt, header, speculative viewing prompt, prompt wrapper, model, optional API base URL, and optional API-key environment variable.

The current default constructor uses the system prompt and the supplied task directly. The header, speculative viewing prompt, and prompt wrapper remain available to custom constructors but are not merged by the default path.

**Agent:**

Each `Agent` owns one rollout, one workspace reference, one config, an LLM client, constructors, hooks, tools, and asynchronous inbox/outbox queues. The rollout ID is the agent's execution identity. Parent and child IDs describe rollout relationships; they do not imply workspace sharing or commit ancestry.

**Constructors:**

Constructors modify chat state during initial setup and followups.

The default constructor inserts the configured system prompt followed by the user prompt. Optional constructors can substitute the current date, operating-system information, or the workspace path listing into configured tokens. Each provider replaces both the lightweight `{{key}}` and full-sentence `{{key*}}` forms in the same pass.

**Hooks:**

Hooks run after each LLM response. Their optional string results are stacked and appended to the latest tool/user message or inserted as a new user message.

The default `ToolCallHook` refreshes session files, parses tool arguments, injects runtime-only arguments such as `agent`, `session`, and `agentconfig`, executes the selected tool, and appends an OpenAI-format tool response. Tool exceptions become tool response text rather than escaping the agent loop.

**Tools:**

`Tool` wraps a Python function and builds an OpenAI function schema from its signature and docstring. Runtime-only parameters are omitted from the public schema. Required parameters are inferred from missing defaults, and examples are parsed from `Task:` / `Tool Call:` docstring blocks.

## Agent Loop

The agent loop has a configurable maximum number of steps, defaulting to 100.

1. Drain the inbox into `raw_chat`. A `STOP` message saves and ends the rollout.
2. Send the current chat, model, and tool schemas to an OpenAI-compatible chat-completions client.
3. Append the assistant message to `raw_chat`.
4. Run each hook and append any stacked hook output.
5. Save the rollout.
6. Return the assistant content when no tool call remains; otherwise continue.

Exceeding the step limit raises an error.

## Pipeline Composition

**Pipeline:**

`Pipeline` is an abstract runtime with a map of active agents. Concrete pipelines decide how agents are created, connected, assigned workspaces, and finalized.

**SingleAgentPipeline:**

The implemented pipeline creates one agent from a config path and prompt. It accepts an explicit rollout ID, parent ID, constructors, hooks, tools, workspace, client, and step limit. If no workspace is supplied, it creates a fresh overlay on the session.

The pipeline runs the agent and an outbox listener concurrently, routes messages to active agents, saves the rollout during cleanup, and removes the agent from the active map. A missing target is an error.

**BasicMultiAgentPipeline:**

This pipeline concurrently runs five agents from the same prompt in cloned, isolated workspaces. Candidate failures are retained without stopping the other runs. A sixth agent receives the task, all five diffs, and their completion statuses, then returns exactly one candidate number. That validated number is the pipeline result; the candidate workspaces and diffs remain available to the caller. The pipeline never commits a workspace.

Workspace behavior is compositional: future pipelines can pass one workspace to several agents, clone workspaces for isolation, or combine both patterns in different branches.

**Messaging Limitation:**

The current inbox/outbox implementation is scaffolding rather than functional multi-agent messaging. `SingleAgentPipeline` listens only to its single agent's outbox, and its active-agent registry contains only that agent. Messages to any other rollout fail, independently created pipelines cannot see each other's live agents, and the declared messaging tools are not implemented. A message arriving during an agent's final LLM step may also remain unread because the inbox is only drained before each step.

Broadcast messaging requires a shared runtime message bus used by every pipeline in the same composed run. The bus must own the live-agent registry, support direct and broadcast envelopes with sender identity, deliver only to active inboxes, and register/unregister agents atomically with completion. Tool execution must await asynchronous messaging tools, and agents must check delivered messages after an LLM response before returning. `Session.datastore` cannot serve this role because it contains persisted rollouts rather than live agents. The basic multi-agent pipeline does not use messaging; it composes independent candidate runs and a final judging run.

## Code Tools

**Viewing:**

The viewing tools read the effective workspace rather than the session directly. They support whole files, truncated file overviews, line ranges, explicit element paths, and the innermost element at a line. Parsed element views use `CodeNode` byte ranges; unsupported files fall back to raw line-oriented views.

The lower-level renderer can show full nodes or collapse nested bodies to an approximate symbol budget while retaining signatures and optional docstrings.

**Editing:**

Implemented edits include moving files in the overlay, creating empty files, replacing whole files, replacing parsed elements by path or line, and replacing line ranges. Structural and line edits are translated into byte-coordinate `FileEdit` values, which both parsed and ordinary files apply polymorphically.

Moves are represented as a workspace deletion plus creation. Directory creation is implicit when committed; the current `make_dir` arguments do not change in-memory behavior.

The interactive `open_file`, `open_lines`, `open_element`, and `open_element_at` tools are declared but not implemented.

**Searching:**

`search` performs case-insensitive regex search over the effective workspace. An optional regex filters paths, and an optional comma-separated extension list filters file types.

Matches in parsed files are assigned directly to the innermost `CodeNode`, avoiding duplicate parent matches. Top-level matches and matches in generic files are grouped under `<file>`. Element paths are searchable alongside content. Docstrings are included without repeating their matching source lines.

Results retain the ten elements with the most matches and are trimmed to forty output lines. `multisearch`, folder listing, and folder-search variants are declared but not implemented.

**Agent Utilities:**

Delegation, subagent messaging, cancellation, secondary-tool listing, and shell execution are declared but not implemented. Multi-agent behavior is currently supplied by pipeline composition rather than these tools.

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
- A shared live-agent message bus and implemented delegation, broadcast, and agent-management tools.
- Interactive editor windows.
- Non-Python language adapters.
- Repomap, embeddings, BM25, reranking, or prefix-cache retrieval.
- Automatic workspace commits, rebasing, or merging.
- Persistent tool-proxy history.

These are extension points rather than hidden session behavior. The current runtime is centered on a live shared session, sparse copy-on-write workspaces, explicit pipeline composition, optimistic commits, Tree-sitter-backed code files, and persisted rollout histories.
