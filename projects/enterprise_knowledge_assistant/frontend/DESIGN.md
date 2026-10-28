# The knowledge desk

Taskify helps employees ask private questions about company information, follow answers to original documents, and maintain a useful shared library. The design puts the conversation first and makes the connection to its sources visible.

## Visual system

| Token | Value     | Purpose                                 |
| ----- | --------- | --------------------------------------- |
| Cloud | `#F7F8FC` | Quiet working canvas                    |
| Paper | `#FFFFFF` | Documents, forms, navigation            |
| Ink   | `#26334D` | Reading text and headings               |
| Iris  | `#6554C0` | Actions, selected navigation, identity  |
| Lilac | `#EEEBFA` | Selected surfaces and company questions |
| Sage  | `#EAF4EF` | Ready documents and confirmations       |

Manrope gives headings a rounded, open character; Source Sans 3 provides readable controls and longer answers. Both are bundled locally through Fontsource. Supporting text uses `#657087` for contrast against the light canvas. The shared stylesheet owns the tokens, spacing, breakpoints, and motion.

## Layout decision

A top-navigation concept gave every destination equal prominence but used too much space on small screens. A persistent desk sidebar makes the company library discoverable while keeping administration in its own navigation group. Content and forms are left aligned; the empty conversation is centered around its primary action.

```text
Desktop
┌────────────────────┬──────────────────────────────────────────┐
│ Taskify            │ Company workspace                Private │
│ Company workspace  ├──────────────────────────────────────────┤
│                    │ Page title and useful context            │
│ Chat               │                                          │
│ Knowledge          │ Conversation / library / working form    │
│                    │                                          │
│ Administration     │                                          │
│ Manage knowledge   │                                          │
│ Create user        │                                          │
│                    │                                          │
│ Account / log out  │ Question composer, when chatting         │
└────────────────────┴──────────────────────────────────────────┘

Mobile
┌──────────────────────────────┐
│ Menu    Workspace    Private │
├──────────────────────────────┤
│ Page title                   │
│                              │
│ Single-column work area      │
│                              │
│ Composer / primary action    │
└──────────────────────────────┘
```

## Review against the brief

The palette stays cool and light. Decorative gradients, generic metric tiles, and repeated card shadows were excluded. The folded-page monogram, file-format colors, and original-source references ground the identity in actual company documents. Document lists use rows; forms use working panels; chat remains an open reading surface. Those structures reflect different tasks rather than applying one card treatment everywhere.

Only the empty conversation has an entrance sequence. Subsequent motion explains loading, an expanded navigation drawer, or a confirmation. Reduced-motion preferences disable animations and transitions. Mobile navigation supports Escape, focus containment, focus restoration, and an inert background. Inputs retain labels, controls have visible focus, and the composer handles composition events for multilingual keyboards.

Search filters currently loaded documents and their filenames. When more pages are available, the interface names that boundary and keeps loading available. Starter prompts fill the composer for review rather than sending a question automatically. Authentication, role boundaries, source authorization, plain-text answer rendering, and the saved-conversation workflow remain owned by the existing application layer.
