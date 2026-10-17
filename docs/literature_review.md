# Literature note: validating a plan after the world changes

This note is the background for the October 18 handoff. The question Ryan locked on 11 October 2026 is narrow:

> When a deterministic world-state change invalidates an existing plan, can a validator identify the failing action preconditions and reject an invalid continuation while leaving a still-valid plan alone?

The program in this repository answers that question for propositional, totally ordered plans. It is a checker. It does not generate plans, it does not call a model, and it does not reopen the August satellite-JEPA draft.

## How this was searched

The relevant literature is not one bibliography. It splits into four clusters that actually touch the question: the semantics of preconditions and effects, execution monitoring after a discrepancy, plan repair versus leaving a valid plan alone, and the recent practice of putting a symbolic checker next to a language-model planner.

The search covered those clusters on the open web, then the primary sources that the searches and their own citations kept returning: the STRIPS and PLANEX papers, the PDDL validation tool VAL, Fritz and McIlraith on monitoring, the ICAPS line on plan repair and plan stability, Nebel and Koehler on the complexity of reuse, and the 2023–2025 papers that validate or repair language-model plans by precondition failure. Citations below are sources that were opened, or whose bibliographic details were confirmed from those sources. A claim that every planning paper has been listed would be false. Temporal, numeric, probabilistic, and motion planning appear only where they mark the boundary of this prototype. The August ESA anomaly-detection draft is outside the handoff and is not reviewed here.

## What a valid step is

Fikes and Nilsson (1971) introduced STRIPS operators with preconditions, an add list, and a delete list. The later standard formulation, as Muise, McIlraith, and Beck (2011) restate it for their monitor, is the one this prototype uses. A state is a set of true facts. A fact that is absent is false. An action is executable only when every precondition fact holds. Applying an executable action adds some facts and deletes others. A sequence is executable when each action is executable in the state produced by the actions before it.

That last sentence is the whole replay rule. Pednault's ADL (1989) and PDDL (Ghallab et al., 1998; Fox and Long, 2003) add types, quantifiers, conditional effects, and, in PDDL2.1, time and continuous change. Reiter's situation calculus (2001) is the logical setting in which Fritz and McIlraith later define regression. None of those extensions are required to ask Ryan's question, and none are implemented here. Effects in this code are assignments of Boolean facts, which is enough to express an add and a delete.

Bylander (1994) showed that propositional STRIPS plan existence is hard in general. That result is about generation. Checking a fully specified sequence against fully specified preconditions is a walk down the sequence. The handoff is the walk.

## Monitoring, and the state change that does not matter

The problem is older than language models. Fikes, Hart, and Nilsson (1972) built PLANEX because Shakey’s executed state rarely matched the state the planner had expected, and an exact match was neither realistic nor necessary. Most of a situation is irrelevant to the rest of the plan. PLANEX represents a sequential plan as a triangle table and computes a kernel for each suffix: the clauses that must hold if that suffix is still a way to the goal. The executor looks for a true kernel. If none is true, it replans. An atom that never enters a kernel can change without touching the plan.

That is fixture 01. `weather_clear` becomes false. Nothing in `unlock_cabinet` or `power_panel` mentions it. The plan stays valid. Fritz and McIlraith (2007) make the same distinction for a faster domain. In RoboCup the world is observed many times a second, and a team that replans on every discrepancy either wastes the cycle or, if it ignores discrepancies, walks into a real failure. Their validity monitor regresses the goal and the remaining preconditions back through the suffix, following Reiter (2001). Only a change that hits a regressed atom matters. Their harder result is about optimality, not validity: a plan can stay valid and stop being the best plan. This handoff does not score cost or optimality. Fixture 05 is about validity only.

The same idea shows up under other names. Veloso, Pollack, and Cox (1998) monitor the rationale of planning decisions rather than the whole state. McCarthy and Pollack (2000) adapt that focused monitor to a causal-link planner on a mobile robot. Wilkins (1985) recovers from execution errors in SIPE by using the structure of the plan to see which unexpected predicates actually affect it, then replanning while keeping the unaffected part. Muise, McIlraith, and Beck (2011) describe SIPE, and Prodigy, as monitors of causal-link violations. Ambros-Ingerson and Steel (1988) and Doyle, Atkinson, and Doshi (1986) integrate monitoring into the executive. De Giacomo, Reiter, and Soutchanski (1998) give a situation-calculus account for Golog programs, again for validity. Pettersson (2005) surveys the robotics side, including model-free monitors that do not have an explicit precondition model at all. Those monitors answer a different question. This prototype has the model in hand and checks it directly.

Muise, McIlraith, and Beck (2011) extend regression monitoring from sequences to partial-order plans. A partial-order plan is a family of sequences (Weld, 1994). Levine (2012) extracts candidate causal links from temporally flexible plans so the Pike executive can name, early, which future action a disturbance threatens. Both are the right next machinery if the plan is not a total order. Ryan specified an ordered plan, so the checker walks one order and records, at the later step, which failed earlier action withheld the missing fact. That link is the sequential special case of a causal link, computed during replay rather than stored by a planner.

Koenig, Furcy, and Bauer (2002) is the system Fritz and McIlraith single out as prior work on monitoring optimality, and only in a limited form. It is cited here so the boundary stays visible: irrelevant-for-validity and irrelevant-for-optimality are different tests. We run the first.

## Failed actions and invalid continuation

Classical semantics say an inapplicable action is not executable. They say less about the bookkeeping if a checker keeps walking afterward. If the checker applies the effects anyway, later preconditions that depended on those effects look satisfied, and the trace hides the cascade. If the checker stops at the first failure, the cascade is never written down.

Ryan’s rule does neither. Fixture 03 is the witness. The change sets `have_key` false. `unlock_cabinet` is rejected and does not write `cabinet_open`. `power_panel` is then rejected because `cabinet_open` is still false, and the trace names `unlock_cabinet` as the failed producer. A contrast replay that does apply the failed effect accepts `power_panel`. That contrast is what “invalid continuation” means in this handoff: treating the suffix as executable because a failed step was allowed to change the world. The validator uses the strict replay and rejects the suffix.

Fixture 02 is the control for that story. `tool_ready` disappears, so `take_tool` fails. `read_gauge` depends on `gauge_present`, which the change did not touch and `take_tool` does not produce. The second step stays valid. A direct resource loss and a withheld effect are different rows in the trace. Collapsing them would make every downstream miss look like another disappeared resource.

Howey, Long, and Fox (2004) built VAL for the third and fourth international planning competitions. VAL is the tool later language-model benchmarks call when they need an independent decision that a PDDL plan is legal. PlanBench uses it that way (Valmeekam et al., 2023). VAL covers PDDL2.1, including continuous effects, and it can advise a mixed-initiative user. This prototype is not a substitute for it. The deliberate differences are the ones the handoff needs: propositional facts only, a full trace after the first failure, effects of a failed step withheld, and an explicit comparison against a supplied repair and against a rewrite of a plan that was still valid.

## Repair, replanning, and a rewrite that was not required

Once a monitor has decided the current plan is invalid, someone has to produce another plan. That second problem is not this handoff. The history of it still explains fixtures 04 and 05.

Kambhampati (1990; with Hendler, 1992) treats reuse as repair of a validation structure: map an annotated plan into a new problem, mark the inconsistencies, and refit while disturbing the still-valid parts as little as possible. Simmons (1988) debugs a plan by replacing the assumptions that failed. Hanks and Weld (1995) give a domain-independent adaptation algorithm. Gerevini and Serina (2000) repair inside temporal windows of a planning graph, and later by replanning windows with heuristic goals (Gerevini and Serina, the CEUR/Fundamenta Informaticae line). van der Krogt and de Weerdt (2005) split repair into unrefinement (remove the actions that are in the way) and ordinary planning (add actions), and show that a planner can be extended to do both. Their POPR system beat replanning from scratch and beat GPG on the instances they report.

Nebel and Koehler (1995) are the reason this prototype does not pretend that repair is the cheap part. Worst-case, reuse has no complexity advantage over generating a plan. Conservative modification, which keeps as much of the old plan as possible, can be strictly harder than planning from scratch, even when the old and new instances look similar. Retrieving a good library plan is itself hard. So “we already have a plan” is not an algorithm. Fixture 04 does not search. It checks a repair that was written into the fixture: `fetch_spare_key`, then the original two steps. The same change leaves the original plan invalid. The table’s no-repair column is that original plan. The repair column is the supplied sequence, which replays cleanly. Passing fixture 04 says the checker can accept a legal plan after the same change that broke another plan. It says nothing about a generator.

Fox, Gerevini, Long, and Serina (2006) argue that when a plan has to be replaced, stability matters, especially where the executive or its equipment can get hurt by a large unsignalled change. They define stability by a distance between action sets, seed LPG with the old plan, and penalize drift. They cite minimal perturbation (Kambhampati, 1990; Simmons, 1988) and the point, from Cushing and Kambhampati (2005), that a plan which revises one already shown to other agents cannot be scored as if those commitments did not exist. Brenner and Nebel (2006; journal version 2009) make the same practical point inside continual planning: if plan stability is not an issue one may replan freely, but breaking a shared plan is expensive because revision spreads to other agents.

Fixture 05 is the case those papers assume away when they say the old plan must be replaced. The weather fact flips. The original plan never consults it, so it remains executable. A different plan, with an extra `log_status` step, is also executable. The checker records the difference as an unnecessary rewrite. It does not call the original plan an invalid continuation. Those are different errors. Fox and colleagues measure how far a necessary repair moved. We only mark that a rewrite happened while the original replay was clean. We do not compute edit distance, and we do not claim the rewrite is worse on any objective besides validity. A shorter or cheaper rewrite of a valid plan would still be labelled unnecessary on this test, because the test is about validity.

## Checkers in front of language-model planners

The reason to build the small checker, rather than another planner, is the empirical record on language models since 2022.

Valmeekam, Marquez, Sreedharan, and Kambhampati (arXiv:2302.06706, 2023) evaluate models as autonomous planners, as heuristic advisors, and with a person in the loop. Autonomous executable-plan rates in that study are about 3 percent. PlanBench (Valmeekam, Marquez, Olmo, Sreedharan, and Kambhampati, NeurIPS 2023) turns the same style of domain into a suite for generation, verification, execution reasoning, replanning, and reuse. The appendix uses Fast Downward to produce reference plans and VAL to judge them. It also scores model plans under a precondition relaxation, which ignores preconditions and treats every action as executable, and under a delete relaxation. A plan that is legal in the real model is legal in both relaxations. The interesting failures are the ones that become legal only after a relaxation. That is the same contrast as our lenient replay, restricted to effects of failed steps, and the same contrast as a checker that does not read preconditions at all.

Arora and Kambhampati (arXiv:2305.17077, 2023) locate a concrete failure mode of a finetuned GPT-2 planner: it emits actions whose preconditions are false in the state it is in. They train a verifier to reject those actions and prune sampled trajectories. Rossetti, Tummolo, Gerevini, Olivato, Putelli, and Serina (ICAPS 2025 RIPL workshop) do the symbolic version of that prune. PlanGPT can emit a high-probability action that is illegal, such as picking up a block that is covered. Their Val-MB decoder asks a PDDL validator during generation and drops the illegal prefix. The validator is doing fixture-02 work at every decoding step: the resource for this action is not in the state, so the action is not a candidate.

Xie, Yang, Gunerli, and Riedl (arXiv:2409.12278, 2024) split a world model into the two questions STRIPS already separates: is this action applicable, and if it is, what changes. They fine-tune models to predict preconditions and effects, then check and apply those predictions. The second half of that pipeline is a learned action model sitting where this repository has a hand-written one. Until that model is trustworthy, a checker that trusts the written preconditions is the safer instrument. This handoff uses the written ones.

On robots, the same split appears as recovery rather than as an offline table. Raman, Cohen, Idrees, Rosen, Mooney, Tellex, and Paulius (ICRA 2024) prompt for a corrective action when a skill fails its precondition; CAPE is a generator that consumes the kind of unmet-precondition record our trace produces. Rivera and colleagues (arXiv:2410.06108, 2024) ground predicates before execution in ConceptAgent and feed the unsatisfied set back to the model. Chen, Yang, Jia, Hu, Chen, Zhang, Wang, and Pan (RSS 2024) refine missing preconditions with a language model and then replan in LASP. Petruzzellis, Cornelio, and Liò (arXiv:2504.04578, 2025) simulate a candidate plan in an ideal PDDL world and, at runtime, compare that simulated state with the observed one. Merler, Dainese, Alakuijala, Bonetta, Ferrazzi, Tian, Magnini, and Marttinen (arXiv:2505.13180, 2025) show, in ViPlan, what happens when the precondition judgment itself is wrong: rejecting a true precondition can block a necessary action permanently, and accepting a false one makes the agent repeat an illegal action. Their grounder is a vision-language model. Ours is a Boolean lookup. The failure modes they name are why the lookup has to be the thing under test before any learned grounder is attached.

Across this cluster the symbolic checker is the piece that makes a later claim measurable. Missed invalidation, invalid continuation, and unnecessary rewriting are not given those three names in the papers above. The phenomena are. A model plan that skips a precondition is a miss. A suffix that only works if a failed action’s effects are pretended is an invalid continuation. A new plan for a state in which the old plan still replays is an unnecessary rewrite, which is the validity special case of the unnecessary replanning Fritz and McIlraith describe and of the instability Fox, Gerevini, Long, and Serina measure.

## Where the prototype sits

The checker is a propositional STRIPS replay with four additions that the handoff asked for and that VAL’s “is this PDDL plan legal?” question does not package together:

- the world-state change is applied before any step
- a failed step writes nothing, and the walk continues
- a supplied repair is scored next to the unrepaired plan
- a rewrite of a still-valid plan is labelled separately from an invalid continuation

It does not parse PDDL, quantify over objects, handle conditional or continuous effects, monitor partial orders or time, estimate cost, or search for a repair. A plan with no unmet preconditions can still fail an unstated goal. Fixture 04’s repair happens to power the panel; the official criterion is the precondition walk, not a goal test. There is one change, applied once, before the plan. The checker does not model a disturbance that arrives between step 2 and step 3. Two hundred further replays, drawn from a fixed seed, check the same rule on random actions: determinism, effects withheld on failure, and agreement with the lenient replay up to the first failure. They are a regression suite for the rule, not a benchmark study.

Nothing here needs a GPU or a remote notebook. The command that produces the expected-versus-observed table finishes in tens of milliseconds on a laptop because each fixture is a handful of Boolean lookups. The language-model papers above are where compute starts, and Ryan deferred that work until this prototype has been reviewed.

## References

Arora, D., and Kambhampati, S. (2023). Learning and leveraging verifiers to improve planning capabilities of pre-trained language models. arXiv:2305.17077.

Ambros-Ingerson, J., and Steel, S. (1988). Integrating planning, execution and monitoring. Proceedings of AAAI-88, 83–88. Cited from Fritz and McIlraith (2007).

Brenner, M., and Nebel, B. (2006). Continual planning and acting in dynamic multiagent environments. https://gki.informatik.uni-freiburg.de/papers/brenner-nebel06.pdf. Journal version: Autonomous Agents and Multi-Agent Systems, 19(3), 297–331, 2009.

Bylander, T. (1994). The computational complexity of propositional STRIPS planning. Artificial Intelligence, 69(1–2), 165–204.

Chen, G., Yang, L., Jia, R., Hu, Z., Chen, Y., Zhang, W., Wang, W., and Pan, J. (2024). Language-augmented symbolic planner for open-world task planning. Robotics: Science and Systems. arXiv:2407.09792. https://doi.org/10.15607/rss.2024.xx.037

Cushing, W., and Kambhampati, S. (2005). Replanning: A new perspective. Cited by Fox, Gerevini, Long, and Serina (2006) for commitments created by a plan that has already been communicated.

De Giacomo, G., Reiter, R., and Soutchanski, M. (1998). Execution monitoring of high-level robot programs. Proceedings of KR-98, 453–465.

Doyle, R., Atkinson, D., and Doshi, R. (1986). Generating perception requests and expectations to verify the execution of plans. Proceedings of AAAI-86, 81–88.

Fikes, R. E., and Nilsson, N. J. (1971). STRIPS: A new approach to the application of theorem proving to problem solving. Artificial Intelligence, 2(3–4), 189–208. https://doi.org/10.1016/0004-3702(71)90010-5

Fikes, R. E., Hart, P. E., and Nilsson, N. J. (1972). Learning and executing generalized robot plans. Artificial Intelligence, 3, 251–288.

Fox, M., Gerevini, A., Long, D., and Serina, I. (2006). Plan stability: Replanning versus plan repair. Proceedings of ICAPS 2006. https://aaai.org/papers/icaps-06-022-plan-stability-replanning-versus-plan-repair/

Fox, M., and Long, D. (2003). PDDL2.1: An extension to PDDL for expressing temporal planning domains. Journal of Artificial Intelligence Research, 20, 61–124.

Fritz, C., and McIlraith, S. A. (2007). Monitoring plan optimality during execution. Proceedings of ICAPS 2007, 144–151. https://www.cs.toronto.edu/~sheila/publications/fri-mci-icaps07.pdf

Gerevini, A., and Serina, I. (2000). Fast plan adaptation through planning graphs: Local and systematic search techniques. Proceedings of AIPS 2000.

Gerevini, A., and Serina, I. Efficient plan adaptation through replanning windows and heuristic goals. https://ceur-ws.org/Vol-451/paper08gerevini.pdf

Ghallab, M., Howe, A., Knoblock, C., McDermott, D., Ram, A., Veloso, M., Weld, D., and Wilkins, D. (1998). PDDL—The Planning Domain Definition Language. Technical Report CVC TR-98-003/DCS TR-1165, Yale Center for Computational Vision and Control.

Hanks, S., and Weld, D. S. (1995). A domain-independent algorithm for plan adaptation. Journal of Artificial Intelligence Research, 2, 319–360. https://doi.org/10.1613/jair.79

Howey, R., Long, D., and Fox, M. (2004). VAL: Automatic plan validation, continuous effects and mixed initiative planning using PDDL. Proceedings of ICTAI 2004. https://doi.org/10.1109/ICTAI.2004.120

Kambhampati, S. (1990). A theory of plan modification. Proceedings of AAAI-90, 176–182.

Kambhampati, S., and Hendler, J. (1992). A validation-structure-based theory of plan modification and reuse. Artificial Intelligence, 55(2–3), 193–258. https://doi.org/10.1016/0004-3702(92)90056-4

Koenig, S., Furcy, D., and Bauer, C. (2002). Heuristic search-based replanning. Proceedings of AIPS 2002, 294–301.

Levine, S. J. (2012). Monitoring the execution of temporal plans for robotic systems. M.Eng. thesis, Massachusetts Institute of Technology. http://hdl.handle.net/1721.1/73686

McCarthy, C. E., and Pollack, M. E. (2000). Towards focused plan monitoring: A technique and an application to mobile robots. Autonomous Robots, 9(1), 71–81. https://doi.org/10.1023/a:1008980403252

Merler, M., Dainese, N., Alakuijala, M., Bonetta, G., Ferrazzi, P., Tian, Y., Magnini, B., and Marttinen, P. (2025). ViPlan: A benchmark for visual planning with symbolic predicates and vision-language models. arXiv:2505.13180.

Muise, C., McIlraith, S. A., and Beck, J. C. (2011). Monitoring the execution of partial-order plans via regression. Proceedings of IJCAI 2011. https://www.ijcai.org/Proceedings/11/Papers/330.pdf

Nebel, B., and Koehler, J. (1995). Plan reuse versus plan generation: A theoretical and empirical analysis. Artificial Intelligence, 76(1–2), 427–454. https://doi.org/10.1016/0004-3702(94)00082-c

Pednault, E. P. D. (1989). ADL: Exploring the middle ground between STRIPS and the situation calculus. Proceedings of KR 1989.

Pettersson, O. (2005). Execution monitoring in robotics: A survey. Robotics and Autonomous Systems, 53(2), 73–88. https://doi.org/10.1016/j.robot.2005.09.004

Petruzzellis, F., Cornelio, C., and Liò, P. (2025). Hierarchical planning for complex tasks with knowledge graph-RAG and symbolic verification. arXiv:2504.04578.

Raman, S. S., Cohen, V., Idrees, I., Rosen, E., Mooney, R., Tellex, S., and Paulius, D. (2024). CAPE: Corrective actions from precondition errors using large language models. Proceedings of ICRA 2024.

Reiter, R. (2001). Knowledge in Action: Logical Foundations for Specifying and Implementing Dynamical Systems. MIT Press.

Rivera, C., Byrd, G., Paul, W., Feldman, T., Booker, M., Holmes, E., Handelman, D., Kemp, B., Badger, A., Schmidt, A., Jatavallabhula, K. M., de Melo, C. M., Seenivasan, L., Unberath, M., and Chellappa, R. (2024). ConceptAgent: LLM-driven precondition grounding and tree search for robust task planning and execution. arXiv:2410.06108.

Rossetti, N., Tummolo, M., Gerevini, A. E., Olivato, M., Putelli, L., and Serina, I. (2025). Enhancing GPT-based planning policies by model-based plan validation. ICAPS 2025 Workshop on Reliable and Integrated Planning and Learning (RIPL).

Simmons, R. G. (1988). A theory of debugging plans and interpretations. Proceedings of AAAI-88, 94–99.

Valmeekam, K., Marquez, M., Olmo, A., Sreedharan, S., and Kambhampati, S. (2023). PlanBench: An extensible benchmark for evaluating large language models on planning and reasoning about change. Advances in Neural Information Processing Systems 36, Datasets and Benchmarks. https://proceedings.neurips.cc/paper_files/paper/2023/file/7a92bcdede88c7afd108072faf5485c8-Paper-Datasets_and_Benchmarks.pdf

Valmeekam, K., Sreedharan, S., Marquez, M., Olmo, A., and Kambhampati, S. (2023). On the planning abilities of large language models: A critical investigation with a proposed benchmark. arXiv:2302.06706.

van der Krogt, R., and de Weerdt, M. (2005). Plan repair as an extension of planning. Proceedings of ICAPS 2005, 161–170.

Veloso, M., Pollack, M., and Cox, M. (1998). Rationale-based monitoring for planning in dynamic environments. Proceedings of AIPS 1998, 171–179.

Weld, D. S. (1994). An introduction to least commitment planning. AI Magazine, 15(4), 27–61. Cited from Muise, McIlraith, and Beck (2011).

Wilkins, D. E. (1985). Recovering from execution errors in SIPE. Computational Intelligence, 1(1), 33–45. https://doi.org/10.1111/j.1467-8640.1985.tb00057.x

Xie, K., Yang, I., Gunerli, J., and Riedl, M. (2024). Making large language models into world models with precondition and effect knowledge. arXiv:2409.12278.

The maintained VAL sources are at https://github.com/KCL-Planning/VAL.
