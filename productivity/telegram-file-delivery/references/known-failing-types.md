# Known MEDIA-failing file types

Types that look like text when sent via MEDIA: prefix in send_message.
For ALL of these, use direct Telegram Bot API `sendDocument` instead.

## Confirmed failing

| Extension | MIME | What happens with MEDIA |
|-----------|------|-------------------------|
| .py | text/x-python | Content appears as raw text message |
| .html | text/html | Content appears as raw text message |
| .txt | text/plain | Content appears as raw text message |
| .md | text/markdown | Content appears as raw text message |
| .json | application/json | Content appears as raw text message |
| .yaml | text/yaml | Content appears as raw text message |
| .csv | text/csv | Content appears as raw text message |
| .log | text/plain | Content appears as raw text message |

## Confirmed working

| Extension | MIME | What happens with MEDIA |
|-----------|------|-------------------------|
| .png | image/png | Shows inline as photo |
| .jpg / .jpeg | image/jpeg | Shows inline as photo |
| .webp | image/webp | Shows inline as photo |
| .ogg | audio/ogg | Sends as voice bubble |
| .mp4 | video/mp4 | Plays inline |

## Untested (likely fails)

| Extension | Likely behavior |
|-----------|----------------|
| .pdf | Probably raw text or nothing |
| .zip | Probably nothing |
| .svg | Might show as image or break |
