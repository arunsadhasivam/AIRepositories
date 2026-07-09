1) reflex Agent - if else agent
2) React Agent - based on input react 
3) Plan Execute Reflect(PER) Agent - plan, execute, reflect - reduce llm plan execute and then reflect
4) Query Decomposition Agent
    - ask who live longer a or b
    - internally use search tool find age of a
    - internally use search tool find age of b
    - syntehesis

5) Deep Research Agent. - do hypothesis do complex investigation
                           here it uses multiple agent like query decomposition to decompose query and PER to
                           plan , execute and reflect.
                         
# AI Agent Architectures

| Agent Type | Strength | Weakness | Use Case |
|---|---|---|---|
| **Reflex Agent** (If-Else) | Fast, cheap, deterministic, easy to debug | Can't handle novel scenarios, no reasoning, rules unmanageable at scale, no context adaptation | FAQ bots, form validation, IVR systems, threshold-based alerts |
| **React Agent** (Reason+Act) | Dynamic tool use, self-correcting via observation, flexible for multi-step tasks | Can loop excessively, no upfront plan (inefficient), costlier (multiple LLM calls), weak on long-horizon tasks | Support agent doing lookup+answer, coding assistant (run→check→fix), single-tool tasks (weather, search) |
| **Plan-Execute-Reflect** | Fewer LLM calls than React for multi-step tasks, better long-horizon handling, self-correcting via reflection, plan is auditable | Wrong initial plan if problem misunderstood, reflection adds latency/cost, rigid plan breaks if new info emerges mid-execution, complex orchestration | Workflow automation (generate→validate→format), coding agents planning file changes, "research→draft→review" pipelines |
| **Query Decomposition** | Handles compound questions well, sub-queries parallelizable (faster), traceable per-part sourcing, reduces hallucination | Wrong decomposition breaks everything, synthesis can misread sub-answers, overhead for simple queries, dependent sub-queries hard to parallelize | Comparison questions (life expectancy, stock/product comparison), multi-entity lookups, multi-source aggregation |
| **Deep Research Agent** | Handles deep/ambiguous multi-hop research, combines decomposition breadth + PER depth, adaptive (revises hypothesis), well-grounded comprehensive output | High latency, expensive (nested agent calls), hard to debug orchestration, compounding errors across layers | Market research reports, competitive analysis, literature review, due diligence investigations |
