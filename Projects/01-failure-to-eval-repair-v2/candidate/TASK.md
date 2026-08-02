# Technical screen: a campaign that shipped incomplete

Target time: 90 minutes. Please stop at 120 minutes.

## The customer story

A marketer uploaded a list they described as five target companies and asked
CharacterQuilt for a personalized landing page and three LinkedIn ads for each
company, using the Brand Kit and campaign template they had selected.

CharacterQuilt reported the request complete, and the check that ships with
this starter agrees. The customer disagrees. Their note and the evidence from
the run are in `fixtures/`. Not everything in there necessarily has the same
cause.

This repository is a small local stand-in for that system. It does not call a
real model or a real customer account.

## Your assignment

Work out what actually happened, then improve the system so requests like this
one come out right.

We expect you to work with a coding agent — Claude Code, Codex, or equivalent —
and to record the whole session. We are evaluating how you use the agent, not
just the repository it leaves behind. Before you or the agent edit any source
or test file, use the evidence to form your own view of the problem, direct the
agent as you develop `ROADMAP.md`, and commit that roadmap on its own. During
the rest of the work, challenge assumptions and inspect the evidence yourself.
We read the transcript for the points where your input changed the work; the
number of messages you send does not matter.
A one-line request for an agent to complete the exercise unattended is not a
passing submission, even if the resulting code looks good. Nothing here tells
you what belongs in the roadmap; deciding that is part of the exercise.

By the end you should be able to show:

- what went wrong, and how you know;
- what "complete" should mean for this request;
- what you changed;
- why the fix holds beyond the exact data in `fixtures/`;
- what you left uncertain or out of scope.

You can change the implementation and the tests freely, including the checks
the starter ships with. Keep both make commands working.

## Constraints

- Everything stays local: no UI, database, queue, external service, or real
  model call.
- Load target accounts through the lookup interface the starter provides rather
  than reading the fixture file directly. Your own checks may supply their own
  implementation of that interface.
- Any deliverable must stay traceable to the uploaded input it came from.
- No special-casing of values that happen to appear in the fixtures.
- Don't repair behavior you can't tie to the customer's complaint.

## What to send back

- the repository, with its Git history;
- the complete raw transcript of your agent session, including the parts that
  went nowhere — please don't tidy it into a cleaner story;
- your `ROADMAP.md`, committed before any source or test edit;
- your code and whatever checks you added;
- `make demo` and `make test` working, with their output;
- `DECISIONS.md` and `SUBMISSION.md` filled in, including the time you actually
  spent.

`make demo` and `make test` already pass on the starter, so a green run is not
evidence that you are done — and neither is a green run of checks you wrote
yourself. Read the actual output before you claim a result. There are no hidden
tests and no automatic grade. A person reads the roadmap, the transcript, the
code, and your explanation.
