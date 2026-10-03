export const meta = {
    name: "deliberation",
    description: "Council debate: blind openings, open-floor rounds with urgency bids, then a ballot vote counted in code",
    whenToUse: "Launched by the council skill, which frames the brief and acts as clerk between sittings",
    phases: [{
        title: "Openings",
        detail: "every member states a position without seeing the others",
    }, {
        title: "Floor",
        detail: "members bid for the floor and the most urgent speak",
    }, {
        title: "Vote",
        detail: "members vote on the clerk's ballot, counted in code",
    }],
};

/*
 * Council deliberation workflow.
 *
 * Runs a debate between council members under coded rules of order: blind openings, open-floor
 * rounds in which members bid for the right to speak, and a vote on a ballot. Each seat is played
 * by the plugin agent of the same name (agents/<seat>.md), which carries the persona, the model
 * and the effort level. This script carries the rules that are the same for every member.
 *
 * The debate is played in sittings. The council skill launches the script once per sitting and
 * relaunches it with `resumeFromRunId`: agent calls of earlier sittings replay from cache and only
 * the next sitting runs live. Between sittings the clerk (the main session) adds a note; to close,
 * it passes the ballot. The brief and earlier notes must be resent unchanged, or the replay
 * diverges - the `expect` checkpoint guards that.
 *
 * args: {
 *   brief: string                       neutral statement of the matter
 *   seats?: string[]                    seats to convene (default: all 16)
 *   sittings?: number                   sittings to play in total, counting earlier launches
 *   notes?: string[]                    clerk notes; notes[i] is read out after sitting i + 1
 *   ballot?: [{id, title, summary}]     when present, the vote is held after the last sitting
 *   expect?: {notes, fingerprint}       checkpoint returned by the previous launch
 * }
 */

const SEATS = [
    "INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP",
    "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP",
];
const ROUNDS_PER_SITTING = 3;
const MAX_ROUNDS = 8;
const QUIET_BELOW = 3; // the floor is quiet when no bid reaches this urgency
const TURN_PENALTY = 1; // floor priority lost per turn already taken
const REPLY_BONUS = 2; // floor priority gained by a member who was challenged or questioned
const CONSENSUS_SHARE = 0.75;
const MOVES = ["challenge", "support", "question", "new_angle", "concede", "propose", "move_to_vote"];
const OWES_REPLY = ["challenge", "question"];

const CONDUCT = `- Argue from the brief and from what was said. Do not invent facts, and say so when you assume something.
- Speak from your own way of seeing things, in plain language. Never mention your seat's type or traits.
- Do not repeat a point that is already on the record.`;

const OPENING = {
    phase: "Openings",
    tag: "Opening",
    schema: {
        type: "object",
        additionalProperties: false,
        required: ["sees", "stance", "reasoning", "proposal"],
        properties: {
            sees: { type: "string", description: "What your way of seeing things notices here that a plain cost-benefit reading would miss, in at most 50 words" },
            stance: { type: "string", description: "Your position in one or two sentences" },
            reasoning: { type: "string", description: "What decides it for you, in at most 80 words" },
            proposal: { type: "string", description: "The concrete course of action you recommend, in at most 12 words" },
        },
    },
};

const RENDER = {
    opening: e => `**${e.seat}** sees: ${e.sees} **Stance:** ${e.stance} ${e.reasoning} *Proposal: ${e.proposal}*`,
    speech: e => `**${e.seat}** to ${e.to} (${e.move}): ${e.text}`,
    murmurs: e => `*Murmurs -* ${e.items.map(m => `${m.seat}: ${m.text}`).join(" | ")}`,
    note: e => `**Clerk:** ${e.text}`,
    close: e => `*${e.text}*`,
};

/** Normalize the `args` global into a full config; a bare string is taken as the brief. */
function readConfig(input) {
    const given = typeof input === "string" ? { brief: input } : input || {};
    return {
        brief: (given.brief || "").trim(),
        seats: given.seats && given.seats.length ? given.seats.map(seat => seat.toUpperCase()) : SEATS,
        sittings: given.sittings || 1,
        notes: (given.notes || []).map(note => note.trim()),
        ballot: given.ballot || null,
        expect: given.expect || null,
    };
}

/** Short stable hash of a string (djb2). */
function fingerprint(text) {
    let hash = 5381;
    for (let i = 0; i < text.length; i++) hash = ((hash << 5) + hash + text.charCodeAt(i)) | 0;
    return (hash >>> 0).toString(16);
}

/** Checkpoint over the brief and the first `count` clerk notes; the next launch sends it back as `expect`. */
function checkpoint(cfg, count) {
    return { notes: count, fingerprint: fingerprint([cfg.brief, ...cfg.notes.slice(0, count)].join("\n---\n")) };
}

/** Reject a config that cannot be played or that would make the cached replay diverge. */
function assertValid(cfg) {
    const unknown = cfg.seats.filter(seat => !SEATS.includes(seat));
    if (!cfg.brief) throw new Error("council: args.brief is required");
    if (unknown.length) throw new Error(`council: unknown seats: ${unknown.join(", ")}`);
    if (cfg.seats.length < 3) throw new Error("council: convene at least 3 seats");
    if (cfg.ballot && (cfg.ballot.length < 2 || cfg.ballot.length > 5)) throw new Error("council: a ballot needs 2 to 5 options");
    if (cfg.expect && checkpoint(cfg, cfg.expect.notes).fingerprint !== cfg.expect.fingerprint) {
        throw new Error("council: the brief or an earlier clerk note differs from the previous launch; resend them unchanged");
    }
}

/** Sitting that a floor round belongs to. */
function sittingOf(round) {
    return Math.ceil(round / ROUNDS_PER_SITTING);
}

/** Render transcript entries as Markdown, with a heading wherever the section changes. */
function renderTranscript(entries) {
    return entries.map((entry, i) => {
        const heading = i === 0 || entries[i - 1].section !== entry.section ? `## ${entry.section}\n\n` : "";
        return heading + RENDER[entry.kind](entry);
    }).join("\n\n");
}

/** Ask every seat the stage's question in parallel; seats that fail to answer are left out. */
async function askAll(seats, stage, promptFor) {
    const answers = await parallel(seats.map(seat => () => agent(promptFor(seat), {
        agentType: `council:${seat.toLowerCase()}`,
        schema: stage.schema,
        phase: stage.phase,
        label: `${stage.tag} ${seat}`,
    })));
    return seats.map((seat, i) => ({ seat, answer: answers[i] })).filter(reply => reply.answer);
}

/** Prompt for the blind opening round; identical for every seat. */
function openingPrompt(cfg) {
    return `The council is convened on the matter below. This is the opening round: every member states a position at the same time, and you cannot see what the others say.

# Brief

${cfg.brief}

# Your task

State where you stand, starting from what your seat weighs most. Decide the way someone with your priorities would decide, even where a neutral analyst would tally it differently. The other members are answering at this moment and will cover the neutral tally between them, so the council learns nothing from you if you only repeat it.
- sees: what your way of seeing things notices here that a plain cost-benefit reading would miss or underweight, in at most 50 words.
- stance: your position in one or two sentences.
- reasoning: what decides it for you, in at most 80 words.
- proposal: the concrete course of action you recommend, in at most 12 words.

# Rules

- Take the position your own way of seeing things actually leads to. Do not disagree for show, and do not drift to the answer you expect the majority to give.
${CONDUCT}`;
}

/** Collect the blind openings and start the debate state. */
async function openings(cfg) {
    const replies = await askAll(cfg.seats, OPENING, () => openingPrompt(cfg));
    return {
        entries: replies.map(reply => ({ kind: "opening", section: "Openings", sitting: 0, seat: reply.seat, ...reply.answer })),
        turns: {},
        owed: [],
        bids: [],
        rounds: 0,
        closed: null,
    };
}

/** Stage for one floor round; a bid may address any convened seat or ALL. */
function floorStage(seats, round) {
    return {
        phase: "Floor",
        tag: `R${round}`,
        schema: {
            type: "object",
            additionalProperties: false,
            required: ["urgency", "move", "addressed_to", "contribution", "murmur"],
            properties: {
                urgency: { type: "integer", minimum: 0, maximum: 5 },
                move: { type: "string", enum: MOVES },
                addressed_to: { type: "string", enum: [...seats, "ALL"] },
                contribution: { type: "string", description: "What you would say with the floor, at most 120 words" },
                murmur: { type: "string", description: "Your audible reaction if you do not get the floor, at most 12 words" },
            },
        },
    };
}

/** Number of members who get the floor per round: a quarter of the council, at least 2. */
function floorSize(seatCount) {
    return Math.max(2, Math.ceil(seatCount / 4));
}

/** Prompt asking one member for a floor bid in the given round. */
function floorPrompt(cfg, state, round, seat) {
    const reply = state.owed.includes(seat) ? " You were challenged or questioned directly in the last round, so you have the right of reply." : "";
    return `The council is in session on the matter below. You hold the ${seat} seat.

# Brief

${cfg.brief}

# The debate so far

${renderTranscript(state.entries)}

# Your task: floor round ${round} of at most ${MAX_ROUNDS}

You have held the floor ${state.turns[seat] || 0} time(s) so far.${reply}
Prepare what you would say if given the floor now, and rate honestly how much it needs saying. The ${floorSize(cfg.seats.length)} most urgent members speak; everyone else is recorded only with a murmur.

- urgency: how badly the council needs to hear this from you now. 0 = nothing to add. 1 = a refinement someone else could make. 2 = a fair point, but the debate survives without it. 3 = the debate is going wrong without this. 4 = a decisive point nobody has made. 5 = the council is about to make a mistake that only you see. Stay in character: your seat description says how readily you take the floor, and a member who speaks seldom bids 0 to 2 in most rounds. In a healthy round most bids are 2 or lower.
- move: challenge, support, question, new_angle, concede, propose or move_to_vote. Use move_to_vote when the disagreements that remain would not change your vote.
- addressed_to: the seat whose claim you answer, or ALL for a new angle, a proposal or a motion.
- contribution: at most 120 words. Name the specific claim you are answering.
- murmur: at most 12 words, your audible reaction if you do not get the floor.

# Rules

- Answer the strongest version of the claim you oppose.
- Change your position only by naming the argument that moved you. Agreeing to keep the peace is not allowed, and neither is holding out once you have been answered.
${CONDUCT}`;
}

/** Reason the floor closes on these bids, or null when the debate goes on. */
function closingReason(bids, seatCount) {
    const motions = bids.filter(bid => bid.answer.move === "move_to_vote").length;
    if (motions * 2 > seatCount) return `Motion to vote carried, ${motions} of ${seatCount}.`;
    if (!bids.some(bid => bid.answer.urgency >= QUIET_BELOW)) return "The floor fell quiet.";
    return null;
}

/** Floor priority of a bid: its urgency, lowered per turn already taken, raised by a right of reply. */
function priority(bid, state) {
    const owed = state.owed.includes(bid.seat) ? REPLY_BONUS : 0;
    return bid.answer.urgency - TURN_PENALTY * (state.turns[bid.seat] || 0) + owed;
}

/** Deterministic lot for breaking a tie between equal bids, different for every seat and round. */
function lot(seat, round) {
    return parseInt(fingerprint(`${seat} draws in round ${round}`), 16);
}

/** Pick the round's speakers: highest priority first, ties to whoever spoke least, then by lot. */
function pickSpeakers(bids, state, round) {
    return bids
        .map(bid => ({ bid, score: priority(bid, state), turns: state.turns[bid.seat] || 0, lot: lot(bid.seat, round) }))
        .filter(candidate => candidate.bid.answer.urgency > 0)
        .sort((a, b) => b.score - a.score || a.turns - b.turns || a.lot - b.lot)
        .slice(0, floorSize(bids.length))
        .map(candidate => candidate.bid);
}

/** Close the floor for good, recording why. */
function closeFloor(state, round, reason) {
    const entry = { kind: "close", section: `Floor round ${round}`, sitting: sittingOf(round), text: reason };
    return { ...state, rounds: round, closed: reason, entries: [...state.entries, entry] };
}

/** One-line record of a round's bids for the clerk: seat, urgency, move, with * on those who got the floor. */
function bidRecord(round, bids, speakers) {
    const line = bids.map(bid => `${bid.seat} ${bid.answer.urgency} ${bid.answer.move}${speakers.includes(bid) ? "*" : ""}`).join(", ");
    return { sitting: sittingOf(round), line: `R${round}: ${line}` };
}

/** Play one floor round and return the next debate state. */
async function floorRound(cfg, before, round) {
    const bids = await askAll(cfg.seats, floorStage(cfg.seats, round), seat => floorPrompt(cfg, before, round, seat));
    const reason = closingReason(bids, cfg.seats.length);
    const speakers = reason ? [] : pickSpeakers(bids, before, round);
    const state = { ...before, bids: [...before.bids, bidRecord(round, bids, speakers)] };
    if (reason) return closeFloor(state, round, reason);
    const place = { section: `Floor round ${round}`, sitting: sittingOf(round) };
    const speeches = speakers.map(bid => ({
        ...place,
        kind: "speech",
        seat: bid.seat,
        move: bid.answer.move,
        to: bid.answer.addressed_to,
        text: bid.answer.contribution,
    }));
    const murmurs = bids.filter(bid => !speakers.includes(bid)).map(bid => ({ seat: bid.seat, text: bid.answer.murmur }));
    speeches.forEach(speech => log(`R${round} ${RENDER.speech(speech)}`));
    return {
        ...state,
        rounds: round,
        entries: [...state.entries, ...speeches, ...(murmurs.length ? [{ ...place, kind: "murmurs", items: murmurs }] : [])],
        turns: speakers.reduce((turns, bid) => ({ ...turns, [bid.seat]: (turns[bid.seat] || 0) + 1 }), state.turns),
        owed: speeches.filter(speech => OWES_REPLY.includes(speech.move) && speech.to !== speech.seat).map(speech => speech.to),
    };
}

/** Play the floor rounds of one sitting, then read out the clerk's note for it if there is one. */
async function playSitting(cfg, start, sitting) {
    let state = start;
    const last = Math.min(sitting * ROUNDS_PER_SITTING, MAX_ROUNDS);
    for (let round = (sitting - 1) * ROUNDS_PER_SITTING + 1; round <= last && !state.closed; round++) {
        state = await floorRound(cfg, state, round);
    }
    if (!state.closed && state.rounds >= MAX_ROUNDS) state = closeFloor(state, MAX_ROUNDS, "Round cap reached.");
    const note = cfg.notes[sitting - 1];
    if (!note || state.rounds < (sitting - 1) * ROUNDS_PER_SITTING + 1) return state;
    return { ...state, entries: [...state.entries, { kind: "note", section: `Clerk note after sitting ${sitting}`, sitting, text: note }] };
}

/** Report returned to the clerk after a sitting: what was said in it and whether the floor is still open. */
function debateReport(cfg, state) {
    const fresh = state.entries.filter(entry => entry.sitting === cfg.sittings || (cfg.sittings === 1 && entry.sitting === 0));
    return {
        status: state.closed ? "ready_for_ballot" : "open",
        closedBy: state.closed,
        rounds: state.rounds,
        turns: state.turns,
        bids: state.bids.filter(record => record.sitting === cfg.sittings).map(record => record.line),
        transcript: renderTranscript(fresh),
        checkpoint: checkpoint(cfg, cfg.notes.length),
    };
}

/** Stage for a vote on the given options. */
function voteStage(seats, motion) {
    return {
        phase: "Vote",
        tag: motion.firstCount ? "Runoff" : "Vote",
        schema: {
            type: "object",
            additionalProperties: false,
            required: ["vote", "confidence", "rationale", "changed_mind", "moved_by"],
            properties: {
                vote: { type: "string", enum: motion.options.map(option => option.id) },
                confidence: { type: "integer", minimum: 1, maximum: 5 },
                rationale: { type: "string", description: "The argument that decides it for you, at most 60 words" },
                changed_mind: { type: "boolean", description: "True if this differs from the position in your opening" },
                moved_by: { type: "string", enum: [...seats, "NONE"], description: "The seat whose argument moved you most" },
            },
        },
    };
}

/** One line per counted option, for the runoff prompt and the progress log. */
function renderCount(count) {
    return count.map(line => `${line.id} (${line.title}): ${line.votes}`).join(", ");
}

/** Prompt asking one member to vote; a motion with a first count is a runoff. */
function votePrompt(cfg, state, motion, seat) {
    const runoff = motion.firstCount ?
        `\n\nThe first count produced no majority: ${renderCount(motion.firstCount)}. This is the runoff between the two leading options.` :
        "";
    return `The council has closed the debate on the matter below and now votes. You hold the ${seat} seat.

# Brief

${cfg.brief}

# The debate

${renderTranscript(state.entries)}

# Ballot

${motion.options.map(option => `- ${option.id}: ${option.title} - ${option.summary}`).join("\n")}${runoff}

# Your task

Cast your vote.
- vote: the id of the option you back.
- confidence: 1 = barely, 5 = certain.
- rationale: the argument that decides it for you, in at most 60 words.
- changed_mind: true if this differs from the position in your opening.
- moved_by: the seat whose argument moved you most, or NONE.

# Rules

- Vote for what you judge best after the debate, not for what is most popular.
${CONDUCT}`;
}

/** Mean of a list of numbers, 0 for an empty list. */
function mean(numbers) {
    return numbers.length ? numbers.reduce((sum, n) => sum + n, 0) / numbers.length : 0;
}

/** Count the votes per option, strongest first; equal counts are ordered by mean confidence. */
function countVotes(options, votes) {
    return options.map(option => {
        const backers = votes.filter(vote => vote.answer.vote === option.id);
        return {
            id: option.id,
            title: option.title,
            votes: backers.length,
            seats: backers.map(vote => vote.seat),
            confidence: mean(backers.map(vote => vote.answer.confidence)),
        };
    }).sort((a, b) => b.votes - a.votes || b.confidence - a.confidence);
}

/** Strength of the result: the leading option's share of all convened seats. */
function levelOf(count, seatCount) {
    const share = count[0].votes / seatCount;
    if (share === 1) return "unanimous";
    if (share >= CONSENSUS_SHARE) return "consensus";
    return share > 0.5 ? "majority" : "split";
}

/** Poll every member on a motion and count the result. */
async function poll(cfg, state, motion) {
    const votes = await askAll(cfg.seats, voteStage(cfg.seats, motion), seat => votePrompt(cfg, state, motion, seat));
    const count = countVotes(motion.options, votes);
    log(`${motion.firstCount ? "Runoff" : "Vote"}: ${renderCount(count)}`);
    return { votes, count };
}

/** Final record of the vote for the clerk. */
function verdict(cfg, state, final, firstCount) {
    const level = levelOf(final.count, cfg.seats.length);
    return {
        status: level === "split" ? "split" : "decided",
        level,
        winner: level === "split" ? null : final.count[0].id,
        count: final.count,
        runoff: firstCount !== null,
        firstCount,
        votes: final.votes.map(vote => ({ seat: vote.seat, ...vote.answer })),
        abstained: cfg.seats.filter(seat => !final.votes.some(vote => vote.seat === seat)),
        rounds: state.rounds,
        closedBy: state.closed,
    };
}

/** Hold the vote on the clerk's ballot, with one runoff between the two leading options if no majority forms. */
async function holdVote(cfg, state) {
    const first = await poll(cfg, state, { options: cfg.ballot, firstCount: null });
    if (levelOf(first.count, cfg.seats.length) !== "split") return verdict(cfg, state, first, null);
    const leaders = first.count.slice(0, 2).map(line => line.id);
    const finalists = cfg.ballot.filter(option => leaders.includes(option.id));
    const second = await poll(cfg, state, { options: finalists, firstCount: first.count });
    return verdict(cfg, state, second, first.count);
}

const cfg = readConfig(args);
assertValid(cfg);
let state = await openings(cfg);
for (let sitting = 1; sitting <= cfg.sittings; sitting++) state = await playSitting(cfg, state, sitting);
return cfg.ballot ? await holdVote(cfg, state) : debateReport(cfg, state);
