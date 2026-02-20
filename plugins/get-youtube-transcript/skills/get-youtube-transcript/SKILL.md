---
name: get-youtube-transcript
description: >-
  Fetch transcripts and subtitles from YouTube videos. Use when users want to get,
  download, extract, or read a YouTube video transcript or subtitles. Triggers on
  "get transcript", "youtube transcript", "fetch subtitles", "transcribe video",
  "video transcript", "what does this video say". Requires uvx with youtube-transcript-api.
user-invocable: true
argument-hint: <youtube-url-or-video-id> [options]
allowed-tools:
  - Bash
  - Write
  - Read
---

# Get YouTube Transcript

Fetch transcripts from YouTube videos via `uvx --from youtube-transcript-api youtube_transcript_api`.

## Argument Parsing

Extract video ID(s) and options from `$ARGUMENTS`:

- **YouTube URLs**: Extract video ID from patterns like:
    - `https://www.youtube.com/watch?v=VIDEO_ID`
    - `https://youtu.be/VIDEO_ID`
    - `https://www.youtube.com/embed/VIDEO_ID`
    - `https://youtube.com/shorts/VIDEO_ID`
- **Bare video IDs**: Use directly (11-character alphanumeric strings with `-` and `_`)
- **Multiple videos**: Space-separated URLs or IDs are supported

### Supported Options

Users may specify these inline with the URL/ID:

| Option                                             | Description                                                        |
| -------------------------------------------------- | ------------------------------------------------------------------ |
| `--languages` or language name (e.g., "in German") | Preferred transcript language(s)                                   |
| `--translate <lang>` or "translate to \<language>" | Translate transcript to target language                            |
| `--format <fmt>`                                   | Output format: `text` (default), `json`, `pretty`, `srt`, `webvtt` |
| `--list` or "list languages"                       | List available transcript languages                                |
| `--exclude-generated`                              | Skip auto-generated transcripts                                    |
| `--exclude-manually-created`                       | Skip manually created transcripts                                  |

## Workflow

### Step 1: Parse Input

Extract video ID(s) from the provided arguments. If no arguments given, ask the user for a YouTube URL or video ID.

### Step 2: Determine Intent

Based on the arguments, determine if the user wants to:

1. **List available transcripts** — if `--list` or "list languages" is mentioned
2. **Fetch transcript** — default action

### Step 3: Execute

#### List Transcripts

```bash
uvx --from youtube-transcript-api youtube_transcript_api VIDEO_ID --list-transcripts
```

#### Fetch Transcript

Build the command from parsed options:

```bash
uvx --from youtube-transcript-api youtube_transcript_api VIDEO_ID [OPTIONS]
```

Default flags when no format is specified: `--format text`

**Language handling:**

- If user specifies a language (e.g., "in German"), map to ISO 639-1 code and use `--languages de`
- If user asks to translate (e.g., "translate to French"), use `--translate fr`
- If no language specified, omit `--languages` to get the default transcript

### Step 4: Present Results

- **Short transcripts** (under 200 lines): Display directly in the conversation
- **Long transcripts** (200+ lines): Save to a file and tell the user where it was saved
- If the user specified a file path, always save there regardless of length
- When saving, use a descriptive filename: `<video-id>.txt` (or appropriate extension for the format)

## Error Handling

- **No transcript available**: Inform the user and suggest `--list-transcripts` to check available languages
- **Invalid video ID/URL**: Ask the user to verify the URL
- **Network errors**: Report the error and suggest retrying

## Examples

User: "get transcript from https://www.youtube.com/watch?v=dQw4w9WgXcQ"
→ `uvx --from youtube-transcript-api youtube_transcript_api dQw4w9WgXcQ --format text`

User: "youtube transcript dQw4w9WgXcQ in German"
→ `uvx --from youtube-transcript-api youtube_transcript_api dQw4w9WgXcQ --languages de --format text`

User: "get subtitles for dQw4w9WgXcQ translated to French as srt"
→ `uvx --from youtube-transcript-api youtube_transcript_api dQw4w9WgXcQ --translate fr --format srt`

User: "what languages are available for dQw4w9WgXcQ"
→ `uvx --from youtube-transcript-api youtube_transcript_api dQw4w9WgXcQ --list-transcripts`
