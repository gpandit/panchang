"use client";

import type { JSX } from "react";
import { useState } from "react";
import {
  Card,
  Cta,
  Footer,
  FormField,
  IconButton,
  ListRow,
  Modal,
  Nav,
  SectionHeader,
} from "@/components/primitives";

/**
 * Structural preview of the contracted base components (see
 * packages/design-tokens/CONTRACT.md). Driven entirely by named tokens —
 * intentionally undesigned. TODO(design): once skins land, this route is the
 * place to verify the design system end-to-end against real markup/contracts.
 */
export default function ComponentsPreviewPage(): JSX.Element {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <main className="flex flex-col gap-xl p-lg">
      <SectionHeader
        level={1}
        title="Component preview"
        subtitle="Structural shells only — no visual design. See CONTRACT.md."
      />

      <section>
        <SectionHeader title="Nav" />
        <Nav
          brand={<span className="font-display">The Pandit</span>}
          activeHref="/today"
          items={[
            { href: "/today", label: "Today" },
            { href: "/calendar", label: "Calendar" },
            { href: "/festivals", label: "Festivals" },
          ]}
          actions={<IconButton icon={<span aria-hidden="true">⚙</span>} aria-label="Settings" />}
        />
      </section>

      <section>
        <SectionHeader title="Card" />
        <div className="grid grid-cols-2 gap-md">
          <Card header={<strong>Static card</strong>} body={<p>Body content goes here.</p>} />
          <Card
            interactive
            selected
            aria-label="Interactive selected card"
            header={<strong>Interactive card</strong>}
            body={<p>Selected, focusable, keyboard-activatable.</p>}
          />
        </div>
      </section>

      <section>
        <SectionHeader title="CTA / Buttons" />
        <div className="flex flex-row gap-sm">
          <Cta label="Primary" variant="primary" />
          <Cta label="Secondary" variant="secondary" />
          <Cta label="Ghost" variant="ghost" />
          <Cta label="Destructive" variant="destructive" />
          <Cta label="Loading" loading />
          <IconButton icon={<span aria-hidden="true">★</span>} aria-label="Favourite" />
        </div>
      </section>

      <section>
        <SectionHeader title="List row" />
        <ul>
          <ListRow primary="Ekadashi reminder" secondary="Tomorrow, 6:00 AM" />
          <ListRow
            interactive
            primary="Diwali planning"
            secondary="3 tasks remaining"
            trailing={<span aria-hidden="true">›</span>}
          />
        </ul>
      </section>

      <section>
        <SectionHeader title="Form field" />
        <div className="flex flex-col gap-md max-w-sm">
          <FormField
            id="location"
            label="Location"
            hint="Used to compute sunrise-to-sunrise day boundaries."
            control={<input type="text" className="rounded-md border border-border px-sm py-xs" />}
          />
          <FormField
            id="email"
            label="Email"
            required
            invalid
            error="Enter a valid email address."
            control={<input type="email" className="rounded-md border border-border px-sm py-xs" />}
          />
        </div>
      </section>

      <section>
        <SectionHeader title="Modal" />
        <Cta label="Open modal" onClick={() => setModalOpen(true)} />
        <Modal
          open={modalOpen}
          onClose={() => setModalOpen(false)}
          labelledBy="preview-modal-title"
          header={<h2 id="preview-modal-title">Confirm action</h2>}
          body={<p>Focus is trapped here; Escape or the backdrop closes it.</p>}
          footer={
            <div className="flex flex-row gap-sm justify-end">
              <Cta label="Cancel" variant="ghost" onClick={() => setModalOpen(false)} />
              <Cta label="Confirm" variant="primary" onClick={() => setModalOpen(false)} />
            </div>
          }
        />
      </section>

      <Footer
        links={[
          { href: "/privacy", label: "Privacy" },
          { href: "/terms", label: "Terms" },
        ]}
        legal="© The Pandit — placeholder footer, structure only."
      />
    </main>
  );
}
