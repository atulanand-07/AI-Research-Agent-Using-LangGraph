You are an expert React UI/UX developer.

Build a modern, production-ready React frontend for an AI Research Assistant.

The design inspiration should be Google's NotebookLM.

DO NOT copy NotebookLM code.
Create an original implementation with the same layout, spacing, modern aesthetics, rounded corners, dark theme, and smooth animations.

==========================================================
TECH STACK
==========================================================

- React (Vite)
- Plain CSS (No Tailwind)
- React Icons (or Lucide React)
- Functional Components
- Hooks
- Responsive Layout
- Clean component structure

==========================================================
THEME
==========================================================

Dark Theme

Background:
#1B1C1F

Cards:
#24262B

Borders:
#34373D

Accent:
#4A90E2

Text:
#FFFFFF

Secondary Text:
#AEB4BE

Hover:
#2D3037

Rounded Corners:
16px

Modern shadows.

Smooth hover animations.

Smooth transitions.

==========================================================
LAYOUT
==========================================================

Header at top

Below it

Three panels

----------------------------------------
| Sources | Chat | Get Articles |
----------------------------------------

Height should occupy almost the full viewport.

Resizable feeling using CSS grid.

Sources: 25%

Chat: 50%

Get Articles: 25%

==========================================================
HEADER
==========================================================

Left

Robot icon

Title

AI Researcher

Right side

Two Toggle Buttons

--------------------------------

Sources

ON / OFF

--------------------------------

Articles

ON / OFF

--------------------------------

Behavior

Sources OFF
Articles OFF

= General Chat Mode

Sources ON
Articles OFF

= RAG Mode

Sources OFF
Articles ON

= Article Chat

Sources ON
Articles ON

= Hybrid Mode

Display current mode beside the toggles.

Example

Current Mode:
Hybrid

==========================================================
SOURCES PANEL
==========================================================

Exactly like NotebookLM.

Card title

Sources

Button

+ Add Sources

Supported

PDF

Wikipedia URL

Below

Scrollable list

Each source card contains

PDF icon

Source Name

Delete icon

At bottom

Show

No sources added yet.

==========================================================
CHAT PANEL
==========================================================

Large conversation window.

Messages

User messages

Right aligned

Assistant messages

Left aligned

Modern chat bubbles.

Bottom

Input field

Placeholder

Ask anything...

Send button.

Below every assistant response display exactly

3-5 clickable follow-up suggestion chips.

Example

--------------------------------

Why Multi-head Attention?

Applications

Limitations

Future Work

Encoder vs Decoder

--------------------------------

Clicking a chip automatically sends it as the next message.

No backend needed.

Use mock data.

==========================================================
GET ARTICLES PANEL
==========================================================

Replace NotebookLM Studio completely.

Card title

Get Articles

Search bar

Placeholder

Search research papers...

Search icon.

When searching

Display

Top 10 paper cards.

Each Paper Card

Paper title

Authors

Year

Source

(arXiv / Semantic Scholar / Wikipedia)

Short abstract

Citation count

Clickable.

When clicked

Highlight selected card.

==========================================================
MOCK DATA
==========================================================

Use dummy papers.

Example

Attention Is All You Need

BERT

GPT-3

LLaMA

LangGraph

RAG

ReAct

Chain of Thought

AutoGPT

Voyager

==========================================================
COMPONENT STRUCTURE
==========================================================

Header

ToggleButtons

SourcesPanel

SourceCard

ChatPanel

ChatBubble

SuggestionChips

ArticlesPanel

SearchBar

PaperCard

==========================================================
STATE
==========================================================

React state only.

No backend.

Maintain

sources

articles

selectedArticle

messages

followups

searchText

knowledgeMode

Knowledge Mode values

general

sources

article

hybrid

==========================================================
INTERACTIONS
==========================================================

Toggle buttons update knowledge mode.

Searching filters papers.

Selecting paper highlights it.

Sending message appends chat.

Clicking follow-up sends it.

Deleting source removes it.

==========================================================
ANIMATIONS
==========================================================

Hover lift cards.

Buttons animate.

Paper selection glow.

Smooth scrolling.

Message fade-in.

Suggestion chip hover effect.

==========================================================
RESPONSIVE
==========================================================

Desktop

3 columns.

Tablet

2 columns.

Mobile

Stack vertically.

==========================================================
CODE QUALITY
==========================================================

Write production-quality React code.

Use reusable components.

Keep CSS modular.

Avoid duplicated code.

Use Flexbox and CSS Grid appropriately.

Use semantic HTML.

Well-commented code.

==========================================================
OUTPUT
==========================================================

Generate the complete Vite React project.

Include every file.

Do not omit any code.

Do not use placeholders.

Provide complete runnable code.