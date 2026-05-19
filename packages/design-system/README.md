# @pinky/design-system

React component library built on shadcn/ui primitives. Provides the visual building blocks for the Pinky web UI.

## Components

28 shadcn/ui components including Button, Dialog, AlertDialog, Input, Select, Badge, Card, Tabs, Table, Tooltip, and more.

## Usage

Components are imported directly by the web app:

```typescript
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
```

## Styling

- Tailwind CSS v4 with `@theme` tokens
- All custom CSS in `@layer base`
- Design tokens defined in the web app's `globals.css`

## Adding Components

Use the shadcn/ui CLI from the web app directory:

```bash
cd apps/web
npx shadcn@latest add <component-name>
```
